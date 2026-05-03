"""
Test PELT with different signals and models.

Compares:
- Signals: [returns, vol], rolling_mean, cumulative_log_returns
- Models: rbf, l2, linear

Run: python backend/scripts/test_pelt_signal.py
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

import numpy as np
import pandas as pd
import ruptures as rpt
from app.engine.data_layer import fetch_ohlcv


def print_segments(df: pd.DataFrame, changepoints: list[int], label: str):
    """Print segment details with dates and price info."""
    print(f'\n=== {label} ===')
    print(f'Total segments: {len(changepoints) - 1}')

    if len(changepoints) <= 1:
        print('  No changepoints detected')
        return

    print(f'\nSegment details:')
    for i in range(len(changepoints) - 1):
        start_idx = changepoints[i]
        end_idx = changepoints[i + 1] - 1

        start_idx = max(0, min(start_idx, len(df) - 1))
        end_idx = max(0, min(end_idx, len(df) - 1))

        seg = df.iloc[start_idx:end_idx + 1]
        if len(seg) == 0:
            continue

        start_price = seg['close'].iloc[0]
        end_price = seg['close'].iloc[-1]
        pct_change = ((end_price / start_price) - 1) * 100

        direction = "↑" if pct_change > 1 else "↓" if pct_change < -1 else "→"

        print(f'  Seg {i+1}: {seg.index[0]} → {seg.index[-1]}')
        print(f'          Bars: {len(seg)}, Change: {pct_change:+.2f}% {direction}')

        if i >= 19:
            remaining = len(changepoints) - 2 - i
            if remaining > 0:
                print(f'  ... and {remaining} more segments')
            break


def run_pelt(signal: np.ndarray, model: str, min_size: int, penalty: float) -> list[int]:
    """Run PELT and return changepoints including 0 and n."""
    algo = rpt.Pelt(model=model, min_size=min_size).fit(signal)
    cp = algo.predict(pen=penalty)

    # Ensure starts with 0
    if cp[0] != 0:
        cp = [0] + cp

    return cp


def main():
    print("=== PELT Signal Comparison Test ===\n")

    # Fetch data
    symbol = 'BTCUSDT'
    start_date = '2026-01-01'
    end_date = '2026-04-25'
    tf = '1h'

    df = fetch_ohlcv(symbol, start_date, end_date, tf, 'CRYPTO')
    print(f'Symbol: {symbol}')
    print(f'Date range: {start_date} to {end_date}')
    print(f'Timeframe: {tf}')
    print(f'Total bars: {len(df)}')

    # Parameters
    vol_window = 20
    min_size = 50

    # Compute signals
    log_returns = np.log(df['close'] / df['close'].shift(1))
    rolling_vol = log_returns.rolling(window=vol_window, min_periods=vol_window).std()
    rolling_mean = log_returns.rolling(window=vol_window, min_periods=vol_window).mean()
    cum_log_returns = log_returns.cumsum()

    # Signal 1: [returns, vol] - current volatility strategy
    signal_vol = pd.DataFrame({
        'log_returns': log_returns,
        'rolling_vol': rolling_vol,
    }).dropna()
    signal_vol_norm = (signal_vol - signal_vol.mean()) / signal_vol.std()
    signal_vol_arr = signal_vol_norm.values
    offset_vol = len(df) - len(signal_vol)

    # Signal 2: rolling_mean - directional strategy
    signal_dir = rolling_mean.dropna()
    signal_dir_norm = (signal_dir - signal_dir.mean()) / signal_dir.std()
    signal_dir_arr = signal_dir_norm.values.reshape(-1, 1)
    offset_dir = len(df) - len(signal_dir)

    # Signal 3: cumulative log returns
    signal_cum = cum_log_returns.dropna()
    signal_cum_norm = (signal_cum - signal_cum.mean()) / signal_cum.std()
    signal_cum_arr = signal_cum_norm.values.reshape(-1, 1)
    offset_cum = len(df) - len(signal_cum)

    # Default penalty
    penalty = np.log(len(df))
    print(f'\nParameters:')
    print(f'  vol_window: {vol_window}')
    print(f'  min_size: {min_size}')
    print(f'  penalty: {penalty:.2f}')

    # Test combinations
    print(f'\n{"="*70}')
    print('SIGNAL: [log_returns, rolling_vol] (Volatility Strategy)')
    print(f'{"="*70}')

    for model in ['rbf', 'l2']:
        cp = run_pelt(signal_vol_arr, model, min_size, penalty)
        # Adjust for offset
        cp_adj = [max(0, c + offset_vol) for c in cp]
        cp_adj[-1] = len(df)
        print_segments(df, cp_adj, f'Model: {model}')

    print(f'\n{"="*70}')
    print('SIGNAL: rolling_mean(log_returns) (Directional Strategy)')
    print(f'{"="*70}')

    for model in ['rbf', 'l2']:
        cp = run_pelt(signal_dir_arr, model, min_size, penalty)
        cp_adj = [max(0, c + offset_dir) for c in cp]
        cp_adj[-1] = len(df)
        print_segments(df, cp_adj, f'Model: {model}')

    print(f'\n{"="*70}')
    print('SIGNAL: cumulative_log_returns')
    print(f'{"="*70}')

    for model in ['rbf', 'l2', 'linear']:
        cp = run_pelt(signal_cum_arr, model, min_size, penalty)
        cp_adj = [max(0, c + offset_cum) for c in cp]
        cp_adj[-1] = len(df)
        print_segments(df, cp_adj, f'Model: {model}')

    # Try with lower penalty for more segments
    print(f'\n{"="*70}')
    print(f'LOWER PENALTY TEST (penalty = {penalty/2:.2f})')
    print(f'{"="*70}')

    penalty_low = penalty / 2

    cp = run_pelt(signal_dir_arr, 'rbf', min_size, penalty_low)
    cp_adj = [max(0, c + offset_dir) for c in cp]
    cp_adj[-1] = len(df)
    print_segments(df, cp_adj, 'rolling_mean + rbf + low penalty')

    cp = run_pelt(signal_vol_arr, 'rbf', min_size, penalty_low)
    cp_adj = [max(0, c + offset_vol) for c in cp]
    cp_adj[-1] = len(df)
    print_segments(df, cp_adj, '[returns, vol] + rbf + low penalty')


if __name__ == "__main__":
    main()
