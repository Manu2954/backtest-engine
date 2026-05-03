"""
LLM-Guided Regime Detection - Iterative Mode

Runs one experiment at a time, sends results to LLM,
and lets LLM suggest the next experiment to try.

Starts with a default config, then iterates based on LLM feedback.

Prerequisites:
    - llama.cpp server running on 192.168.1.6:8080

Run: python backend/scripts/llm_regime_iterative.py
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

# Available options for LLM to choose from (5m excluded - separate analysis)
AVAILABLE_TIMEFRAMES = ["1h", "4h", "1d"]
AVAILABLE_PERIODS = {
    "2021_bull": ("2021-01-01", "2021-11-15"),
    "2022_bear": ("2021-11-15", "2022-11-15"),
    "2023_recovery": ("2022-11-15", "2024-01-01"),
    "2025_recent": ("2025-01-01", "2026-04-25"),
}
AVAILABLE_METHODS = ["L1", "PELT"]
SYMBOL = "BTCUSDT"

# Track experiment history
experiment_history = []


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
        'segments_sample': segments[:5],  # First 5 for context
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
            'min_size': min_size,
            'vol_window': vol_window,
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
        'segments_sample': segments_info[:5],
    }


# ============================================================================
# Iterative Runner
# ============================================================================

def run_single_experiment(
    period: str,
    timeframe: str,
    method: str,
    params: dict,
) -> dict[str, Any]:
    """Run a single experiment with given configuration."""
    start_date, end_date = AVAILABLE_PERIODS[period]

    print(f"\nRunning: {method} on {period} {timeframe}")
    print(f"  Params: {params}")

    try:
        df = fetch_ohlcv(SYMBOL, start_date, end_date, timeframe, 'CRYPTO')
        print(f"  Fetched {len(df)} bars")
    except Exception as e:
        return {"error": f"fetch_failed: {e}"}

    if method == "L1":
        result = run_l1_experiment(df, k=params.get('k', 0.015))
    elif method == "PELT":
        result = run_pelt_experiment(
            df,
            signal_type=params.get('signal_type', 'rolling_mean'),
            penalty_multiplier=params.get('penalty_multiplier', 1.0),
            min_size=params.get('min_size', 50),
            vol_window=params.get('vol_window', 20),
        )
    else:
        return {"error": f"unknown_method: {method}"}

    result['config'] = {
        'period': period,
        'timeframe': timeframe,
        'date_range': f"{start_date} to {end_date}",
    }

    return result


def format_result_for_llm(result: dict) -> str:
    """Format single experiment result for LLM."""
    if "error" in result:
        return f"ERROR: {result['error']}"

    config = result.get('config', {})
    text = f"""
Experiment Result:
  Period: {config.get('period')} ({config.get('date_range')})
  Timeframe: {config.get('timeframe')}
  Method: {result['method']}
  Params: {result.get('params')}

  Total bars: {result['total_bars']}
  Segments: {result['num_segments']}
"""

    if result['method'] == 'L1':
        text += f"  BULL: {result['bull_segments']}, BEAR: {result['bear_segments']}\n"
    else:
        text += f"  BULL: {result['bull_segments']}, BEAR: {result['bear_segments']}, "
        text += f"CHOPPY: {result['choppy_segments']}, RANGING: {result['ranging_segments']}\n"

    text += f"  Segment sizes: min={result['min_segment_bars']}, avg={result['avg_segment_bars']}, max={result['max_segment_bars']}\n"

    return text


def format_history_for_llm() -> str:
    """Format experiment history for LLM context."""
    if not experiment_history:
        return "No experiments run yet."

    text = "Previous experiments:\n"
    for i, exp in enumerate(experiment_history[-10:], 1):  # Last 10
        text += f"\n{i}. {exp['config']['period']} | {exp['config']['timeframe']} | {exp['method']}\n"
        text += f"   Segments: {exp['num_segments']}, "
        if exp['method'] == 'L1':
            text += f"BULL/BEAR: {exp['bull_segments']}/{exp['bear_segments']}"
        else:
            text += f"B/E/C/R: {exp['bull_segments']}/{exp['bear_segments']}/{exp['choppy_segments']}/{exp['ranging_segments']}"
        text += f", avg={exp['avg_segment_bars']} bars\n"

    return text


def ask_llm_for_next_experiment() -> dict:
    """Ask LLM to suggest next experiment configuration."""
    history = format_history_for_llm()

    prompt = f"""
You are guiding regime detection experiments for trading strategy backtesting.

{history}

Available options:
- Periods: {list(AVAILABLE_PERIODS.keys())}
- Timeframes: {AVAILABLE_TIMEFRAMES}
- Methods: L1 (params: k=0.01-0.03), PELT (params: signal_type=rolling_mean|returns_vol, penalty_multiplier=1.0-2.0)
- Note: penalty_multiplier < 1.0 removed (over-segments)

Based on the results so far, suggest the NEXT experiment to run.
Consider:
- Testing different market conditions if we haven't
- Trying different timeframes to see how methods scale
- Adjusting parameters based on segment counts

Respond in EXACTLY this JSON format (no other text):
{{"period": "2021_bull", "timeframe": "1h", "method": "L1", "params": {{"k": 0.015}}}}

