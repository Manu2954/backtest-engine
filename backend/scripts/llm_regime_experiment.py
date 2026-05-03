"""
LLM-Guided Regime Detection Experimentation

Runs regime detection experiments with different parameters,
sends results to local LLM for analysis, and gets suggestions
for next experiments.

Prerequisites:
    - llama.cpp server running on 192.168.1.6:8080
    - Phi-3 or similar model loaded

Run: python backend/scripts/llm_regime_experiment.py
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

import json
import requests
import numpy as np
import pandas as pd
from typing import Any

from app.engine.data_layer import fetch_ohlcv

# LLM Configuration
LLM_URL = "http://192.168.1.6:8080/v1/chat/completions"
LLM_MODEL = "Phi-3-mini-4k-instruct-q4.gguf"


def ask_llm(prompt: str, max_tokens: int = 500) -> str:
    """Send prompt to local LLM and get response."""
    try:
        response = requests.post(
            LLM_URL,
            headers={"Content-Type": "application/json"},
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LLM Error: {e}"


# ============================================================================
# L1 Trend Filter Implementation
# ============================================================================

def l1_trend_filter(y: np.ndarray, lambda_param: float = 1.0) -> np.ndarray:
    """L1 trend filtering using cvxpy."""
    import cvxpy as cp

    n = len(y)
    x = cp.Variable(n)

    D2 = np.zeros((n - 2, n))
    for i in range(n - 2):
        D2[i, i] = 1
        D2[i, i + 1] = -2
        D2[i, i + 2] = 1

    objective = cp.Minimize(
        cp.sum_squares(y - x) + lambda_param * cp.norm(D2 @ x, 1)
    )

    prob = cp.Problem(objective)
    prob.solve(solver=cp.CLARABEL)

    return x.value


def detect_slope_changes(trend: np.ndarray, threshold: float = 1e-6) -> list[int]:
    """Detect where slope changes sign in the filtered trend."""
    slope = np.diff(trend)
    breakpoints = []
    for i in range(1, len(slope)):
        if slope[i-1] * slope[i] < 0:
            if abs(slope[i] - slope[i-1]) > threshold:
                breakpoints.append(i)
    return breakpoints


def run_l1_experiment(
    df: pd.DataFrame,
    k: float = 0.015,
) -> dict[str, Any]:
    """Run L1 trend filter experiment with given parameters."""
    log_prices = np.log(df['close'].values)
    n = len(log_prices)

    scaled_lambda = k * n

    trend = l1_trend_filter(log_prices, lambda_param=scaled_lambda)
    breakpoints = detect_slope_changes(trend)

    # Build segments
    boundaries = [0] + breakpoints + [len(df)]
    segments = []

    for i in range(len(boundaries) - 1):
        start_idx = boundaries[i]
        end_idx = boundaries[i + 1] - 1
        seg = df.iloc[start_idx:end_idx + 1]

        if len(seg) == 0:
            continue

        start_price = seg['close'].iloc[0]
        end_price = seg['close'].iloc[-1]
        pct_change = ((end_price / start_price) - 1) * 100

        # Compute slope direction
        seg_trend = trend[start_idx:end_idx + 1]
        slope = (seg_trend[-1] - seg_trend[0]) / len(seg_trend) if len(seg_trend) > 1 else 0
        regime = "BULL" if slope > 0 else "BEAR"

        segments.append({
            'start_date': str(seg.index[0]),
            'end_date': str(seg.index[-1]),
            'regime': regime,
            'bars': len(seg),
            'pct_change': round(pct_change, 2),
        })

    # Compute statistics
    bull_segs = [s for s in segments if s['regime'] == 'BULL']
    bear_segs = [s for s in segments if s['regime'] == 'BEAR']

    return {
        'method': 'L1',
        'params': {'k': k, 'lambda': round(scaled_lambda, 0)},
        'total_bars': len(df),
        'num_segments': len(segments),
        'bull_segments': len(bull_segs),
        'bear_segments': len(bear_segs),
        'avg_segment_bars': round(np.mean([s['bars'] for s in segments]), 1) if segments else 0,
        'min_segment_bars': min([s['bars'] for s in segments]) if segments else 0,
        'max_segment_bars': max([s['bars'] for s in segments]) if segments else 0,
        'segments': segments[:10],  # First 10 for context
    }


# ============================================================================
# PELT Implementation
# ============================================================================

def run_pelt_experiment(
    df: pd.DataFrame,
    signal_type: str = "rolling_mean",
    model: str = "rbf",
    penalty_multiplier: float = 1.0,
    min_size: int = 50,
    vol_window: int = 20,
    r2_mode: str = "percentile",
    r2_percentile: float = 75,
) -> dict[str, Any]:
    """Run PELT experiment with production-style labeling."""
    import ruptures as rpt
    from scipy import stats

    log_returns = np.log(df['close'] / df['close'].shift(1))

    # Prepare signal based on type
    if signal_type == "rolling_mean":
        signal = log_returns.rolling(window=vol_window, min_periods=vol_window).mean().dropna()
        signal_norm = (signal - signal.mean()) / signal.std()
        signal_arr = signal_norm.values.reshape(-1, 1)
    elif signal_type == "returns_vol":
        rolling_vol = log_returns.rolling(window=vol_window, min_periods=vol_window).std()
        signal = pd.DataFrame({
            'log_returns': log_returns,
            'rolling_vol': rolling_vol,
        }).dropna()
        signal_norm = (signal - signal.mean()) / signal.std()
        signal_arr = signal_norm.values
    else:
        raise ValueError(f"Unknown signal_type: {signal_type}")

    offset = len(df) - len(signal_arr)

    # Default penalty
    n = len(signal_arr)
    penalty = np.log(n) * penalty_multiplier

    # Run PELT
    algo = rpt.Pelt(model=model, min_size=min_size).fit(signal_arr)
    changepoints = algo.predict(pen=penalty)

    # Adjust indices
    changepoints = [max(0, cp + offset) for cp in changepoints]
    if changepoints[0] != 0:
        changepoints = [0] + changepoints
    changepoints[-1] = len(df)

    # Compute features for each segment (production-style)
    segment_features = []
    for i in range(len(changepoints) - 1):
        start_idx = changepoints[i]
        end_idx = changepoints[i + 1]
        segment = df.iloc[start_idx:end_idx]

        if len(segment) < 3:
            segment_features.append({
                'slope': 0.0,
                'r_squared': 0.0,
                'mean_return': 0.0,
                'std_return': 0.0,
            })
            continue

        # OLS regression on close prices
        y = segment['close'].values
        x = np.arange(len(y))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Normalize slope by mean price (percentage slope per bar)
        mean_price = y.mean()
        slope_pct = (slope / mean_price) * 100 if mean_price != 0 else 0.0

        # R²
        r_squared = r_value ** 2

        # Returns stats
        returns = segment['close'].pct_change().dropna()
        mean_return = returns.mean() * 100 if len(returns) > 0 else 0.0
        std_return = returns.std() * 100 if len(returns) > 0 else 0.0

        segment_features.append({
            'slope': slope_pct,
            'r_squared': r_squared,
            'mean_return': mean_return,
            'std_return': std_return,
        })

    # Compute R² threshold based on mode
    all_r2 = [f['r_squared'] for f in segment_features]
    if r2_mode == "percentile":
        r2_threshold = np.percentile(all_r2, r2_percentile) if all_r2 else 0.3
    else:
        r2_threshold = 0.3

    # Compute median std_return for CHOPPY vs RANGING
    all_stds = [f['std_return'] for f in segment_features]
    median_std = np.median(all_stds) if all_stds else 0.0

    # Label segments (production-style)
    segments = []
    regime_counts = {'BULL': 0, 'BEAR': 0, 'CHOPPY': 0, 'RANGING': 0}

    for i, features in enumerate(segment_features):
        start_idx = changepoints[i]
        end_idx = changepoints[i + 1] - 1
        seg = df.iloc[start_idx:end_idx + 1]

        if len(seg) == 0:
            continue

        slope = features['slope']
        r_squared = features['r_squared']
        std_return = features['std_return']

        start_price = seg['close'].iloc[0]
        end_price = seg['close'].iloc[-1]
        pct_change = ((end_price / start_price) - 1) * 100

        # Production labeling rules
        SLOPE_TOLERANCE = 1e-6
        if r_squared >= r2_threshold and abs(slope) > SLOPE_TOLERANCE:
            # Directional regime
            regime = "BULL" if slope > 0 else "BEAR"
        else:
            # Sideways regime
            regime = "CHOPPY" if std_return > median_std else "RANGING"

        regime_counts[regime] += 1

        segments.append({
            'start_date': str(seg.index[0]),
            'end_date': str(seg.index[-1]),
            'regime': regime,
            'bars': len(seg),
            'pct_change': round(pct_change, 2),
            'r_squared': round(r_squared, 3),
            'slope': round(slope, 4),
        })

    return {
        'method': 'PELT',
        'params': {
            'signal_type': signal_type,
            'model': model,
            'penalty_multiplier': penalty_multiplier,
            'penalty': round(penalty, 2),
            'min_size': min_size,
            'vol_window': vol_window,
            'r2_threshold': round(r2_threshold, 3),
        },
        'total_bars': len(df),
        'num_segments': len(segments),
        'bull_segments': regime_counts['BULL'],
        'bear_segments': regime_counts['BEAR'],
        'choppy_segments': regime_counts['CHOPPY'],
        'ranging_segments': regime_counts['RANGING'],
        'avg_segment_bars': round(np.mean([s['bars'] for s in segments]), 1) if segments else 0,
        'min_segment_bars': min([s['bars'] for s in segments]) if segments else 0,
        'max_segment_bars': max([s['bars'] for s in segments]) if segments else 0,
        'segments': segments[:10],
    }


# ============================================================================
# Main Experiment Loop
# ============================================================================

def run_experiment_batch(df: pd.DataFrame, timeframe: str) -> list[dict]:
    """Run a batch of experiments with different configurations."""
    results = []

    # L1 experiments with different k values
    for k in [0.01, 0.015, 0.02, 0.03]:
        print(f"  Running L1 with k={k}...")
        try:
            result = run_l1_experiment(df, k=k)
            results.append(result)
        except Exception as e:
            print(f"    Error: {e}")

    # PELT experiments (pen=0.5 removed: over-segments)
    configs = [
        {"signal_type": "rolling_mean", "model": "rbf", "penalty_multiplier": 1.0},
        {"signal_type": "rolling_mean", "model": "rbf", "penalty_multiplier": 2.0},
        {"signal_type": "returns_vol", "model": "rbf", "penalty_multiplier": 1.0},
    ]

    for config in configs:
        print(f"  Running PELT with {config}...")
        try:
            result = run_pelt_experiment(df, **config)
            results.append(result)
        except Exception as e:
            print(f"    Error: {e}")

    return results


def format_results_for_llm(results: list[dict], symbol: str, timeframe: str, date_range: str) -> str:
    """Format experiment results for LLM analysis."""
    summary = f"""
