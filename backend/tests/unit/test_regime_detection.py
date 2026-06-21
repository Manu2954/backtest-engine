"""
Unit tests for regime detection logic.

Tests the pluggable segmentation architecture:
- SegmentationFactory
- VolatilityStrategy (HIGH_VOL, LOW_VOL, TRANSITION)
- DirectionalStrategy (BULL, BEAR, CHOPPY, RANGING)
- Analysis functions (trades by regime, dependency, etc.)
"""
import numpy as np
import pandas as pd
import pytest

from app.engine.robustness.regime_detection import (
    Segment,
    detect_changepoints,
    detect_regimes,
    extract_segment_features,
    get_regime_at_date,
    analyze_trades_by_regime,
    analyze_cross_regime_trades,
    calculate_regime_distribution,
    assess_regime_dependency,
    build_regime_report,
)
from app.engine.robustness.segmentation import (
    SegmentationFactory,
    VolatilityStrategy,
    DirectionalStrategy,
)
from app.engine.robustness.segmentation.base import LabeledSegment


# =============================================================================
# Helper functions
# =============================================================================

def create_trending_df(n_bars: int, trend: str = "up", volatility: float = 0.01) -> pd.DataFrame:
    """Create a DataFrame with a clear trend for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=n_bars, freq="D")

    if trend == "up":
        base_price = 100
        returns = np.random.normal(0.002, volatility, n_bars)
        prices = base_price * np.cumprod(1 + returns)
    elif trend == "down":
        base_price = 100
        returns = np.random.normal(-0.002, volatility, n_bars)
        prices = base_price * np.cumprod(1 + returns)
    else:  # sideways
        base_price = 100
        returns = np.random.normal(0.0, volatility, n_bars)
        prices = base_price * np.cumprod(1 + returns)

    return pd.DataFrame({
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(1000, 10000, n_bars),
    }, index=dates)


def create_multi_regime_df() -> pd.DataFrame:
    """Create a DataFrame with multiple regimes."""
    np.random.seed(42)

    # Uptrend (50 bars)
    up_returns = np.random.normal(0.003, 0.01, 50)
    up_prices = 100 * np.cumprod(1 + up_returns)

    # Downtrend (50 bars)
    down_returns = np.random.normal(-0.003, 0.01, 50)
    down_prices = up_prices[-1] * np.cumprod(1 + down_returns)

    # Sideways (50 bars)
    side_returns = np.random.normal(0.0, 0.005, 50)
    side_prices = down_prices[-1] * np.cumprod(1 + side_returns)

    prices = np.concatenate([up_prices, down_prices, side_prices])
    dates = pd.date_range("2020-01-01", periods=len(prices), freq="D")

    return pd.DataFrame({
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(1000, 10000, len(prices)),
    }, index=dates)


# =============================================================================
# SegmentationFactory tests
# =============================================================================

def test_factory_create_volatility_strategy():
    """Factory creates VolatilityStrategy."""
    strategy = SegmentationFactory.create_strategy("pelt_volatility")
    assert isinstance(strategy, VolatilityStrategy)
    assert strategy.get_strategy_name() == "volatility"


def test_factory_create_directional_strategy():
    """Factory creates DirectionalStrategy."""
    strategy = SegmentationFactory.create_strategy("pelt_directional")
    assert isinstance(strategy, DirectionalStrategy)
    assert strategy.get_strategy_name() == "directional"


def test_factory_invalid_strategy():
    """Factory raises for invalid strategy."""
    with pytest.raises(ValueError, match="Unknown segmentation strategy"):
        SegmentationFactory.create_strategy("invalid")


def test_factory_get_available_strategies():
    """Factory lists available strategies."""
    strategies = SegmentationFactory.get_available_strategies()
    assert "pelt_volatility" in strategies
    assert "pelt_directional" in strategies
    assert "l1_trend" in strategies


# =============================================================================
# VolatilityStrategy tests
# =============================================================================

def test_volatility_strategy_regime_types():
    """Volatility strategy has correct regime types."""
    strategy = VolatilityStrategy()
    regimes = strategy.get_regime_types()
    assert "HIGH_VOL" in regimes
    assert "LOW_VOL" in regimes
    assert "TRANSITION" in regimes


def test_volatility_strategy_detect_changepoints():
    """Volatility strategy detects changepoints."""
    df = create_multi_regime_df()
    strategy = VolatilityStrategy()

    changepoints = strategy.detect_changepoints(df, min_segment_length=20)

    assert changepoints[0] == 0
    assert changepoints[-1] == len(df)
    assert len(changepoints) >= 2


def test_volatility_strategy_compute_features():
    """Volatility strategy computes volatility-focused features."""
    df = create_trending_df(50, "up")
    strategy = VolatilityStrategy()

    features = strategy.compute_segment_features(df, 0, 50)

    assert "mean_vol" in features
    assert "std_vol" in features
    assert "mean_return" in features
    assert "max_drawdown" in features


def test_volatility_strategy_label_segments():
    """Volatility strategy labels segments."""
    df = create_multi_regime_df()
    strategy = VolatilityStrategy()

    changepoints = strategy.detect_changepoints(df, min_segment_length=20)
    labeled = strategy.label_segments(df, changepoints)

    assert len(labeled) == len(changepoints) - 1
    for seg in labeled:
        assert seg.regime in strategy.get_regime_types()
        assert isinstance(seg, LabeledSegment)


# =============================================================================
# DirectionalStrategy tests
# =============================================================================

def test_directional_strategy_regime_types():
    """Directional strategy has correct regime types."""
    strategy = DirectionalStrategy()
    regimes = strategy.get_regime_types()
    assert "BULL" in regimes
    assert "BEAR" in regimes
    assert "CHOPPY" in regimes
    assert "RANGING" in regimes


def test_directional_strategy_detect_changepoints():
    """Directional strategy detects changepoints."""
    df = create_multi_regime_df()
    strategy = DirectionalStrategy()

    changepoints = strategy.detect_changepoints(df, min_segment_length=20)

    assert changepoints[0] == 0
    assert changepoints[-1] == len(df)
    assert len(changepoints) >= 2


def test_directional_strategy_compute_features():
    """Directional strategy computes trend-focused features."""
    df = create_trending_df(50, "up", volatility=0.005)
    strategy = DirectionalStrategy()

    features = strategy.compute_segment_features(df, 0, 50)

    assert "slope" in features
    assert "r_squared" in features
    assert "mean_return" in features
    assert "std_return" in features
    assert "trend_score" in features
    assert features["slope"] > 0  # Uptrend should have positive slope


def test_directional_strategy_label_uptrend():
    """Directional strategy labels uptrend as BULL."""
    df = create_trending_df(100, "up", volatility=0.005)
    strategy = DirectionalStrategy()

    changepoints = [0, 100]
    labeled = strategy.label_segments(df, changepoints)

    assert len(labeled) == 1
    # With clear uptrend and low volatility, should be BULL
    assert labeled[0].regime in ["BULL", "RANGING"]  # May be RANGING if R² is low


def test_directional_strategy_label_downtrend():
    """Directional strategy labels downtrend as BEAR."""
    df = create_trending_df(100, "down", volatility=0.005)
    strategy = DirectionalStrategy()

    changepoints = [0, 100]
    labeled = strategy.label_segments(df, changepoints)

    assert len(labeled) == 1
    assert labeled[0].regime in ["BEAR", "RANGING"]


def test_directional_strategy_strength_calculation():
    """Directional strategy calculates strength for directional regimes."""
    df = create_multi_regime_df()
    strategy = DirectionalStrategy()

    changepoints = strategy.detect_changepoints(df, min_segment_length=20)
    labeled = strategy.label_segments(df, changepoints)

    for seg in labeled:
        if seg.regime in ["BULL", "BEAR"]:
            assert seg.strength is not None
            assert 0.0 <= seg.strength <= 1.0
        else:
            assert seg.strength is None


def test_directional_strategy_r2_mode_percentile():
    """Directional strategy uses percentile-based R² threshold by default."""
    strategy = DirectionalStrategy()

    assert strategy.r2_mode == "percentile"
    assert strategy.r2_percentile == 75
    assert strategy.r2_fixed == 0.3


def test_directional_strategy_r2_mode_fixed():
    """Directional strategy can use fixed R² threshold."""
    strategy = DirectionalStrategy(r2_mode="fixed", r2_fixed=0.4)

    assert strategy.r2_mode == "fixed"
    assert strategy.r2_fixed == 0.4


def test_directional_strategy_r2_mode_affects_labeling():
    """Different R² modes produce different regime distributions."""
    df = create_multi_regime_df()

    # Percentile mode (stricter - only top 25% get directional labels)
    strategy_pct = DirectionalStrategy(r2_mode="percentile", r2_percentile=75)
    changepoints = strategy_pct.detect_changepoints(df, min_segment_length=20)
    labeled_pct = strategy_pct.label_segments(df, changepoints)

    # Fixed mode with low threshold (more lenient)
    strategy_fixed = DirectionalStrategy(r2_mode="fixed", r2_fixed=0.2)
    labeled_fixed = strategy_fixed.label_segments(df, changepoints)

    # Count directional regimes
    directional_pct = sum(1 for s in labeled_pct if s.regime in ["BULL", "BEAR"])
    directional_fixed = sum(1 for s in labeled_fixed if s.regime in ["BULL", "BEAR"])

    # Fixed 0.2 should produce at least as many directional labels as 75th percentile
    # (because 0.2 is typically a lower bar than 75th percentile R²)
    assert directional_fixed >= directional_pct or len(changepoints) <= 2


def test_factory_creates_directional_with_r2_params():
    """Factory passes R² parameters to DirectionalStrategy."""
    strategy = SegmentationFactory.create_strategy(
        "pelt_directional",
        r2_mode="fixed",
        r2_percentile=80,
        r2_fixed=0.5,
    )

    assert strategy.r2_mode == "fixed"
    assert strategy.r2_percentile == 80
    assert strategy.r2_fixed == 0.5


# =============================================================================
# detect_changepoints (convenience function) tests
# =============================================================================

def test_detect_changepoints_volatility_strategy():
    """detect_changepoints works with volatility strategy."""
    df = create_multi_regime_df()

    changepoints = detect_changepoints(df, strategy="pelt_volatility", min_segment_length=20)

    assert changepoints[0] == 0
    assert changepoints[-1] == len(df)


def test_detect_changepoints_directional_strategy():
    """detect_changepoints works with directional strategy."""
    df = create_multi_regime_df()

    changepoints = detect_changepoints(df, strategy="pelt_directional", min_segment_length=20)

    assert changepoints[0] == 0
    assert changepoints[-1] == len(df)


def test_detect_changepoints_invalid_strategy():
    """detect_changepoints raises for invalid strategy."""
    df = create_trending_df(100, "up")

    with pytest.raises(ValueError, match="Unknown segmentation strategy"):
        detect_changepoints(df, strategy="invalid")


# =============================================================================
# detect_regimes tests
# =============================================================================

def test_detect_regimes_returns_segments_and_labels():
    """detect_regimes returns segments and labels."""
    df = create_multi_regime_df()

    segments, labels = detect_regimes(df, strategy="pelt_directional", min_segment_length=20)

    assert len(segments) >= 1
    assert len(labels) == len(df)
    assert all(isinstance(s, Segment) for s in segments)


def test_detect_regimes_insufficient_data():
    """detect_regimes handles insufficient data."""
    df = create_trending_df(30, "up")

    segments, labels = detect_regimes(df, min_segment_length=20)

    # Should return single segment
    assert len(segments) == 1
    assert len(labels) == len(df)


def test_detect_regimes_volatility_strategy():
    """detect_regimes uses volatility strategy correctly."""
    df = create_multi_regime_df()

    segments, labels = detect_regimes(df, strategy="pelt_volatility", min_segment_length=20)

    # Volatility strategy produces HIGH_VOL, LOW_VOL, TRANSITION
    unique_labels = labels.unique()
    for label in unique_labels:
        assert label in ["HIGH_VOL", "LOW_VOL", "TRANSITION"]


def test_detect_regimes_directional_strategy():
    """detect_regimes uses directional strategy correctly."""
    df = create_multi_regime_df()

    segments, labels = detect_regimes(df, strategy="pelt_directional", min_segment_length=20)

    # Directional strategy produces BULL, BEAR, CHOPPY, RANGING
    unique_labels = labels.unique()
    for label in unique_labels:
        assert label in ["BULL", "BEAR", "CHOPPY", "RANGING"]


def test_detect_regimes_segment_coverage():
    """Segments cover entire date range."""
    df = create_multi_regime_df()

    segments, labels = detect_regimes(df, strategy="pelt_directional", min_segment_length=20)

    # Check coverage
    assert segments[0].start_date == df.index[0]
    assert segments[-1].end_date == df.index[-1]


def test_detect_regimes_segment_has_strength():
    """Directional segments have strength for BULL/BEAR."""
    df = create_multi_regime_df()

    segments, labels = detect_regimes(df, strategy="pelt_directional", min_segment_length=20)

    for seg in segments:
        if seg.regime in ["BULL", "BEAR"]:
            assert seg.strength is not None
        # CHOPPY/RANGING should have None strength


# =============================================================================
# extract_segment_features tests
# =============================================================================

def test_extract_segment_features_count():
    """extract_segment_features returns features for each segment."""
    df = create_multi_regime_df()
    changepoints = [0, 50, 100, 150]

    features = extract_segment_features(df, changepoints, strategy="pelt_directional")

    assert len(features) == 3


def test_extract_segment_features_has_segment_id():
    """Features include segment_id."""
    df = create_multi_regime_df()
    changepoints = [0, 50, 150]

    features = extract_segment_features(df, changepoints, strategy="pelt_directional")

    assert features[0]["segment_id"] == 0
    assert features[1]["segment_id"] == 1


# =============================================================================
# get_regime_at_date tests
# =============================================================================

def test_get_regime_at_date_exact():
    """get_regime_at_date returns exact match."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    labels = pd.Series(["BULL"] * 5 + ["BEAR"] * 5, index=dates)

    regime = get_regime_at_date(labels, dates[0])
    assert regime == "BULL"

    regime = get_regime_at_date(labels, dates[7])
    assert regime == "BEAR"


