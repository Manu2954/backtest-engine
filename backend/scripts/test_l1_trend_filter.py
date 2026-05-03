"""
Test L1 Trend Filtering for regime detection.

L1 trend filtering fits a piecewise linear trend to data,
naturally producing sparse slope changes (breakpoints).

Sub-classification uses KDE (Kernel Density Estimation) on price distribution:
- High KDE peak = price concentrated at few levels = CONSOLIDATION
- Flat KDE = price spread across levels = TRENDING

Prerequisites:
    pip install cvxpy matplotlib scipy

Run: python backend/scripts/test_l1_trend_filter.py
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

import warnings
import numpy as np
import pandas as pd
from scipy import stats

# Suppress cvxpy numerical warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, module='cvxpy')

try:
    import cvxpy as cp
except ImportError:
    print("Install cvxpy: pip install cvxpy")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Plots will be skipped.")

from app.engine.data_layer import fetch_ohlcv


def compute_kde_peak(prices: np.ndarray, n_points: int = 100) -> tuple[float, float]:
    """
    Compute KDE peak height for price distribution.

    High peak = price concentrated at few levels = consolidation
    Low/flat = price spread across levels = trending

    Args:
        prices: Price series
        n_points: Number of points for KDE evaluation

    Returns:
        Tuple of (peak_height, peak_price)
    """
    if len(prices) < 10:
        return 0.0, np.mean(prices)

    # Normalize prices to [0, 1] range for comparable peak heights
    p_min, p_max = prices.min(), prices.max()
    if p_max == p_min:
        return 1.0, p_min  # All same price = maximum consolidation

    prices_norm = (prices - p_min) / (p_max - p_min)

    # Fit KDE
    try:
        kde = stats.gaussian_kde(prices_norm)

        # Evaluate on grid
        grid = np.linspace(0, 1, n_points)
        density = kde(grid)

        # Peak height (max density)
        peak_idx = np.argmax(density)
        peak_height = density[peak_idx]

        # Convert peak location back to price
        peak_price = p_min + grid[peak_idx] * (p_max - p_min)

        return peak_height, peak_price
    except Exception:
        return 0.0, np.mean(prices)


def compute_price_concentration(prices: np.ndarray, n_bins: int = 20) -> float:
    """
    Compute price concentration ratio.

    High ratio = prices concentrated in few bins = consolidation
    Low ratio = prices spread across bins = trending

    Args:
        prices: Price series
        n_bins: Number of bins for histogram

    Returns:
        Concentration ratio (0 to 1, higher = more concentrated)
    """
    if len(prices) < 10:
        return 0.5

    # Create histogram
    counts, _ = np.histogram(prices, bins=n_bins)

    # Concentration = max bin / total (what fraction in most popular bin)
    concentration = counts.max() / counts.sum()

    return concentration


def l1_trend_filter(y: np.ndarray, lambda_param: float = 1.0) -> np.ndarray:
    """
    L1 trend filtering (second-order).

    Minimizes: ||y - x||² + λ * ||D²x||₁

    Where D² is the second difference operator (measures slope changes).

    Args:
        y: Input signal (e.g., log prices)
        lambda_param: Regularization parameter. Higher = smoother trend.

    Returns:
        Filtered trend (same length as y)
    """
    n = len(y)
    x = cp.Variable(n)

    # Second difference matrix (n-2 x n)
    # D²x[i] = x[i] - 2*x[i+1] + x[i+2]
    # This measures the change in slope
    D2 = np.zeros((n - 2, n))
    for i in range(n - 2):
        D2[i, i] = 1
        D2[i, i + 1] = -2
        D2[i, i + 2] = 1

    # Objective: minimize ||y - x||² + λ * ||D²x||₁
    objective = cp.Minimize(
        cp.sum_squares(y - x) + lambda_param * cp.norm(D2 @ x, 1)
    )

    prob = cp.Problem(objective)
    prob.solve(solver=cp.CLARABEL)  # Fast solver

    return x.value


def detect_slope_changes(trend: np.ndarray, threshold: float = 1e-6) -> list[int]:
    """
    Detect where slope changes sign in the filtered trend.

    Args:
        trend: Filtered trend from L1 filter
        threshold: Minimum slope change to consider

    Returns:
        List of indices where slope changes sign
    """
    # Compute slope (first difference)
    slope = np.diff(trend)

    # Find sign changes
    breakpoints = []
    for i in range(1, len(slope)):
        # Slope changed sign
        if slope[i-1] * slope[i] < 0:
            # Check if change is significant
            if abs(slope[i] - slope[i-1]) > threshold:
                breakpoints.append(i)

    return breakpoints


def compute_bic(y: np.ndarray, trend: np.ndarray, n_breakpoints: int) -> float:
    """
    Compute BIC for L1 trend filter result.

    BIC = n * log(RSS/n) + k * log(n)

    Args:
        y: Original signal
        trend: Filtered trend
        n_breakpoints: Number of detected breakpoints

    Returns:
        BIC score (lower is better)
    """
    n = len(y)
    rss = np.sum((y - trend) ** 2)

    # Degrees of freedom: breakpoints + 1 (for the base trend)
    # Each breakpoint adds a "kink" to the piecewise linear function
    k = n_breakpoints + 1

    # BIC formula
    bic = n * np.log(rss / n) + k * np.log(n)

    return bic


def find_optimal_lambda(y: np.ndarray, lambda_range: list[float]) -> tuple[float, dict]:
    """
    Find optimal λ using BIC criterion.

    Args:
        y: Input signal
        lambda_range: List of λ values to try

    Returns:
        Tuple of (optimal_lambda, results_dict)
    """
    results = {}

    for lam in lambda_range:
        trend = l1_trend_filter(y, lambda_param=lam)
        breakpoints = detect_slope_changes(trend)
        bic = compute_bic(y, trend, len(breakpoints))

        results[lam] = {
            'trend': trend,
            'breakpoints': breakpoints,
            'n_segments': len(breakpoints) + 1,
            'bic': bic,
        }
        print(f'  λ={lam:8.1f} → {len(breakpoints)+1:3d} segments, BIC={bic:.2f}')

    # Find λ with minimum BIC
    optimal_lambda = min(results.keys(), key=lambda l: results[l]['bic'])

    return optimal_lambda, results


def compute_ols_tstat(y: np.ndarray) -> tuple[float, float, float]:
    """
    Compute OLS slope and t-statistic for a segment.

    Args:
        y: Log prices for the segment

    Returns:
        Tuple of (slope, t_stat, r_squared)
    """
    n = len(y)
    if n < 3:
        return 0.0, 0.0, 0.0

    # Time index
    x = np.arange(n)

    # OLS: y = a + b*x
    x_mean = x.mean()
    y_mean = y.mean()

    # Slope
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    if denominator == 0:
        return 0.0, 0.0, 0.0

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # Predictions and residuals
    y_pred = intercept + slope * x
    residuals = y - y_pred

    # R-squared
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Standard error of slope
    mse = ss_res / (n - 2)  # Mean squared error
    se_slope = np.sqrt(mse / denominator) if mse > 0 else 0.0

    # t-statistic
    t_stat = slope / se_slope if se_slope > 0 else 0.0

    return slope, t_stat, r_squared


def label_segments(
    df: pd.DataFrame,
    trend: np.ndarray,
    breakpoints: list[int],
    kde_percentile: float = 70,
) -> list[dict]:
    """
    Label segments based on slope direction and KDE for sub-classification.

    Primary regime (from slope):
    - BULL: Positive slope
    - BEAR: Negative slope

    Sub-regime (from KDE peak height):
    - CONSOLIDATION: KDE peak in top percentile (price concentrated)
    - TRENDING: KDE peak in bottom percentile (price spread out)

    Args:
        df: OHLCV DataFrame
        trend: L1 filtered trend (log prices)
        breakpoints: List of breakpoint indices
        kde_percentile: Top X% of KDE peaks = CONSOLIDATION

    Returns:
        Tuple of (segments list, kde_threshold)
    """
    boundaries = [0] + breakpoints + [len(df)]
    segments = []

    # First pass: compute all metrics
    for i in range(len(boundaries) - 1):
        start_idx = boundaries[i]
        end_idx = boundaries[i + 1] - 1

        seg = df.iloc[start_idx:end_idx + 1]
        seg_prices = seg['close'].values
        seg_log_prices = np.log(seg_prices)

        if len(seg) == 0:
            continue

        # Compute OLS stats on log prices
        slope, t_stat, r_squared = compute_ols_tstat(seg_log_prices)

        # Compute KDE peak height and concentration
        kde_peak, peak_price = compute_kde_peak(seg_prices)
        concentration = compute_price_concentration(seg_prices)

        # Price metrics
        start_price = seg_prices[0]
        end_price = seg_prices[-1]
        pct_change = ((end_price / start_price) - 1) * 100

        # Primary regime from slope direction
        if slope > 0:
            regime = "BULL"
        else:
            regime = "BEAR"

        segments.append({
            'start_idx': start_idx,
            'end_idx': end_idx,
            'start_date': seg.index[0],
            'end_date': seg.index[-1],
            'regime': regime,
            'sub_regime': None,  # Will be set in second pass
            'bars': len(seg),
            'slope': slope,
            't_stat': t_stat,
            'r_squared': r_squared,
            'kde_peak': kde_peak,
            'concentration': concentration,
            'peak_price': peak_price,
            'pct_change': pct_change,
            'start_price': start_price,
            'end_price': end_price,
        })

    # Second pass: compute KDE percentile threshold and label sub-regimes
    all_kde_peaks = [seg['kde_peak'] for seg in segments]
    kde_threshold = np.percentile(all_kde_peaks, kde_percentile)

    for seg in segments:
        # High KDE peak = consolidation (price concentrated)
        if seg['kde_peak'] >= kde_threshold:
            seg['sub_regime'] = "CONSOLIDATION"
        else:
            seg['sub_regime'] = "TRENDING"

    return segments, kde_threshold


def detect_consolidation_zones(
    df: pd.DataFrame,
    segments: list[dict],
    window_size: int = 24,
    range_percentile: float = 30,
    min_persistence: int = 12,
) -> list[dict]:
    """
    Detect consolidation zones within L1 segments.

    Consolidation = price range compression (tight range relative to typical).
    Only labels as CONSOLIDATION if condition persists for min_persistence bars.

    Args:
        df: OHLCV DataFrame
        segments: L1 segments from pass 1
        window_size: Rolling window for range calculation
        range_percentile: Below this percentile = consolidation candidate
        min_persistence: Minimum consecutive bars to confirm consolidation

    Returns:
        List of sub-segments with TRENDING or CONSOLIDATION label
    """
    # First pass: compute all rolling ranges to find threshold
    all_ranges = []

    for seg in segments:
        start_idx = seg['start_idx']
        end_idx = seg['end_idx']
        seg_df = df.iloc[start_idx:end_idx + 1]

        if len(seg_df) < window_size:
            continue

        highs = seg_df['high'].values
        lows = seg_df['low'].values

        for i in range(len(seg_df) - window_size + 1):
            window_high = highs[i:i + window_size].max()
            window_low = lows[i:i + window_size].min()
            range_pct = (window_high - window_low) / window_low
            all_ranges.append(range_pct)

    # Threshold: ranges below this are "tight" = consolidation candidate
    range_threshold = np.percentile(all_ranges, range_percentile) if all_ranges else 0.01

    # Second pass: label bars with persistence requirement
    refined_segments = []

    for seg in segments:
        start_idx = seg['start_idx']
        end_idx = seg['end_idx']
        seg_df = df.iloc[start_idx:end_idx + 1]
        parent_regime = seg['regime']

        # If segment too small, keep as trending
        if len(seg_df) < window_size * 2:
            refined_seg = seg.copy()
            refined_seg['sub_regime'] = 'TRENDING'
            refined_segments.append(refined_seg)
            continue

        highs = seg_df['high'].values
        lows = seg_df['low'].values

        # First: mark each bar as consolidation candidate or not
        is_tight = []
        for i in range(len(seg_df) - window_size + 1):
            window_high = highs[i:i + window_size].max()
            window_low = lows[i:i + window_size].min()
            range_pct = (window_high - window_low) / window_low
            is_tight.append(range_pct < range_threshold)

        # Fill remaining bars at end
        last_tight = is_tight[-1] if is_tight else False
        for _ in range(len(seg_df) - len(is_tight)):
            is_tight.append(last_tight)

        # Apply persistence: only mark CONSOLIDATION if min_persistence consecutive tight bars
        bar_labels = ['TRENDING'] * len(seg_df)

        i = 0
        while i < len(is_tight):
            if is_tight[i]:
                # Count consecutive tight bars
                j = i
                while j < len(is_tight) and is_tight[j]:
                    j += 1
                consecutive = j - i

                if consecutive >= min_persistence:
                    # Mark all these bars as CONSOLIDATION
                    for k in range(i, j):
                        bar_labels[k] = 'CONSOLIDATION'

                i = j
            else:
                i += 1

        # Merge consecutive same-label bars
        sub_segments = []
        current_label = bar_labels[0]
        sub_start = 0

        for i in range(1, len(bar_labels)):
            if bar_labels[i] != current_label:
                sub_segments.append({
                    'local_start': sub_start,
                    'local_end': i - 1,
                    'sub_regime': current_label,
                })
                current_label = bar_labels[i]
                sub_start = i

        # Close final
        sub_segments.append({
            'local_start': sub_start,
            'local_end': len(bar_labels) - 1,
            'sub_regime': current_label,
        })

        # Convert to global indices and compute stats
        for sub in sub_segments:
            global_start = start_idx + sub['local_start']
            global_end = start_idx + sub['local_end']

            sub_df = df.iloc[global_start:global_end + 1]
            sub_log_prices = np.log(sub_df['close'].values)

            slope, t_stat, r_squared = compute_ols_tstat(sub_log_prices)

            start_price = sub_df['close'].iloc[0]
            end_price = sub_df['close'].iloc[-1]
            pct_change = ((end_price / start_price) - 1) * 100

            refined_segments.append({
                'start_idx': global_start,
                'end_idx': global_end,
                'start_date': sub_df.index[0],
                'end_date': sub_df.index[-1],
                'regime': parent_regime,
                'sub_regime': sub['sub_regime'],
                'bars': len(sub_df),
                'slope': slope,
                't_stat': t_stat,
                'r_squared': r_squared,
                'pct_change': pct_change,
                'start_price': start_price,
                'end_price': end_price,
            })

    return refined_segments


def print_refined_segments(segments: list[dict]):
    """Print refined segment details with sub-regime."""
    print(f'\nTotal sub-segments: {len(segments)}')

    # Count by regime + sub_regime
    combo_counts = {}
    combo_bars = {}
    for seg in segments:
        key = f"{seg['regime']}_{seg['sub_regime']}"
        combo_counts[key] = combo_counts.get(key, 0) + 1
        combo_bars[key] = combo_bars.get(key, 0) + seg['bars']

    print(f'Segment counts: {combo_counts}')

    print(f'\nSegment details:')
    for i, seg in enumerate(segments):
        direction = "↑" if seg['regime'] == 'BULL' else "↓"
        sub_icon = "◆" if seg['sub_regime'] == 'CONSOLIDATION' else "→"

        print(f"  Seg {i+1}: {seg['start_date']} → {seg['end_date']}")
        print(f"          {seg['regime']} {direction} | {seg['sub_regime']} {sub_icon} | "
              f"Bars: {seg['bars']}, Change: {seg['pct_change']:+.2f}%")

        if i >= 29:
            remaining = len(segments) - i - 1
            if remaining > 0:
                print(f"  ... and {remaining} more segments")
            break

    return combo_bars


def refine_segments_pass2(
    df: pd.DataFrame,
    segments: list[dict],
    min_subsegment: int = 100,
    t_threshold: float = 2.0,
    vol_percentile: float = 50,
) -> list[dict]:
    """
    Pass 2: Refine L1 segments by splitting weak-trend portions.

    For each L1 segment:
    1. If overall |t-stat| is low, the segment might be sideways
    2. Try to find a split point that creates better sub-segments

    Args:
        df: OHLCV DataFrame
        segments: L1 segments from pass 1
        min_subsegment: Minimum bars for a sub-segment
        t_threshold: t-stat threshold for significance
        vol_percentile: Percentile to split CHOPPY vs RANGING

    Returns:
        List of refined sub-segments
    """
    # First, collect all residual vols for percentile calculation
    all_residual_vols = []
    for seg in segments:
        all_residual_vols.append(seg['residual_vol'])
    median_vol = np.percentile(all_residual_vols, vol_percentile) if all_residual_vols else 0

    refined_segments = []

    for seg in segments:
        # Re-label based on t-stat threshold
        t_stat = seg['t_stat']
        residual_vol = seg['residual_vol']

        if t_stat > t_threshold:
            regime = "BULL"
        elif t_stat < -t_threshold:
            regime = "BEAR"
        elif residual_vol > median_vol:
            regime = "CHOPPY"
        else:
            regime = "RANGING"

        # Update segment with new label
        refined_seg = seg.copy()
        refined_seg['regime'] = regime
        refined_seg['parent_regime'] = seg['regime']  # Keep original L1 label
        refined_segments.append(refined_seg)

    return refined_segments


def print_labeled_segments(segments: list[dict]):
    """Print labeled segment details with KDE metrics."""
    print(f'\nTotal segments: {len(segments)}')

    # Count by regime + sub_regime
    combo_counts = {}
    combo_bars = {}
    for seg in segments:
        key = f"{seg['regime']}_{seg['sub_regime']}"
        combo_counts[key] = combo_counts.get(key, 0) + 1
        combo_bars[key] = combo_bars.get(key, 0) + seg['bars']

    print(f'Segment counts: {combo_counts}')

    print(f'\nSegment details:')
    for i, seg in enumerate(segments):
        direction = "↑" if seg['regime'] == 'BULL' else "↓"
        sub_icon = "◆" if seg['sub_regime'] == 'CONSOLIDATION' else "→"

        print(f"  Seg {i+1}: {seg['start_date']} → {seg['end_date']}")
        print(f"          {seg['regime']} {direction} | {seg['sub_regime']} {sub_icon} | "
              f"Bars: {seg['bars']}, Change: {seg['pct_change']:+.2f}%")
        print(f"          KDE Peak: {seg['kde_peak']:.2f}, Concentration: {seg['concentration']:.2f}, R²: {seg['r_squared']:.3f}")

        if i >= 29:
            remaining = len(segments) - i - 1
            if remaining > 0:
                print(f"  ... and {remaining} more segments")
            break

    return combo_bars


def print_segments(df: pd.DataFrame, breakpoints: list[int], label: str):
    """Print segment details."""
    print(f'\n=== {label} ===')
    print(f'Total segments: {len(breakpoints) + 1}')
    print(f'Total bars: {len(df)}')
    print(f'\nSegment details:')

    # Build segment boundaries
    boundaries = [0] + breakpoints + [len(df)]

    for i in range(len(boundaries) - 1):
        start_idx = boundaries[i]
        end_idx = boundaries[i + 1] - 1

        seg = df.iloc[start_idx:end_idx + 1]
        if len(seg) == 0:
            continue

        start_price = seg['close'].iloc[0]
        end_price = seg['close'].iloc[-1]
        pct_change = ((end_price / start_price) - 1) * 100

        direction = "↑" if pct_change > 0.5 else "↓" if pct_change < -0.5 else "→"

        print(f'  Seg {i+1}: {seg.index[0]} → {seg.index[-1]}')
        print(f'          Bars: {len(seg)}, Price: ${start_price:.0f} → ${end_price:.0f} ({pct_change:+.2f}%) {direction}')


def plot_comparison(df: pd.DataFrame, results: dict, lambdas_to_plot: list[float], save_path: str = None):
    """
    Plot price with L1 trend overlays for different λ values.

    Args:
        df: DataFrame with price data
        results: Results dict from find_optimal_lambda
        lambdas_to_plot: List of λ values to show
        save_path: Optional path to save the figure
    """
    if not HAS_MATPLOTLIB:
        print("Skipping plot - matplotlib not installed")
        return

    prices = df['close'].values
    dates = df.index

    n_plots = len(lambdas_to_plot)
    fig, axes = plt.subplots(n_plots, 1, figsize=(14, 4 * n_plots), sharex=True)

    if n_plots == 1:
        axes = [axes]

    for ax, lam in zip(axes, lambdas_to_plot):
        if lam not in results:
            continue

        trend = results[lam]['trend']  # Convert back from log
        breakpoints = results[lam]['breakpoints']
        n_segs = results[lam]['n_segments']

        # Plot price
        ax.plot(dates, prices, 'b-', alpha=0.5, linewidth=0.5, label='Price')

        # Plot trend (convert from log)
        ax.plot(dates, np.exp(trend), 'r-', linewidth=1.5, label=f'L1 Trend (λ={lam})')

        # Mark breakpoints
        for bp in breakpoints:
            ax.axvline(x=dates[bp], color='green', linestyle='--', alpha=0.7, linewidth=0.8)

        ax.set_ylabel('Price ($)')
        ax.set_title(f'λ = {lam}  |  {n_segs} segments')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel('Date')

    # Format x-axis
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    axes[-1].xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.xticks(rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'\nPlot saved to: {save_path}')

    plt.show()


def get_bars_per_day(timeframe: str) -> int:
    """Return number of bars per day for a given timeframe."""
    bars_map = {
        '1m': 1440,
        '5m': 288,
        '15m': 96,
        '30m': 48,
        '1h': 24,
        '4h': 6,
        '1d': 1,
        '1w': 1/7,  # ~0.14 bars per day
    }
    return bars_map.get(timeframe, 24)


def compute_lambda_from_horizon(
    timeframe: str,
    min_segment_days: float = 7,
    penalty_factor: float = 1.5,
) -> float:
    """
    Compute λ based on target minimum segment duration.

    Args:
        timeframe: Data timeframe (e.g., '5m', '1h', '1d')
        min_segment_days: Minimum segment duration in days
        penalty_factor: Multiplier for λ (higher = smoother/fewer segments)

    Returns:
        λ value for L1 trend filter
    """
    bars_per_day = get_bars_per_day(timeframe)
    min_segment_bars = min_segment_days * bars_per_day

    # λ scales with target horizon
    # penalty_factor controls how strictly we enforce the minimum
    lambda_param = min_segment_bars * penalty_factor

    return lambda_param


def main():
    print("=== L1 Trend Filtering with KDE Classification ===\n")

    # Fetch data
    symbol = 'BTCUSDT'
    start_date = '2026-01-01'
    end_date = '2026-04-25'
    tf = '5m'
    df = fetch_ohlcv(symbol, start_date, end_date, tf, 'CRYPTO')
    print(f'Symbol: {symbol}\nStart date: {start_date}\nEnd_date: {end_date}\nTimeframe: {tf}')
    print(f'Total bars: {len(df)}')

    # Use log prices as signal
    log_prices = np.log(df['close'].values)
    n = len(log_prices)

    # Scaled λ: base_factor * n (original approach)
    k = 0.015
    scaled_lambda = k * n
    print(f'Scaled λ (k={k}): {scaled_lambda:.0f}')

    # Fit L1 trend filter
    print(f'\nFitting L1 trend filter with λ={int(scaled_lambda)}...')
    trend = l1_trend_filter(log_prices, lambda_param=scaled_lambda)
    breakpoints = detect_slope_changes(trend)

    # KDE percentile for classification (top X% = consolidation)
    kde_percentile = 70

    print(f'\n{"="*60}')
    print(f'L1 Segments with KDE-based Classification')
    print(f'{"="*60}')
    print(f'KDE percentile: {kde_percentile}% (top {100-kde_percentile}% KDE peaks = CONSOLIDATION)')

    # Label segments with KDE
    segments, kde_threshold = label_segments(df, trend, breakpoints, kde_percentile=kde_percentile)
    print(f'Computed KDE threshold: {kde_threshold:.3f}')

    combo_bars = print_labeled_segments(segments)

    # Distribution summary
    total_bars = len(df)
    print(f'\n{"="*60}')
    print(f'Distribution by regime + sub-regime (by bars):')
    print(f'{"="*60}')
    for combo, bars in sorted(combo_bars.items()):
        pct = bars / total_bars * 100
        print(f'  {combo}: {bars} bars ({pct:.1f}%)')

    # KDE statistics
    kde_peaks = [seg['kde_peak'] for seg in segments]
    concentrations = [seg['concentration'] for seg in segments]
    print(f'\nKDE Peak stats: min={min(kde_peaks):.2f}, max={max(kde_peaks):.2f}, mean={np.mean(kde_peaks):.2f}')
    print(f'Concentration stats: min={min(concentrations):.2f}, max={max(concentrations):.2f}, mean={np.mean(concentrations):.2f}')


if __name__ == "__main__":
    main()
