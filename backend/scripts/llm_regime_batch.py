"""
LLM-Guided Regime Detection - Batch Mode

Runs all combinations of:
- Timeframes: 5m, 1h, 4h, 1d
- Date ranges: 2021 bull, 2022 bear, 2023-24 recovery, 2025-26 recent
- Methods: L1, PELT variants

Sends consolidated results to LLM for comparative analysis.

Prerequisites:
    - llama.cpp server running on 192.168.1.6:8080

Run: python backend/scripts/llm_regime_batch.py
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

import json
import requests
import numpy as np
import pandas as pd
import warnings
from typing import Any
from datetime import datetime

from app.engine.data_layer import fetch_ohlcv

# Suppress cvxpy numerical warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, module='cvxpy')

# LLM Configuration
LLM_URL = "http://192.168.1.6:8080/v1/chat/completions"
LLM_MODEL = "Phi-3-mini-4k-instruct-q4.gguf"

# Test Configurations
TIMEFRAMES = ["1h", "4h", "1d"]  # 5m skipped - separate analysis planned

DATE_RANGES = {
    "2021_bull": ("2021-01-01", "2021-11-15"),      # BTC 29k → 69k
    "2022_bear": ("2021-11-15", "2022-11-15"),      # BTC 69k → 16k
    "2023_recovery": ("2022-11-15", "2024-01-01"),  # BTC 16k → 45k
    "2025_recent": ("2025-01-01", "2026-04-25"),    # Recent data
}

SYMBOL = "BTCUSDT"


def ask_llm(prompt: str, max_tokens: int = 1000) -> str:
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
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LLM Error: {e}"


# ============================================================================
# L1 Trend Filter
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
    """Detect where slope changes sign."""
    slope = np.diff(trend)
    breakpoints = []
    for i in range(1, len(slope)):
        if slope[i-1] * slope[i] < 0:
            if abs(slope[i] - slope[i-1]) > threshold:
                breakpoints.append(i)
    return breakpoints


def run_l1_experiment(df: pd.DataFrame, k: float = 0.015) -> dict[str, Any]:
    """Run L1 trend filter experiment."""
    if len(df) < 50:
        return {"method": "L1", "error": "insufficient_data", "bars": len(df)}

    log_prices = np.log(df['close'].values)
    n = len(log_prices)
    scaled_lambda = k * n

    try:
        trend = l1_trend_filter(log_prices, lambda_param=scaled_lambda)
        breakpoints = detect_slope_changes(trend)
    except Exception as e:
        return {"method": "L1", "error": str(e), "bars": len(df)}

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

        seg_trend = trend[start_idx:end_idx + 1]
        slope = (seg_trend[-1] - seg_trend[0]) / len(seg_trend) if len(seg_trend) > 1 else 0
        regime = "BULL" if slope > 0 else "BEAR"

        segments.append({
            'regime': regime,
            'bars': len(seg),
            'pct_change': round(pct_change, 2),
        })

    bull_segs = [s for s in segments if s['regime'] == 'BULL']
    bear_segs = [s for s in segments if s['regime'] == 'BEAR']

    return {
        'method': 'L1',
        'params': {'k': k},
        'total_bars': len(df),
        'num_segments': len(segments),
        'bull_segments': len(bull_segs),
        'bear_segments': len(bear_segs),
        'avg_segment_bars': round(np.mean([s['bars'] for s in segments]), 1) if segments else 0,
        'min_segment_bars': min([s['bars'] for s in segments]) if segments else 0,
        'max_segment_bars': max([s['bars'] for s in segments]) if segments else 0,
    }


# ============================================================================
# PELT
# ============================================================================

def run_pelt_experiment(
    df: pd.DataFrame,
    signal_type: str = "rolling_mean",
    penalty_multiplier: float = 1.0,
    min_size: int = 50,
    vol_window: int = 20,
    r2_percentile: float = 75,
) -> dict[str, Any]:
    """Run PELT experiment with production-style labeling."""
    import ruptures as rpt
    from scipy import stats

    if len(df) < min_size + vol_window:
        return {"method": "PELT", "error": "insufficient_data", "bars": len(df)}

    log_returns = np.log(df['close'] / df['close'].shift(1))

    # Prepare signal
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
        return {"method": "PELT", "error": f"unknown_signal: {signal_type}"}

    offset = len(df) - len(signal_arr)
    n = len(signal_arr)
    penalty = np.log(n) * penalty_multiplier

    try:
        algo = rpt.Pelt(model="rbf", min_size=min_size).fit(signal_arr)
        changepoints = algo.predict(pen=penalty)
    except Exception as e:
        return {"method": "PELT", "error": str(e), "bars": len(df)}

    changepoints = [max(0, cp + offset) for cp in changepoints]
    if changepoints[0] != 0:
        changepoints = [0] + changepoints
    changepoints[-1] = len(df)

    # Compute features for labeling
    segment_features = []
    for i in range(len(changepoints) - 1):
        start_idx = changepoints[i]
        end_idx = changepoints[i + 1]
        segment = df.iloc[start_idx:end_idx]

        if len(segment) < 3:
            segment_features.append({
                'slope': 0.0, 'r_squared': 0.0, 'mean_return': 0.0, 'std_return': 0.0,
            })
            continue

        y = segment['close'].values
        x = np.arange(len(y))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        mean_price = y.mean()
        slope_pct = (slope / mean_price) * 100 if mean_price != 0 else 0.0
        r_squared = r_value ** 2

        returns = segment['close'].pct_change().dropna()
        mean_return = returns.mean() * 100 if len(returns) > 0 else 0.0
        std_return = returns.std() * 100 if len(returns) > 0 else 0.0

        segment_features.append({
            'slope': slope_pct,
            'r_squared': r_squared,
            'mean_return': mean_return,
            'std_return': std_return,
        })

    # Thresholds
    all_r2 = [f['r_squared'] for f in segment_features]
    r2_threshold = np.percentile(all_r2, r2_percentile) if all_r2 else 0.3
    all_stds = [f['std_return'] for f in segment_features]
    median_std = np.median(all_stds) if all_stds else 0.0

    # Label segments
    regime_counts = {'BULL': 0, 'BEAR': 0, 'CHOPPY': 0, 'RANGING': 0}
    segments_info = []

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

        SLOPE_TOLERANCE = 1e-6
        if r_squared >= r2_threshold and abs(slope) > SLOPE_TOLERANCE:
            regime = "BULL" if slope > 0 else "BEAR"
        else:
            regime = "CHOPPY" if std_return > median_std else "RANGING"

        regime_counts[regime] += 1
        segments_info.append({
            'regime': regime,
            'bars': len(seg),
            'pct_change': round(pct_change, 2),
        })

    return {
        'method': 'PELT',
        'params': {
            'signal_type': signal_type,
            'penalty_multiplier': penalty_multiplier,
        },
        'total_bars': len(df),
        'num_segments': len(segments_info),
        'bull_segments': regime_counts['BULL'],
        'bear_segments': regime_counts['BEAR'],
        'choppy_segments': regime_counts['CHOPPY'],
        'ranging_segments': regime_counts['RANGING'],
        'avg_segment_bars': round(np.mean([s['bars'] for s in segments_info]), 1) if segments_info else 0,
        'min_segment_bars': min([s['bars'] for s in segments_info]) if segments_info else 0,
        'max_segment_bars': max([s['bars'] for s in segments_info]) if segments_info else 0,
    }


# ============================================================================
# Batch Runner
# ============================================================================

def run_all_experiments() -> dict[str, Any]:
    """Run all combinations and collect results."""
    all_results = {}

    for period_name, (start_date, end_date) in DATE_RANGES.items():
        all_results[period_name] = {}

        for tf in TIMEFRAMES:
            print(f"\n{'='*60}")
            print(f"Testing: {period_name} | {tf}")
            print(f"{'='*60}")

            try:
                df = fetch_ohlcv(SYMBOL, start_date, end_date, tf, 'CRYPTO')
                print(f"Fetched {len(df)} bars")
            except Exception as e:
                print(f"  Error fetching data: {e}")
                all_results[period_name][tf] = {"error": str(e)}
                continue

            if len(df) < 100:
                print(f"  Skipping: insufficient data ({len(df)} bars)")
                all_results[period_name][tf] = {"error": "insufficient_data", "bars": len(df)}
                continue

            results = []

            # L1 experiments
            for k in [0.01, 0.015, 0.02]:
                print(f"  L1 k={k}...", end=" ")
                result = run_l1_experiment(df, k=k)
                results.append(result)
                if "error" not in result:
                    print(f"{result['num_segments']} segments")
                else:
                    print(f"error: {result['error']}")

            # PELT experiments (pen=0.5 removed: over-segments, too noisy)
            pelt_configs = [
                {"signal_type": "rolling_mean", "penalty_multiplier": 1.0},
                {"signal_type": "returns_vol", "penalty_multiplier": 1.0},
            ]

            for config in pelt_configs:
                print(f"  PELT {config['signal_type']} pen={config['penalty_multiplier']}...", end=" ")
                result = run_pelt_experiment(df, **config)
                results.append(result)
                if "error" not in result:
                    print(f"{result['num_segments']} segments")
                else:
                    print(f"error: {result['error']}")

            all_results[period_name][tf] = {
                "bars": len(df),
                "results": results,
            }

    return all_results


def format_batch_results(all_results: dict) -> str:
    """Format all results for LLM analysis."""
    summary = f"""