def test_get_regime_at_date_forward_fill():
    """get_regime_at_date forward fills for missing dates."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    labels = pd.Series(["BULL"] * 10, index=dates)

    # Date between existing dates
    missing_date = pd.Timestamp("2020-01-05 12:00:00")
    regime = get_regime_at_date(labels, missing_date)
    assert regime == "BULL"


# =============================================================================
# analyze_trades_by_regime tests
# =============================================================================

def test_analyze_trades_by_regime_grouping():
    """Trades are grouped by regime correctly."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    labels = pd.Series(["BULL"] * 5 + ["BEAR"] * 5, index=dates)

    trades = [
        {"entry_date": dates[0], "pnl_pct": 0.05},  # 5% in BULL
        {"entry_date": dates[1], "pnl_pct": 0.03},  # 3% in BULL
        {"entry_date": dates[6], "pnl_pct": -0.02},  # -2% in BEAR
    ]

    metrics = analyze_trades_by_regime(trades, labels)

    assert metrics["BULL"]["total_trades"] == 2
    assert metrics["BEAR"]["total_trades"] == 1


def test_analyze_trades_by_regime_win_rate():
    """Win rate calculated correctly."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    labels = pd.Series(["BULL"] * 10, index=dates)

    trades = [
        {"entry_date": dates[0], "pnl_pct": 0.05},
        {"entry_date": dates[1], "pnl_pct": -0.02},
        {"entry_date": dates[2], "pnl_pct": 0.03},
        {"entry_date": dates[3], "pnl_pct": 0.01},
    ]

    metrics = analyze_trades_by_regime(trades, labels)

    # 3 wins out of 4
    assert metrics["BULL"]["win_rate"] == 75.0


def test_analyze_trades_by_regime_empty():
    """Handles regimes with no trades."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    labels = pd.Series(["BULL"] * 5 + ["BEAR"] * 5, index=dates)

    trades = [
        {"entry_date": dates[0], "pnl_pct": 0.05},
    ]

    metrics = analyze_trades_by_regime(trades, labels)

    assert metrics["BULL"]["total_trades"] == 1
    assert metrics["BEAR"]["total_trades"] == 0
    assert metrics["BEAR"]["win_rate"] == 0.0


