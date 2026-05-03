"""
Test HMM (Hidden Markov Model) for regime detection.

Using Fractionally Differenced Prices (Lopez de Prado, Chapter 5):
- Raw prices: full memory, non-stationary (bad for HMM)
- Returns (d=1): no memory, stationary (loses trend info)
- Fractional diff (d=0.3-0.5): some memory, stationary (best of both)

HMM learns:
- Hidden states (regimes): BULL, BEAR, SIDEWAYS
- Transition probabilities between states
- Emission distributions

Prerequisites:
    pip install hmmlearn

Run: python backend/scripts/test_hmm_regime.py
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

try:
    from hmmlearn import hmm
except ImportError:
    print("Install hmmlearn: pip install hmmlearn")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from app.engine.data_layer import fetch_ohlcv


def get_weights_ffd(d: float, threshold: float = 1e-5) -> np.ndarray:
    """
    Compute weights for fractional differentiation (Fixed-width window).

    Args:
        d: Fractional differentiation order (0 < d < 1)
           d=0: original series (full memory)
           d=1: first difference (no memory)
           d=0.3-0.5: sweet spot for trends
        threshold: Minimum weight magnitude to include

    Returns:
        Array of weights (most recent first)
    """
    weights = [1.0]
    k = 1
    while True:
        w = -weights[-1] * (d - k + 1) / k
        if abs(w) < threshold:
            break
        weights.append(w)
        k += 1
    return np.array(weights[::-1])  # Reverse so oldest weight first


def frac_diff_ffd(series: pd.Series, d: float, threshold: float = 1e-5) -> pd.Series:
    """
    Fractionally differentiate a series using Fixed-width window.

    This preserves memory while achieving stationarity.

    Args:
        series: Price series
        d: Differentiation order (0.3-0.5 typical)
        threshold: Weight cutoff

    Returns:
        Fractionally differenced series
    """
    weights = get_weights_ffd(d, threshold)
    width = len(weights)

    # Apply weights via rolling window
    result = series.rolling(width).apply(lambda x: np.dot(weights, x), raw=True)

    return result


def fit_hmm(features: np.ndarray, n_states: int = 3, n_iter: int = 100) -> tuple:
    """
    Fit a Gaussian HMM to features data.

    Args:
        features: Array of features (can be 1D or 2D)
        n_states: Number of hidden states (regimes)
        n_iter: Max iterations for EM algorithm

    Returns:
        Tuple of (model, hidden_states, log_likelihood)
    """
    # Reshape if needed (hmmlearn needs 2D array)
    if features.ndim == 1:
        X = features.reshape(-1, 1)
    else:
        X = features

    # Fit Gaussian HMM with diagonal covariance (more stable)
    model = hmm.GaussianHMM(
        n_components=n_states,
        covariance_type="diag",  # Changed from "full" for stability
        n_iter=n_iter,
        random_state=42,
    )
    model.fit(X)

    # Predict hidden states
    hidden_states = model.predict(X)

    # Get log likelihood
    log_likelihood = model.score(X)

    return model, hidden_states, log_likelihood


def compute_bic(log_likelihood: float, n_params: int, n_samples: int) -> float:
    """
    Compute BIC for model selection.

    BIC = -2 * log_likelihood + k * log(n)
    """
    return -2 * log_likelihood + n_params * np.log(n_samples)


def get_n_params(n_states: int, n_features: int = 1) -> int:
    """
    Count free parameters in Gaussian HMM.

    - Transition matrix: n_states * (n_states - 1)
    - Initial distribution: n_states - 1
    - Means: n_states * n_features
    - Covariances: n_states * n_features * (n_features + 1) / 2
    """
    trans_params = n_states * (n_states - 1)
    init_params = n_states - 1
    mean_params = n_states * n_features
    cov_params = n_states * n_features * (n_features + 1) // 2
    return trans_params + init_params + mean_params + cov_params


def label_states(model, n_states: int) -> dict:
    """
    Label states based on their mean return.

    Highest mean → BULL
    Lowest mean → BEAR
    Middle → SIDEWAYS (or CHOPPY/RANGING based on variance)
    """
    # Use first feature (rolling_mean) for labeling direction
    means = model.means_[:, 0] if model.means_.ndim == 2 else model.means_.flatten()

    # Handle different covariance shapes for variance
    covars = model.covars_
    if covars.ndim == 3:
        # Use second feature (rolling_std) if available, else first
        feat_idx = 1 if model.means_.shape[1] > 1 else 0
        variances = np.array([covars[i, feat_idx, feat_idx] for i in range(n_states)])
    elif covars.ndim == 2:
        variances = covars[:, 0] if covars.shape[1] > 1 else covars.flatten()
    else:
        variances = covars.flatten()

    # Sort states by mean return
    sorted_indices = np.argsort(means)

    labels = {}
    if n_states == 2:
        labels[int(sorted_indices[0])] = "BEAR"
        labels[int(sorted_indices[1])] = "BULL"
    elif n_states == 3:
        labels[int(sorted_indices[0])] = "BEAR"
        labels[int(sorted_indices[1])] = "SIDEWAYS"
        labels[int(sorted_indices[2])] = "BULL"
    elif n_states == 4:
        labels[int(sorted_indices[0])] = "BEAR"
        # Middle two: distinguish by variance
        mid_indices = sorted_indices[1:3]
        mid_vars = [variances[i] for i in mid_indices]
        if mid_vars[0] > mid_vars[1]:
            labels[int(mid_indices[0])] = "CHOPPY"
            labels[int(mid_indices[1])] = "RANGING"
        else:
            labels[int(mid_indices[0])] = "RANGING"
            labels[int(mid_indices[1])] = "CHOPPY"
        labels[int(sorted_indices[3])] = "BULL"
    else:
        # Generic labeling
        for i, idx in enumerate(sorted_indices):
            labels[int(idx)] = f"STATE_{i}"

    return labels


def get_segments(hidden_states: np.ndarray, dates: pd.DatetimeIndex, labels: dict) -> list:
    """
    Extract contiguous segments from hidden states.

    Returns list of dicts with start, end, regime, bars.
    """
    segments = []
    current_state = int(hidden_states[0])
    start_idx = 0

    for i in range(1, len(hidden_states)):
        state = int(hidden_states[i])
        if state != current_state:
            # State changed - close current segment
            segments.append({
                'start_idx': start_idx,
                'end_idx': i - 1,
                'start_date': dates[start_idx],
                'end_date': dates[i - 1],
                'regime': labels[current_state],
                'bars': i - start_idx,
            })
            current_state = state
            start_idx = i

    # Close final segment
    segments.append({
        'start_idx': start_idx,
        'end_idx': len(hidden_states) - 1,
        'start_date': dates[start_idx],
        'end_date': dates[-1],
        'regime': labels[current_state],
        'bars': len(hidden_states) - start_idx,
    })

    return segments


def print_segments(segments: list, df: pd.DataFrame):
    """Print segment details."""
    print(f'\nTotal segments: {len(segments)}')
    print(f'\nSegment details:')

    for i, seg in enumerate(segments):
        start_price = df['close'].iloc[seg['start_idx']]
        end_price = df['close'].iloc[seg['end_idx']]
        pct_change = ((end_price / start_price) - 1) * 100

        print(f"  Seg {i+1}: {seg['start_date']} → {seg['end_date']}")
        print(f"          Regime: {seg['regime']}, Bars: {seg['bars']}, Change: {pct_change:+.2f}%")

        if i >= 29:  # Limit output
            remaining = len(segments) - i - 1
            if remaining > 0:
                print(f"  ... and {remaining} more segments")
            break


def plot_hmm_results(df: pd.DataFrame, hidden_states: np.ndarray, labels: dict,
                     n_states: int, bic: float, save_path: str = None):
    """Plot price with HMM regime coloring."""
    if not HAS_MATPLOTLIB:
        print("Skipping plot - matplotlib not installed")
        return

    prices = df['close'].values
    dates = df.index

    # Color map for regimes
    colors = {
        'BULL': 'green',
        'BEAR': 'red',
        'SIDEWAYS': 'gray',
        'CHOPPY': 'orange',
        'RANGING': 'blue',
    }
    # Fallback for generic states
    default_colors = ['red', 'gray', 'green', 'orange', 'blue', 'purple']

    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot price
    ax.plot(dates, prices, 'k-', linewidth=0.5, alpha=0.7)

    # Color background by regime
    for i in range(len(hidden_states) - 1):
        state = hidden_states[i]
        label = labels[state]
        color = colors.get(label, default_colors[state % len(default_colors)])
        ax.axvspan(dates[i], dates[i + 1], alpha=0.3, color=color)

    # Create legend
    from matplotlib.patches import Patch
    legend_elements = []
    seen_labels = set()
    for state, label in labels.items():
        if label not in seen_labels:
            color = colors.get(label, default_colors[state % len(default_colors)])
            legend_elements.append(Patch(facecolor=color, alpha=0.3, label=label))
            seen_labels.add(label)
    ax.legend(handles=legend_elements, loc='upper left')

    ax.set_xlabel('Date')
    ax.set_ylabel('Price ($)')
    ax.set_title(f'HMM Regime Detection | {n_states} states | BIC = {bic:.0f}')

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
    print("=== HMM Regime Detection (with Fractional Differentiation) ===\n")

    # Fetch data
    df = fetch_ohlcv('BTCUSDT', '2026-03-01', '2026-04-25', '5m', 'CRYPTO')
    print(f'Total bars: {len(df)}')

    # Fractionally differentiate log prices
    # d=0.4 is typical - preserves memory while achieving stationarity
    d = 0.4
    log_prices = np.log(df['close'])
    frac_diff_prices = frac_diff_ffd(log_prices, d=d, threshold=1e-5)

    # Drop NaN from warmup period
    frac_diff_prices = frac_diff_prices.dropna()
    df_aligned = df.loc[frac_diff_prices.index]

    print(f'Fractional diff order d={d}')
    print(f'Features length: {len(frac_diff_prices)}')

    # Use frac diff prices as single feature
    features = frac_diff_prices.values.reshape(-1, 1)

    # Test different number of states
    print(f'\n{"="*60}')
    print('Finding optimal number of states using BIC...')
    print(f'{"="*60}')

    results = {}
    for n_states in [2, 3, 4, 5]:
        model, hidden_states, log_likelihood = fit_hmm(features, n_states=n_states)
        n_params = get_n_params(n_states, n_features=1)  # 1 feature now
        bic = compute_bic(log_likelihood, n_params, len(features))
        labels = label_states(model, n_states)
        segments = get_segments(hidden_states, df_aligned.index, labels)

        results[n_states] = {
            'model': model,
            'hidden_states': hidden_states,
            'log_likelihood': log_likelihood,
            'bic': bic,
            'labels': labels,
            'segments': segments,
        }

        print(f'  {n_states} states: {len(segments):3d} segments, BIC = {bic:.0f}')

    # Find optimal
    optimal_n = min(results.keys(), key=lambda k: results[k]['bic'])
    print(f'\n✓ Optimal: {optimal_n} states (BIC = {results[optimal_n]["bic"]:.0f})')

    # Show optimal results
    opt = results[optimal_n]
    print(f'\n{"="*60}')
    print(f'Results with {optimal_n} states')
    print(f'{"="*60}')

    # Print state characteristics
    model = opt['model']
    labels = opt['labels']
    print('\nState characteristics (frac diff signal):')
    for state in range(optimal_n):
        mean_val = float(model.means_[state, 0])
        # Handle different covariance shapes
        if model.covars_.ndim == 2:
            std_val = float(np.sqrt(model.covars_[state, 0]))
        else:
            std_val = float(np.sqrt(model.covars_[state]))
        print(f"  {labels[state]}: mean={mean_val:+.6f}, std={std_val:.6f}")

    # Print transition matrix
    print('\nTransition matrix:')
    print('  From\\To  ', end='')
    for state in range(optimal_n):
        print(f'{labels[state]:>10}', end='')
    print()
    for i in range(optimal_n):
        print(f'  {labels[i]:<10}', end='')
        for j in range(optimal_n):
            print(f'{model.transmat_[i, j]:>10.2%}', end='')
        print()

    # Print segments
    print_segments(opt['segments'], df_aligned)

    # Plot
    plot_hmm_results(
        df_aligned, opt['hidden_states'], opt['labels'],
        optimal_n, opt['bic'],
        save_path='hmm_regime_detection.png'
    )

    # Also plot comparison of different state counts
    if HAS_MATPLOTLIB:
        fig, axes = plt.subplots(4, 1, figsize=(14, 16), sharex=True)
        for ax, n_states in zip(axes, [2, 3, 4, 5]):
            res = results[n_states]
            prices = df_aligned['close'].values
            dates = df_aligned.index
            hidden_states = res['hidden_states']
            labels = res['labels']

            ax.plot(dates, prices, 'k-', linewidth=0.5, alpha=0.7)

            colors = {'BULL': 'green', 'BEAR': 'red', 'SIDEWAYS': 'gray',
                      'CHOPPY': 'orange', 'RANGING': 'blue'}
            default_colors = ['red', 'gray', 'green', 'orange', 'blue']

            for i in range(len(hidden_states) - 1):
                state = hidden_states[i]
                label = labels[state]
                color = colors.get(label, default_colors[state % len(default_colors)])
                ax.axvspan(dates[i], dates[i + 1], alpha=0.3, color=color)

            marker = " ← OPTIMAL" if n_states == optimal_n else ""
            ax.set_title(f'{n_states} states | {len(res["segments"])} segments | BIC = {res["bic"]:.0f}{marker}')
            ax.set_ylabel('Price ($)')

        axes[-1].set_xlabel('Date')
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.tight_layout()
        plt.savefig('hmm_comparison.png', dpi=150, bbox_inches='tight')
        print(f'\nComparison plot saved to: hmm_comparison.png')
        plt.show()


if __name__ == "__main__":
    main()