Or for PELT:
{{"period": "2022_bear", "timeframe": "4h", "method": "PELT", "params": {{"signal_type": "rolling_mean", "penalty_multiplier": 1.0}}}}
"""

    response = ask_llm(prompt, max_tokens=200)
    print(f"\nLLM suggestion: {response}")

    # Parse JSON from response
    try:
        import re

        # Try to find complete JSON objects (handles nested braces)
        # Match opening { and count braces until balanced
        suggestions = []
        i = 0
        while i < len(response):
            if response[i] == '{':
                brace_count = 0
                start = i
                for j in range(i, len(response)):
                    if response[j] == '{':
                        brace_count += 1
                    elif response[j] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = response[start:j+1]
                            suggestions.append(json_str)
                            i = j + 1
                            break
                else:
                    i += 1
            else:
                i += 1

        print(f"  Found {len(suggestions)} JSON candidate(s)")

        # Try each candidate with validation
        for idx, json_str in enumerate(suggestions):
            try:
                suggestion = json.loads(json_str)

                # Validate required fields exist
                if not all(k in suggestion for k in ['period', 'timeframe', 'method', 'params']):
                    print(f"  Candidate {idx+1}: Missing required fields, skipping...")
                    continue

                # Validate period
                if suggestion['period'] not in AVAILABLE_PERIODS:
                    print(f"  Candidate {idx+1}: Invalid period '{suggestion['period']}', skipping...")
                    continue

                # Validate timeframe
                if suggestion['timeframe'] not in AVAILABLE_TIMEFRAMES:
                    print(f"  Candidate {idx+1}: Invalid timeframe '{suggestion['timeframe']}', skipping...")
                    continue

                # Validate method
                if suggestion['method'] not in AVAILABLE_METHODS:
                    print(f"  Candidate {idx+1}: Invalid method '{suggestion['method']}', skipping...")
                    continue

                # Validate params based on method
                params = suggestion['params']
                if suggestion['method'] == 'L1':
                    if 'k' not in params:
                        print(f"  Candidate {idx+1}: Missing 'k' parameter for L1, skipping...")
                        continue
                    k = params['k']
                    if not (0.01 <= k <= 0.03):
                        print(f"  Candidate {idx+1}: Invalid k={k} (must be 0.01-0.03), skipping...")
                        continue

                elif suggestion['method'] == 'PELT':
                    if 'signal_type' not in params or 'penalty_multiplier' not in params:
                        print(f"  Candidate {idx+1}: Missing PELT parameters, skipping...")
                        continue
                    if params['signal_type'] not in ['rolling_mean', 'returns_vol']:
                        print(f"  Candidate {idx+1}: Invalid signal_type '{params['signal_type']}', skipping...")
                        continue
                    pen = params['penalty_multiplier']
                    if not (1.0 <= pen <= 2.0):
                        print(f"  Candidate {idx+1}: Invalid penalty_multiplier={pen} (must be 1.0-2.0), skipping...")
                        continue

                # All validations passed
                print(f"  ✓ Valid suggestion: {suggestion['method']} on {suggestion['period']} {suggestion['timeframe']}")
                return suggestion

            except json.JSONDecodeError as e:
                print(f"  Candidate {idx+1}: JSON decode error, skipping...")
                continue
            except Exception as e:
                print(f"  Candidate {idx+1}: Validation error ({e}), skipping...")
                continue

    except Exception as e:
        print(f"  Failed to parse LLM response: {e}")

    # Default fallback
    print("  No valid suggestions found, using fallback config...")
    return {
        "period": "2025_recent",
        "timeframe": "1h",
        "method": "L1",
        "params": {"k": 0.015}
    }


def ask_llm_for_analysis() -> str:
    """Ask LLM to analyze all experiments and give final recommendations."""
    history = format_history_for_llm()

    prompt = f"""
You have run the following regime detection experiments:

{history}

Please provide a final analysis:
1. Which method (L1 or PELT) performed better overall?
2. Which parameters work best for each timeframe?
3. Are there any clear patterns across market conditions?
4. What are your top 2 specific recommendations for production use?

Be concise and specific.
"""

    return ask_llm(prompt, max_tokens=600)


def main():
    print("=" * 70)
    print("LLM-Guided Regime Detection - ITERATIVE MODE")
    print("=" * 70)

    # Test LLM connection
    print("\nTesting LLM connection...")
    test_response = ask_llm("Say 'OK' if you can read this.", max_tokens=10)
    if "Error" in test_response:
        print(f"LLM connection failed: {test_response}")
        return
    print(f"LLM connected: {test_response.strip()}")

    # Start with a default experiment
    print("\n" + "=" * 70)
    print("Starting with default experiment...")
    print("=" * 70)

    current_config = {
        "period": "2025_recent",
        "timeframe": "1h",
        "method": "L1",
        "params": {"k": 0.015}
    }

    max_iterations = 10
    for iteration in range(max_iterations):
        print(f"\n{'='*70}")
        print(f"ITERATION {iteration + 1}/{max_iterations}")
        print(f"{'='*70}")

        # Run experiment
        result = run_single_experiment(
            period=current_config["period"],
            timeframe=current_config["timeframe"],
            method=current_config["method"],
            params=current_config["params"],
        )

        if "error" not in result:
            experiment_history.append(result)
            print(format_result_for_llm(result))
        else:
            print(f"  Experiment failed: {result['error']}")

        # Ask for next experiment (unless last iteration)
        if iteration < max_iterations - 1:
            print("\nAsking LLM for next experiment...")
            current_config = ask_llm_for_next_experiment()
            # Validation now happens inside ask_llm_for_next_experiment()

    # Final analysis
    print("\n" + "=" * 70)
    print("FINAL LLM ANALYSIS")
    print("=" * 70)

    analysis = ask_llm_for_analysis()
    print(analysis)

    # Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'experiments': experiment_history,
        'final_analysis': analysis,
    }

    # Save with timestamp
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'regime_iterative_{timestamp_str}.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