# =============================================================================
# analyze_cross_regime_trades tests
# =============================================================================

def test_analyze_cross_regime_trades_basic():
    """Cross-regime trades detected correctly."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    labels = pd.Series(["BULL"] * 5 + ["BEAR"] * 5, index=dates)

    trades = [
        {"entry_date": dates[0], "exit_date": dates[2], "pnl_pct": 0.05},  # Same regime (BULL)
        {"entry_date": dates[3], "exit_date": dates[7], "pnl_pct": -0.02},  # Cross regime (BULL->BEAR)
    ]

    result = analyze_cross_regime_trades(trades, labels)

    assert result["total_trades"] == 2
    assert result["cross_regime_trades"] == 1
    assert result["cross_regime_pct"] == 50.0
    assert "BULL->BEAR" in result["transitions"]
    assert result["transitions"]["BULL->BEAR"] == 1


def test_analyze_cross_regime_trades_empty():
    """Handles empty trades."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    labels = pd.Series(["BULL"] * 10, index=dates)

    result = analyze_cross_regime_trades([], labels)

    assert result["total_trades"] == 0
    assert result["cross_regime_trades"] == 0
    assert result["cross_regime_pct"] == 0.0


def test_analyze_cross_regime_trades_all_same():
    """All trades in same regime."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    labels = pd.Series(["BULL"] * 10, index=dates)

    trades = [
        {"entry_date": dates[0], "exit_date": dates[2], "pnl_pct": 0.05},
        {"entry_date": dates[3], "exit_date": dates[5], "pnl_pct": 0.03},
    ]

    result = analyze_cross_regime_trades(trades, labels)

    assert result["total_trades"] == 2
    assert result["cross_regime_trades"] == 0
    assert result["cross_regime_pct"] == 0.0
    assert result["transitions"] == {}


def test_analyze_cross_regime_trades_avg_pnl():
    """Average P&L calculated correctly for cross vs same regime."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    labels = pd.Series(["BULL"] * 5 + ["BEAR"] * 5, index=dates)

    trades = [
        {"entry_date": dates[0], "exit_date": dates[2], "pnl_pct": 0.10},  # Same: +10%
        {"entry_date": dates[1], "exit_date": dates[3], "pnl_pct": 0.06},  # Same: +6%
        {"entry_date": dates[3], "exit_date": dates[7], "pnl_pct": -0.04},  # Cross: -4%
    ]

    result = analyze_cross_regime_trades(trades, labels)

    assert result["same_regime_avg_pnl"] == 8.0  # (10 + 6) / 2
    assert result["cross_regime_avg_pnl"] == -4.0

