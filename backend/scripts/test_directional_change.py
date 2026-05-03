"""
Directional Change (DC) Regime Detection

Time-invariant regime detection based on price reversals.
No λ parameter - only θ (reversal threshold).

Philosophy:
- Time is noise; price movement is signal
- A regime doesn't change until price actually reverses by θ%
- Small wiggles are ignored completely

Source: "High-Frequency Finance: A Directional Change Approach" (Tsang et al.)

Run: python backend/scripts/test_directional_change.py
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

from app.engine.data_layer import fetch_ohlcv


def detect_directional_changes(
    df: pd.DataFrame,
    theta: float = None,
    theta_mode: str = "fixed",
    atr_period: int = 14,
    atr_multiplier: float = 2.0,
) -> tuple[list[dict], pd.Series]:
    """
    Detect regime changes using Directional Change algorithm.

    Args:
        df: OHLCV DataFrame
        theta: Reversal threshold (e.g., 0.01 = 1%). Used when theta_mode="fixed"
        theta_mode: "fixed" or "rolling"
            - fixed: Use constant theta throughout
            - rolling: theta = atr_multiplier * ATR / price (adapts to volatility)
        atr_period: ATR period for rolling theta
        atr_multiplier: Multiplier for ATR-based theta

    Returns:
        Tuple of (segments list, regime labels Series)
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    dates = df.index

    n = len(df)
    regimes = ['UNKNOWN'] * n
    segments = []

    # Compute rolling theta if needed
    if theta_mode == "rolling":
        # Compute ATR
        high_s = df['high']
        low_s = df['low']
        close_s = df['close']

        tr1 = high_s - low_s
        tr2 = abs(high_s - close_s.shift(1))
        tr3 = abs(low_s - close_s.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        rolling_atr = tr.rolling(window=atr_period, min_periods=atr_period).mean()

        # theta = multiplier * ATR / price
        rolling_theta = (atr_multiplier * rolling_atr / close_s).values

        # Fill NaN with first valid theta
        first_valid = np.nanmean(rolling_theta[:atr_period * 2])
        rolling_theta = np.nan_to_num(rolling_theta, nan=first_valid)
    else:
        # Fixed theta
        if theta is None:
            theta = 0.02  # Default 2%
        rolling_theta = np.full(n, theta)

    # Initialize
    state = 'UPTREND'  # Start assuming uptrend
    extreme_idx = 0
    extreme_price = closes[0]
    segment_start = 0

    for i in range(1, n):
        current_theta = rolling_theta[i]

        if state == 'UPTREND':
            # Track new highs
            if highs[i] > extreme_price:
                extreme_price = highs[i]
                extreme_idx = i

            # Check for reversal using current theta
            reversal_level = extreme_price * (1 - current_theta)
            if closes[i] < reversal_level:
                # Close uptrend segment
                segments.append({
                    'start_idx': segment_start,
                    'end_idx': extreme_idx,
                    'start_date': dates[segment_start],
                    'end_date': dates[extreme_idx],
                    'regime': 'BULL',
                    'bars': extreme_idx - segment_start + 1,
                    'extreme_price': extreme_price,
                    'theta_at_reversal': current_theta,
                })

                # Mark regime labels
                for j in range(segment_start, extreme_idx + 1):
                    regimes[j] = 'BULL'

                # Switch to downtrend
                state = 'DOWNTREND'
                segment_start = extreme_idx + 1
                extreme_price = lows[i]
                extreme_idx = i

        else:  # DOWNTREND
            # Track new lows
            if lows[i] < extreme_price:
                extreme_price = lows[i]
                extreme_idx = i

            # Check for reversal using current theta
            reversal_level = extreme_price * (1 + current_theta)
            if closes[i] > reversal_level:
                # Close downtrend segment
                segments.append({
                    'start_idx': segment_start,
                    'end_idx': extreme_idx,
                    'start_date': dates[segment_start],
                    'end_date': dates[extreme_idx],
                    'regime': 'BEAR',
                    'bars': extreme_idx - segment_start + 1,
                    'extreme_price': extreme_price,
                    'theta_at_reversal': current_theta,
                })

                # Mark regime labels
                for j in range(segment_start, extreme_idx + 1):
                    regimes[j] = 'BEAR'

                # Switch to uptrend
                state = 'UPTREND'
                segment_start = extreme_idx + 1
                extreme_price = highs[i]
                extreme_idx = i

    # Close final segment
    final_regime = 'BULL' if state == 'UPTREND' else 'BEAR'
    segments.append({
        'start_idx': segment_start,
        'end_idx': n - 1,
        'start_date': dates[segment_start],
        'end_date': dates[-1],
        'regime': final_regime,
        'bars': n - segment_start,
        'extreme_price': extreme_price,
        'theta_at_reversal': rolling_theta[-1],
    })
    for j in range(segment_start, n):
        regimes[j] = final_regime

    regime_labels = pd.Series(regimes, index=dates)
    return segments, regime_labels


def compute_atr_theta(df: pd.DataFrame, atr_period: int = 14, multiplier: float = 0.5) -> float:
    """
    Compute θ based on ATR (Average True Range).

    θ = multiplier * ATR / price

    Args:
        df: OHLCV DataFrame
        atr_period: Period for ATR calculation
        multiplier: ATR multiplier (e.g., 0.5 = half ATR)

    Returns:
        Suggested θ value
    """
    high = df['high']
    low = df['low']
    close = df['close']

    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATR
    atr = tr.rolling(window=atr_period).mean().iloc[-1]

    # θ as percentage
    avg_price = close.mean()
    theta = multiplier * atr / avg_price

    return theta


def print_segments(segments: list, df: pd.DataFrame):
    """Print segment details."""
    print(f'\nTotal segments: {len(segments)}')
    print(f'\nSegment details:')

    for i, seg in enumerate(segments):
        start_price = df['close'].iloc[seg['start_idx']]
        end_price = df['close'].iloc[seg['end_idx']]
        pct_change = ((end_price / start_price) - 1) * 100

        direction = "↑" if seg['regime'] == 'BULL' else "↓"

        print(f"  Seg {i+1}: {seg['start_date']} → {seg['end_date']}")
        print(f"          Regime: {seg['regime']} {direction}, Bars: {seg['bars']}, Change: {pct_change:+.2f}%")

        if i >= 29:
            remaining = len(segments) - i - 1
            if remaining > 0:
                print(f"  ... and {remaining} more segments")
            break


def plot_dc_results(df: pd.DataFrame, segments: list, theta: float, save_path: str = None):
    """Plot price with DC regime coloring."""
    if not HAS_MATPLOTLIB:
        print("Skipping plot - matplotlib not installed")
        return

    fig, ax = plt.subplots(figsize=(14, 6))

    prices = df['close'].values
    dates = df.index

    # Plot price
    ax.plot(dates, prices, 'k-', linewidth=0.5, alpha=0.7)

    # Color segments
    colors = {'BULL': 'green', 'BEAR': 'red'}

    for seg in segments:
        start = seg['start_idx']
        end = seg['end_idx']
        color = colors.get(seg['regime'], 'gray')
        ax.axvspan(dates[start], dates[end], alpha=0.3, color=color)

        # Mark extreme point
        ax.scatter(dates[end], seg['extreme_price'], color=color, s=20, zorder=5)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', alpha=0.3, label='BULL'),
        Patch(facecolor='red', alpha=0.3, label='BEAR'),
    ]
    ax.legend(handles=legend_elements, loc='upper left')

    ax.set_xlabel('Date')
    ax.set_ylabel('Price ($)')
    ax.set_title(f'Directional Change Regime Detection | θ = {theta:.2%} | {len(segments)} segments')

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'\nPlot saved to: {save_path}')

    plt.show()