Regime Detection Batch Experiment Results
==========================================
Symbol: {SYMBOL}
Timeframes: {', '.join(TIMEFRAMES)}
Date Ranges: {', '.join(DATE_RANGES.keys())}

"""
    for period_name, tf_results in all_results.items():
        start, end = DATE_RANGES[period_name]
        summary += f"\n{'='*60}\n"
        summary += f"Period: {period_name} ({start} to {end})\n"
        summary += f"{'='*60}\n"

        for tf, data in tf_results.items():
            if "error" in data and "results" not in data:
                summary += f"\n  {tf}: ERROR - {data['error']}\n"
                continue

            summary += f"\n  Timeframe: {tf} ({data['bars']} bars)\n"
            summary += f"  {'-'*50}\n"

            for r in data.get("results", []):
                if "error" in r:
                    summary += f"    {r['method']}: ERROR - {r['error']}\n"
                    continue

                if r['method'] == 'L1':
                    summary += f"    L1 k={r['params']['k']}: {r['num_segments']} segs "
                    summary += f"(B:{r['bull_segments']}/E:{r['bear_segments']}) "
                    summary += f"avg={r['avg_segment_bars']} bars\n"
                else:
                    summary += f"    PELT {r['params']['signal_type']} pen={r['params']['penalty_multiplier']}: "
                    summary += f"{r['num_segments']} segs "
                    summary += f"(B:{r['bull_segments']}/E:{r['bear_segments']}/C:{r['choppy_segments']}/R:{r['ranging_segments']}) "
                    summary += f"avg={r['avg_segment_bars']} bars\n"

    return summary


def main():
    print("=" * 70)
    print("LLM-Guided Regime Detection - BATCH MODE")
    print("=" * 70)

    # Test LLM connection
    print("\nTesting LLM connection...")
    test_response = ask_llm("Say 'OK' if you can read this.", max_tokens=10)
    if "Error" in test_response:
        print(f"LLM connection failed: {test_response}")
        print("Continuing without LLM analysis...")
        llm_available = False
    else:
        print(f"LLM connected: {test_response.strip()}")
        llm_available = True

    # Run all experiments
    print("\nRunning batch experiments...")
    all_results = run_all_experiments()

    # Format results
    results_summary = format_batch_results(all_results)

    print("\n" + "=" * 70)
    print("BATCH RESULTS SUMMARY")
    print("=" * 70)
    print(results_summary)

    # LLM analysis - chunked by period
    if llm_available:
        print("\n" + "=" * 70)
        print("LLM ANALYSIS (Chunked by Period)")
        print("=" * 70)

        period_analyses = []

        for period_name, tf_results in all_results.items():
            start, end = DATE_RANGES[period_name]

            # Format single period
            period_summary = f"Period: {period_name} ({start} to {end})\n"
            for tf, data in tf_results.items():
                if "error" in data and "results" not in data:
                    period_summary += f"  {tf}: ERROR\n"
                    continue

                period_summary += f"\n  {tf} ({data['bars']} bars):\n"
                for r in data.get("results", []):
                    if "error" in r:
                        continue

                    if r['method'] == 'L1':
                        period_summary += f"    L1 k={r['params']['k']}: {r['num_segments']} segs, avg={r['avg_segment_bars']}\n"
                    else:
                        period_summary += f"    PELT {r['params']['signal_type']} pen={r['params']['penalty_multiplier']}: {r['num_segments']} segs\n"

            # Analyze this period
            prompt = f"""