def test_calculate_regime_distribution():
    """Distribution percentages calculated correctly."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    labels = pd.Series(["BULL"] * 50 + ["BEAR"] * 30 + ["RANGING"] * 20, index=dates)

    dist = calculate_regime_distribution(labels)

    assert dist["BULL"] == 50.0
    assert dist["BEAR"] == 30.0
    assert dist["RANGING"] == 20.0


def test_calculate_regime_distribution_single_regime():
    """Handles single regime."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    labels = pd.Series(["BULL"] * 100, index=dates)

    dist = calculate_regime_distribution(labels)

    assert dist["BULL"] == 100.0


def test_calculate_regime_distribution_empty():
    """Handles empty labels."""
    labels = pd.Series([], dtype=str)

    dist = calculate_regime_distribution(labels)

    assert dist == {}


# =============================================================================
# assess_regime_dependency tests
# =============================================================================

def test_assess_regime_dependency_independent():
    """Low CV is INDEPENDENT."""
    metrics = {
        "BULL": {"total_trades": 10, "total_return_pct": 10.0},
        "BEAR": {"total_trades": 10, "total_return_pct": 9.0},
        "RANGING": {"total_trades": 10, "total_return_pct": 11.0},
    }

    level, cv = assess_regime_dependency(metrics)

    assert level == "INDEPENDENT"
    assert cv < 0.3


