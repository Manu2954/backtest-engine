"""
Test FDI (Fractal Dimension Index) and Shannon Entropy for regime detection.

Uses rolling FDI/Entropy to classify market regimes directly from price data
without L1 trend filtering.

FDI Interpretation:
- ~1.0: Straight line (clean trend)
- ~1.5: Random walk (Brownian motion)
- ~2.0: Space-filling (very choppy/mean-reverting)

Entropy Interpretation:
- Low (~1-2): Predictable direction (trending)
- High (~3+): Uncertain direction (consolidation)

Run: python backend/scripts/test_fdi_entropy_regime.py
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Plots will be skipped.")

from app.engine.data_layer import fetch_ohlcv


def compute_fdi_higuchi(y: np.ndarray, k_max: int = 10) -> float:
    """
    Compute Fractal Dimension using Higuchi's method.

    Args:
        y: Price series (log prices recommended)
        k_max: Maximum interval for curve length calculation

    Returns:
        Fractal dimension (1.0 to 2.0)
    """
    n = len(y)
    if n < k_max * 2:
        k_max = max(2, n // 4)

    L = []
    k_values = []

    for k in range(1, k_max + 1):
        Lk = []
        for m in range(1, k + 1):
            indices = np.arange(m - 1, n, k)
            if len(indices) < 2:
                continue

            subsequence = y[indices]
            length = np.sum(np.abs(np.diff(subsequence)))

            num_points = len(indices)
            norm_factor = (n - 1) / (k * ((num_points - 1) * k))
            Lk.append(length * norm_factor)

        if Lk:
            L.append(np.mean(Lk))
            k_values.append(k)

    if len(L) < 2:
        return 1.5

    log_k = np.log(1 / np.array(k_values))
    log_L = np.log(np.array(L))

    slope, _ = np.polyfit(log_k, log_L, 1)

    return np.clip(slope, 1.0, 2.0)


def compute_shannon_entropy(returns: np.ndarray, n_bins: int = 10) -> float:
    """
    Compute Shannon Entropy of returns distribution.

    Args:
        returns: Log returns series
        n_bins: Number of bins for histogram

    Returns:
        Shannon entropy (higher = more random)
    """
    if len(returns) < n_bins:
        n_bins = max(2, len(returns) // 2)

    counts, _ = np.histogram(returns, bins=n_bins)
    probs = counts / counts.sum()
    probs = probs[probs > 0]

    entropy = -np.sum(probs * np.log2(probs))

    return entropy


def compute_rolling_fdi_entropy(
    df: pd.DataFrame,
    window_size: int = 50,
) -> pd.DataFrame:
    """
    Compute rolling FDI and Entropy for each bar.

    Args:
        df: OHLCV DataFrame
        window_size: Rolling window size

    Returns:
        DataFrame with FDI and Entropy columns
    """
    log_prices = np.log(df['close'].values)
    n = len(log_prices)

    fdis = [np.nan] * n
    entropies = [np.nan] * n

    for i in range(window_size, n):
        window = log_prices[i - window_size:i]
        returns = np.diff(window)

        fdis[i] = compute_fdi_higuchi(window)
        entropies[i] = compute_shannon_entropy(returns)

    result = df.copy()
    result['fdi'] = fdis
    result['entropy'] = entropies

    return result


def classify_regime(fdi: float, entropy: float, slope: float,
                    fdi_threshold: float = 1.4,
                    entropy_threshold: float = 2.5) -> str:
    """
    Classify regime based on FDI, Entropy, and slope.

    Args:
        fdi: Fractal Dimension Index
        entropy: Shannon Entropy
        slope: Price slope (positive = up, negative = down)
        fdi_threshold: FDI threshold for trending vs consolidation
        entropy_threshold: Entropy threshold for trending vs consolidation

    Returns:
        Regime label: BULL, BEAR, CHOPPY, or RANGING
    """
    # Use FDI as primary classifier
    is_trending = fdi < fdi_threshold

    if is_trending:
        if slope > 0:
            return "BULL"
        else:
            return "BEAR"
    else:
        # Consolidation - use entropy to distinguish CHOPPY vs RANGING
        if entropy > entropy_threshold:
            return "CHOPPY"
        else:
            return "RANGING"


def detect_regimes_fdi_entropy(
    df: pd.DataFrame,
    window_size: int = 50,
    fdi_threshold: float = 1.4,
    entropy_threshold: float = 2.5,
    min_segment_size: int = 20,
) -> tuple[list[dict], pd.Series]:
    """
    Detect regimes using FDI and Entropy.

    Args:
        df: OHLCV DataFrame
        window_size: Rolling window for FDI/Entropy calculation
        fdi_threshold: FDI threshold for trending
        entropy_threshold: Entropy threshold for CHOPPY vs RANGING
        min_segment_size: Minimum bars to confirm regime change

    Returns:
        Tuple of (segments list, regime labels Series)
    """
    # Compute rolling metrics
    df_metrics = compute_rolling_fdi_entropy(df, window_size)

    log_prices = np.log(df['close'].values)
    n = len(df)

    # Compute rolling slope
    slopes = [np.nan] * n
    for i in range(window_size, n):
        window = log_prices[i - window_size:i]
        x = np.arange(window_size)
        slope, _ = np.polyfit(x, window, 1)
        slopes[i] = slope

    df_metrics['slope'] = slopes

    # Classify each bar
    regimes = ['UNKNOWN'] * n
    for i in range(window_size, n):
        fdi = df_metrics['fdi'].iloc[i]
        entropy = df_metrics['entropy'].iloc[i]
        slope = df_metrics['slope'].iloc[i]

        if pd.notna(fdi) and pd.notna(entropy) and pd.notna(slope):
            regimes[i] = classify_regime(fdi, entropy, slope,
                                         fdi_threshold, entropy_threshold)

    # Apply smoothing: require min_segment_size consecutive bars
    smoothed_regimes = regimes.copy()

    i = window_size
    while i < n:
        current = regimes[i]
        if current == 'UNKNOWN':
            i += 1
            continue

        # Count consecutive same regime
        j = i
        while j < n and regimes[j] == current:
            j += 1

        consecutive = j - i

        if consecutive < min_segment_size and i > window_size:
            # Too short - merge with previous
            prev_regime = smoothed_regimes[i - 1]
            for k in range(i, j):
                smoothed_regimes[k] = prev_regime

        i = j

    # Build segments from smoothed regimes
    segments = []
    current_regime = smoothed_regimes[window_size]
    seg_start = window_size

    for i in range(window_size + 1, n):
        if smoothed_regimes[i] != current_regime:
            # Close segment
            seg_df = df.iloc[seg_start:i]
            if len(seg_df) > 0:
                start_price = seg_df['close'].iloc[0]
                end_price = seg_df['close'].iloc[-1]
                pct_change = ((end_price / start_price) - 1) * 100

                # Average FDI/Entropy for segment
                seg_fdi = df_metrics['fdi'].iloc[seg_start:i].mean()
                seg_entropy = df_metrics['entropy'].iloc[seg_start:i].mean()

                segments.append({
                    'start_idx': seg_start,
                    'end_idx': i - 1,
                    'start_date': seg_df.index[0],
                    'end_date': seg_df.index[-1],
                    'regime': current_regime,
                    'bars': len(seg_df),
                    'fdi': seg_fdi,
                    'entropy': seg_entropy,
                    'pct_change': pct_change,
                    'start_price': start_price,
                    'end_price': end_price,
                })

            current_regime = smoothed_regimes[i]
            seg_start = i

    # Close final segment
    seg_df = df.iloc[seg_start:n]
    if len(seg_df) > 0:
        start_price = seg_df['close'].iloc[0]
        end_price = seg_df['close'].iloc[-1]
        pct_change = ((end_price / start_price) - 1) * 100
        seg_fdi = df_metrics['fdi'].iloc[seg_start:n].mean()
        seg_entropy = df_metrics['entropy'].iloc[seg_start:n].mean()

        segments.append({
            'start_idx': seg_start,
            'end_idx': n - 1,
            'start_date': seg_df.index[0],
            'end_date': seg_df.index[-1],
            'regime': current_regime,
            'bars': len(seg_df),
            'fdi': seg_fdi,
            'entropy': seg_entropy,
            'pct_change': pct_change,
            'start_price': start_price,
            'end_price': end_price,
        })

    regime_labels = pd.Series(smoothed_regimes, index=df.index)

    return segments, regime_labels


def print_segments(segments: list[dict]):
    """Print segment details."""
    print(f'\nTotal segments: {len(segments)}')

    # Count by regime
    regime_counts = {}
    regime_bars = {}
    for seg in segments:
        regime_counts[seg['regime']] = regime_counts.get(seg['regime'], 0) + 1
        regime_bars[seg['regime']] = regime_bars.get(seg['regime'], 0) + seg['bars']

    print(f'Regime counts: {regime_counts}')

    print(f'\nSegment details:')
    for i, seg in enumerate(segments):
        if seg['regime'] == 'BULL':
            icon = "↑"
        elif seg['regime'] == 'BEAR':
            icon = "↓"
        else:
            icon = "→"

        print(f"  Seg {i+1}: {seg['start_date']} → {seg['end_date']}")
        print(f"          {seg['regime']} {icon} | Bars: {seg['bars']}, Change: {seg['pct_change']:+.2f}%")
        print(f"          FDI: {seg['fdi']:.3f}, Entropy: {seg['entropy']:.2f}")

        if i >= 29:
            remaining = len(segments) - i - 1
            if remaining > 0:
                print(f"  ... and {remaining} more segments")
            break

    return regime_bars


def plot_regimes(df: pd.DataFrame, segments: list[dict], save_path: str = None):
    """Plot price with regime coloring."""
    if not HAS_MATPLOTLIB:
        print("Skipping plot - matplotlib not installed")
        return

    fig, ax = plt.subplots(figsize=(14, 6))

    prices = df['close'].values
    dates = df.index

    # Plot price
    ax.plot(dates, prices, 'k-', linewidth=0.5, alpha=0.7)

    # Color segments
    colors = {
        'BULL': 'green',
        'BEAR': 'red',
        'CHOPPY': 'orange',
        'RANGING': 'blue',
        'UNKNOWN': 'gray',
    }

    for seg in segments:
        start = seg['start_idx']
        end = seg['end_idx']
        color = colors.get(seg['regime'], 'gray')
        ax.axvspan(dates[start], dates[end], alpha=0.3, color=color)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', alpha=0.3, label='BULL'),
        Patch(facecolor='red', alpha=0.3, label='BEAR'),
        Patch(facecolor='orange', alpha=0.3, label='CHOPPY'),
        Patch(facecolor='blue', alpha=0.3, label='RANGING'),
    ]
    ax.legend(handles=legend_elements, loc='upper left')

    ax.set_xlabel('Date')
    ax.set_ylabel('Price ($)')
    ax.set_title(f'FDI/Entropy Regime Detection | {len(segments)} segments')

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'\nPlot saved to: {save_path}')

    plt.show()


def main():
    print("=== FDI/Entropy Regime Detection (Standalone) ===\n")

    # Fetch data
    symbol = 'BTCUSDT'
    start_date = '2024-03-01'
    end_date = '2026-04-25'
    tf = '1h'
    df = fetch_ohlcv(symbol, start_date, end_date, tf, 'CRYPTO')
    print(f'Symbol: {symbol}')
    print(f'Date range: {start_date} to {end_date}')
    print(f'Timeframe: {tf}')
    print(f'Total bars: {len(df)}')

    # Parameters
    window_size = 50
    fdi_threshold = 1.4
    entropy_threshold = 2.5
    min_segment_size = 24  # 1 day for 1h data

    print(f'\nParameters:')
    print(f'  Window size: {window_size} bars')
    print(f'  FDI threshold: {fdi_threshold} (< = trending, >= = consolidation)')
    print(f'  Entropy threshold: {entropy_threshold} (for CHOPPY vs RANGING)')
    print(f'  Min segment size: {min_segment_size} bars')

    # Detect regimes
    print(f'\nDetecting regimes...')
    segments, regime_labels = detect_regimes_fdi_entropy(
        df,
        window_size=window_size,
        fdi_threshold=fdi_threshold,
        entropy_threshold=entropy_threshold,
        min_segment_size=min_segment_size,
    )

    print(f'\n{"="*60}')
    print(f'Results')
    print(f'{"="*60}')

    regime_bars = print_segments(segments)

    # Distribution
    total_bars = len(df) - window_size  # Exclude warmup
    print(f'\n{"="*60}')
    print(f'Regime Distribution (by bars)')
    print(f'{"="*60}')
    for regime, bars in sorted(regime_bars.items()):
        if regime != 'UNKNOWN':
            pct = bars / total_bars * 100
            print(f'  {regime}: {bars} bars ({pct:.1f}%)')

    # FDI/Entropy stats
    fdis = [seg['fdi'] for seg in segments if seg['regime'] != 'UNKNOWN']
    entropies = [seg['entropy'] for seg in segments if seg['regime'] != 'UNKNOWN']

    if fdis:
        print(f'\nFDI stats: min={min(fdis):.3f}, max={max(fdis):.3f}, mean={np.mean(fdis):.3f}')
        print(f'Entropy stats: min={min(entropies):.2f}, max={max(entropies):.2f}, mean={np.mean(entropies):.2f}')

    # Plot
    if HAS_MATPLOTLIB:
        plot_regimes(df, segments, save_path='fdi_entropy_regimes.png')


if __name__ == "__main__":
    main()