def main():
    print("=== Directional Change (DC) Regime Detection ===\n")

    # Fetch data
    df = fetch_ohlcv('BTCUSDT', '2026-03-01', '2026-04-25', '5m', 'CRYPTO')
    print(f'Total bars: {len(df)}')

    # Test fixed θ values
    print(f'\n{"="*60}')
    print('Fixed θ mode:')
    print(f'{"="*60}')

    thetas = [0.005, 0.01, 0.02, 0.03, 0.05]
    fixed_results = {}
    for theta in thetas:
        segments, regime_labels = detect_directional_changes(df, theta=theta, theta_mode="fixed")
        fixed_results[theta] = {
            'segments': segments,
            'regime_labels': regime_labels,
        }
        print(f'  θ = {theta:.1%}: {len(segments):3d} segments')

    # Test rolling θ with different multipliers
    print(f'\n{"="*60}')
    print('Rolling θ mode (θ = multiplier * ATR / price):')
    print(f'{"="*60}')

    multipliers = [1.0, 1.5, 2.0, 2.5, 3.0]
    rolling_results = {}
    for mult in multipliers:
        segments, regime_labels = detect_directional_changes(
            df, theta_mode="rolling", atr_period=14, atr_multiplier=mult
        )
        rolling_results[mult] = {
            'segments': segments,
            'regime_labels': regime_labels,
        }

        # Show theta range
        thetas_used = [s['theta_at_reversal'] for s in segments]
        min_t, max_t = min(thetas_used), max(thetas_used)
        print(f'  mult={mult:.1f}: {len(segments):3d} segments (θ range: {min_t:.2%} - {max_t:.2%})')

    # Compare fixed vs rolling
    print(f'\n{"="*60}')
    print('Comparison: Fixed θ=2% vs Rolling mult=2.0')
    print(f'{"="*60}')

    fixed_segs = fixed_results[0.02]['segments']
    rolling_segs = rolling_results[2.0]['segments']

    print(f'\nFixed θ=2%: {len(fixed_segs)} segments')
    print(f'Rolling mult=2.0: {len(rolling_segs)} segments')

    # Show rolling θ results
    print(f'\n{"="*60}')
    print('Rolling θ (mult=2.0) - Segment details:')
    print(f'{"="*60}')
    print_segments(rolling_segs, df)

    # Regime distribution for rolling
    regime_labels = rolling_results[2.0]['regime_labels']
    bull_pct = (regime_labels == 'BULL').sum() / len(regime_labels) * 100
    bear_pct = (regime_labels == 'BEAR').sum() / len(regime_labels) * 100
    print(f'\nRegime distribution (rolling):')
    print(f'  BULL: {bull_pct:.1f}%')
    print(f'  BEAR: {bear_pct:.1f}%')

    # Plot comparison: fixed vs rolling
    if HAS_MATPLOTLIB:
        fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

        prices = df['close'].values
        dates = df.index
        colors = {'BULL': 'green', 'BEAR': 'red'}

        # Fixed θ=2%
        ax = axes[0]
        ax.plot(dates, prices, 'k-', linewidth=0.5, alpha=0.7)
        for seg in fixed_segs:
            start, end = seg['start_idx'], seg['end_idx']
            ax.axvspan(dates[start], dates[end], alpha=0.3, color=colors[seg['regime']])
        ax.set_title(f'Fixed θ = 2.0% | {len(fixed_segs)} segments')
        ax.set_ylabel('Price ($)')

        # Rolling θ
        ax = axes[1]
        ax.plot(dates, prices, 'k-', linewidth=0.5, alpha=0.7)
        for seg in rolling_segs:
            start, end = seg['start_idx'], seg['end_idx']
            ax.axvspan(dates[start], dates[end], alpha=0.3, color=colors[seg['regime']])
        ax.set_title(f'Rolling θ (mult=2.0) | {len(rolling_segs)} segments')
        ax.set_ylabel('Price ($)')
        ax.set_xlabel('Date')

        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.tight_layout()
        plt.savefig('dc_fixed_vs_rolling.png', dpi=150, bbox_inches='tight')
        print(f'\nComparison plot saved to: dc_fixed_vs_rolling.png')
        plt.show()


if __name__ == "__main__":
    main()