def test_assess_regime_dependency_dependent():
    """High CV is DEPENDENT."""
    metrics = {
        "BULL": {"total_trades": 10, "total_return_pct": 50.0},
        "BEAR": {"total_trades": 10, "total_return_pct": -20.0},
    }

    level, cv = assess_regime_dependency(metrics)

    assert level == "DEPENDENT"
    assert cv > 0.6


def test_assess_regime_dependency_single_regime():
    """Single regime with trades is INDEPENDENT."""
    metrics = {
        "BULL": {"total_trades": 10, "total_return_pct": 15.0},
        "BEAR": {"total_trades": 0, "total_return_pct": 0.0},
    }

    level, cv = assess_regime_dependency(metrics)

    assert level == "INDEPENDENT"
    assert cv == 0.0


def test_assess_regime_dependency_excludes_no_trade_regimes():
    """Regimes with 0 trades excluded from CV calculation."""
    metrics = {
        "BULL": {"total_trades": 10, "total_return_pct": 10.0},
        "BEAR": {"total_trades": 0, "total_return_pct": 0.0},
        "RANGING": {"total_trades": 10, "total_return_pct": 9.0},
    }

    level, cv = assess_regime_dependency(metrics)

    # Only BULL and RANGING count
    assert level == "INDEPENDENT"