Analyze regime detection results for ONE market period:

{period_summary}

Answer briefly:
1. Which method works best for this period?
2. Any problematic results (too few/many segments)?
3. Best parameter choice?

Keep response under 150 words.
"""

            print(f"\nAnalyzing {period_name}...")
            period_analysis = ask_llm(prompt, max_tokens=200)
            print(period_analysis)
            period_analyses.append({
                'period': period_name,
                'analysis': period_analysis
            })

        # Final synthesis
        synthesis_prompt = f"""
Here are analyses for each market period:

{chr(10).join([f"{p['period']}: {p['analysis']}" for p in period_analyses])}

Provide final recommendations:
1. Which method (L1 or PELT) is most robust across all periods?
2. Best parameters for each timeframe?
3. Top 2 recommendations for production use?

Keep under 200 words.
"""

        print("\n" + "=" * 70)
        print("FINAL SYNTHESIS")
        print("=" * 70)

        final_analysis = ask_llm(synthesis_prompt, max_tokens=300)
        print(final_analysis)

        analysis = {
            'period_analyses': period_analyses,
            'final_synthesis': final_analysis
        }
    else:
        analysis = "LLM not available"

    # Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'symbol': SYMBOL,
            'timeframes': TIMEFRAMES,
            'date_ranges': DATE_RANGES,
        },
        'results': all_results,
        'llm_analysis': analysis,
    }

    # Save with timestamp
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'regime_batch_{timestamp_str}.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