Regime Detection Experiment Results
====================================
Symbol: {symbol}
Timeframe: {timeframe}
Date Range: {date_range}
Total Bars: {results[0]['total_bars'] if results else 'N/A'}

Results Summary:
"""
    for i, r in enumerate(results):
        if r['method'] == 'PELT':
            summary += f"""
Experiment {i+1}: {r['method']}
  Params: {json.dumps(r['params'])}
  Segments: {r['num_segments']} (BULL: {r['bull_segments']}, BEAR: {r['bear_segments']}, CHOPPY: {r.get('choppy_segments', 0)}, RANGING: {r.get('ranging_segments', 0)})
  Segment sizes: min={r['min_segment_bars']}, avg={r['avg_segment_bars']}, max={r['max_segment_bars']}
"""
        else:
            summary += f"""
Experiment {i+1}: {r['method']}
  Params: {json.dumps(r['params'])}
  Segments: {r['num_segments']} (BULL: {r['bull_segments']}, BEAR: {r['bear_segments']})
  Segment sizes: min={r['min_segment_bars']}, avg={r['avg_segment_bars']}, max={r['max_segment_bars']}
"""

    return summary


def main():
    print("=== LLM-Guided Regime Detection Experiment ===\n")

    # Test LLM connection
    print("Testing LLM connection...")
    test_response = ask_llm("Say 'OK' if you can read this.", max_tokens=10)
    if "Error" in test_response:
        print(f"LLM connection failed: {test_response}")
        return
    print(f"LLM connected: {test_response.strip()}\n")

    # Experiment configuration
    symbol = 'BTCUSDT'
    timeframe = '1h'
    start_date = '2025-01-01'
    end_date = '2026-04-25'

    print(f"Fetching data: {symbol} {timeframe} from {start_date} to {end_date}")
    df = fetch_ohlcv(symbol, start_date, end_date, timeframe, 'CRYPTO')
    print(f"Total bars: {len(df)}\n")

    # Run experiments
    print("Running experiments...")
    results = run_experiment_batch(df, timeframe)

    # Format results
    results_summary = format_results_for_llm(
        results, symbol, timeframe, f"{start_date} to {end_date}"
    )

    print("\n" + "="*60)
    print("EXPERIMENT RESULTS")
    print("="*60)
    print(results_summary)

    # Ask LLM for analysis
    analysis_prompt = f"""
You are analyzing regime detection experiment results for trading strategy development.

{results_summary}

Please analyze these results and answer:
1. Which method/configuration produced the most reasonable segmentation? (not too few, not too many segments)
2. Are there any concerning patterns (e.g., segments too short or too long)?
3. What parameters should we try next to improve the results?

Be concise and specific.
"""

    print("\n" + "="*60)
    print("LLM ANALYSIS")
    print("="*60)

    analysis = ask_llm(analysis_prompt, max_tokens=500)
    print(analysis)

    # Save results
    output = {
        'config': {
            'symbol': symbol,
            'timeframe': timeframe,
            'date_range': f"{start_date} to {end_date}",
        },
        'results': results,
        'llm_analysis': analysis,
    }

    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'regime_experiment_{timestamp_str}.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