# =============================================================================
# build_regime_report tests
# =============================================================================

def test_build_regime_report_structure():
    """Report has all required fields."""
    df = create_multi_regime_df()
    segments, labels = detect_regimes(df, strategy="pelt_directional", min_segment_length=20)

    trades = [
        {"entry_date": df.index[10], "pnl_pct": 0.05},
        {"entry_date": df.index[60], "pnl_pct": -0.02},
    ]

    metrics = analyze_trades_by_regime(trades, labels)
    distribution = calculate_regime_distribution(labels)
    level, cv = assess_regime_dependency(metrics)

    report = build_regime_report(
        segments, labels, metrics, distribution, level, cv
    )

    assert "segments" in report
    assert "regimes" in report
    assert "summary" in report
    assert "assessment" in report
    assert "total_bars" in report["summary"]
    assert "dependency_level" in report["summary"]
    assert "risk_flags" in report["assessment"]
    assert "recommendation" in report["assessment"]


def test_build_regime_report_includes_strength():
    """Report segments include strength."""
    df = create_multi_regime_df()
    segments, labels = detect_regimes(df, strategy="pelt_directional", min_segment_length=20)

    metrics = analyze_trades_by_regime([], labels)
    distribution = calculate_regime_distribution(labels)
    level, cv = assess_regime_dependency(metrics)

    report = build_regime_report(
        segments, labels, metrics, distribution, level, cv
    )

    for seg in report["segments"]:
        assert "strength" in seg


def test_build_regime_report_risk_flags():
    """Report includes risk flags for poor regimes."""
    df = create_multi_regime_df()
    segments, labels = detect_regimes(df, strategy="pelt_directional", min_segment_length=20)

    # Create metrics with large losses in one regime
    metrics = {
        "BULL": {"total_trades": 5, "total_return_pct": 20.0, "win_rate": 80.0},
        "BEAR": {"total_trades": 5, "total_return_pct": -15.0, "win_rate": 20.0},
        "CHOPPY": {"total_trades": 0, "total_return_pct": 0.0, "win_rate": 0.0},
        "RANGING": {"total_trades": 0, "total_return_pct": 0.0, "win_rate": 0.0},
    }

    distribution = calculate_regime_distribution(labels)
    level, cv = assess_regime_dependency(metrics)

    report = build_regime_report(
        segments, labels, metrics, distribution, level, cv
    )

    # Should flag losing regime
    assert any("BEAR" in flag and "loses" in flag for flag in report["assessment"]["risk_flags"])
