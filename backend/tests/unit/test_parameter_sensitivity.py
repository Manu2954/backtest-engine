"""
Unit tests for parameter sensitivity analyzer.

Tests cover:
- Parameter variant generation
- Stability score calculation
- Robustness assessment
- Risk flag generation
- Edge cases
"""
import pytest

from app.engine.robustness.parameter_sensitivity import (
    assess_robustness_level,
    calculate_stability_score,
    generate_parameter_variants,
    generate_recommendation,
    generate_risk_flags,
)


def test_generate_variants_single_indicator():
    """Test variant generation with single indicator."""
    strategy = {
        "name": "Test Strategy",
        "indicators": [
            {
                "alias": "rsi_14",
                "indicator_type": "RSI",
                "params": {"period": 14, "source": "close"}
            }
        ]
    }

    variants = generate_parameter_variants(strategy, variation_pct=0.2)

    # Should generate 2 variants (lower and upper)
    assert len(variants) == 2

    # Check lower variant
    lower = variants[0]
    assert lower["variant_params"]["original_value"] == 14
    assert lower["variant_params"]["variant_value"] == 11  # 14 * 0.8 = 11.2 → 11
    assert "rsi_14.period: 14 → 11" in lower["variant_label"]
    assert lower["strategy"]["indicators"][0]["params"]["period"] == 11
    assert lower["strategy"]["indicators"][0]["params"]["source"] == "close"  # Unchanged

    # Check upper variant
    upper = variants[1]
    assert upper["variant_params"]["original_value"] == 14
    assert upper["variant_params"]["variant_value"] == 17  # 14 * 1.2 = 16.8 → 17


def test_generate_variants_multiple_indicators():
    """Test variant generation with multiple indicators."""
    strategy = {
        "indicators": [
            {"alias": "rsi_14", "indicator_type": "RSI", "params": {"period": 14}},
            {"alias": "sma_50", "indicator_type": "SMA", "params": {"length": 50}},
        ]
    }

    variants = generate_parameter_variants(strategy, variation_pct=0.2)

    # 2 indicators × 1 param each × 2 variants (upper/lower) = 4 variants
    assert len(variants) == 4

    # Check we have variants for both indicators
    labels = [v["variant_label"] for v in variants]
    assert any("rsi_14" in label for label in labels)
    assert any("sma_50" in label for label in labels)


def test_generate_variants_multiple_params_per_indicator():
    """Test indicator with multiple numeric parameters."""
    strategy = {
        "indicators": [
            {
                "alias": "bb_20",
                "indicator_type": "BBANDS",
                "params": {"period": 20, "std_dev": 3}  # Changed from 2 to 3
            }
        ]
    }

    variants = generate_parameter_variants(strategy, variation_pct=0.2)

    # 1 indicator × 2 params × 2 variants = 4 variants
    assert len(variants) == 4

    labels = [v["variant_label"] for v in variants]
    assert any("period" in label for label in labels)
    assert any("std_dev" in label for label in labels)


def test_generate_variants_skips_non_numeric_params():
    """Test that non-numeric params are not varied."""
    strategy = {
        "indicators": [
            {
                "alias": "rsi_14",
                "indicator_type": "RSI",
                "params": {"period": 14, "source": "close", "name": "RSI"}
            }
        ]
    }

    variants = generate_parameter_variants(strategy, variation_pct=0.2)

    # Only "period" should be varied (not "source" or "name")
    assert len(variants) == 2

    # Verify non-numeric params are preserved
    for variant in variants:
        params = variant["strategy"]["indicators"][0]["params"]
        assert params["source"] == "close"
        assert params["name"] == "RSI"


def test_generate_variants_skips_zero_or_negative():
    """Test that zero/negative params are skipped."""
    strategy = {
        "indicators": [
            {"alias": "test", "indicator_type": "TEST", "params": {"value": 0}}
        ]
    }

    variants = generate_parameter_variants(strategy, variation_pct=0.2)

    # Zero value should be skipped
    assert len(variants) == 0


def test_generate_variants_respects_minimum_of_one():
    """Test that variants don't go below 1."""
    strategy = {
        "indicators": [
            {"alias": "test", "indicator_type": "TEST", "params": {"period": 2}}
        ]
    }

    variants = generate_parameter_variants(strategy, variation_pct=0.5)  # -50%

    # 2 * 0.5 = 1.0, should floor to 1
    lower = [v for v in variants if v["variant_params"]["variant_value"] < 2][0]
    assert lower["variant_params"]["variant_value"] == 1


def test_generate_variants_custom_variation_pct():
    """Test custom variation percentage."""
    strategy = {
        "indicators": [
            {"alias": "rsi_14", "indicator_type": "RSI", "params": {"period": 10}}
        ]
    }

    variants = generate_parameter_variants(strategy, variation_pct=0.3)  # ±30%

    # 10 * 0.7 = 7, 10 * 1.3 = 13
    values = [v["variant_params"]["variant_value"] for v in variants]
    assert 7 in values
    assert 13 in values


def test_calculate_stability_score_perfect_stability():
    """Test stability score when all variants have same metrics."""
    baseline = {"total_return_pct": 15.0, "sharpe_ratio": 1.5, "win_rate": 60.0}
    variants = [
        {"total_return_pct": 15.0, "sharpe_ratio": 1.5, "win_rate": 60.0},
        {"total_return_pct": 15.0, "sharpe_ratio": 1.5, "win_rate": 60.0},
    ]

    score, cvs = calculate_stability_score(baseline, variants)

    # Perfect stability: CV = 0, score = 1.0
    assert score == 1.0
    assert all(cv == 0.0 for cv in cvs.values())


def test_calculate_stability_score_high_variation():
    """Test stability score with high metric variation."""
    baseline = {"total_return_pct": 20.0, "sharpe_ratio": 2.0, "win_rate": 70.0}
    variants = [
        {"total_return_pct": 10.0, "sharpe_ratio": 1.0, "win_rate": 50.0},
        {"total_return_pct": 5.0, "sharpe_ratio": 0.5, "win_rate": 40.0},
    ]

    score, cvs = calculate_stability_score(baseline, variants)

    # High variation: score should be low (< 0.6)
    assert score < 0.6
    assert cvs["total_return_pct"] > 0.3


def test_calculate_stability_score_moderate_variation():
    """Test stability score with moderate variation."""
    baseline = {"total_return_pct": 15.0, "sharpe_ratio": 1.5, "win_rate": 60.0}
    variants = [
        {"total_return_pct": 13.0, "sharpe_ratio": 1.3, "win_rate": 55.0},
        {"total_return_pct": 17.0, "sharpe_ratio": 1.7, "win_rate": 65.0},
    ]

    score, cvs = calculate_stability_score(baseline, variants)

    # Moderate variation: score should be high (>0.8 for low variation)
    assert score > 0.8


def test_calculate_stability_score_custom_metrics():
    """Test stability score with custom metrics."""
    baseline = {"metric_a": 100.0, "metric_b": 50.0}
    variants = [
        {"metric_a": 100.0, "metric_b": 50.0},
        {"metric_a": 100.0, "metric_b": 50.0},
    ]

    score, cvs = calculate_stability_score(
        baseline, variants, key_metrics=["metric_a", "metric_b"]
    )

    assert score == 1.0
    assert "metric_a" in cvs
    assert "metric_b" in cvs


def test_calculate_stability_score_handles_missing_metrics():
    """Test that missing metrics are skipped."""
    baseline = {"total_return_pct": 15.0}
    variants = [
        {"total_return_pct": 15.0},
        {"total_return_pct": 15.0},
    ]

    # Request metrics that don't exist
    score, cvs = calculate_stability_score(
        baseline, variants, key_metrics=["total_return_pct", "missing_metric"]
    )

    # Should only calculate for available metrics
    assert "total_return_pct" in cvs
    assert "missing_metric" not in cvs


def test_assess_robustness_level():
    """Test robustness level classification."""
    assert assess_robustness_level(0.9) == "ROBUST"
    assert assess_robustness_level(0.8) == "ROBUST"
    assert assess_robustness_level(0.75) == "MODERATE"
    assert assess_robustness_level(0.6) == "MODERATE"
    assert assess_robustness_level(0.5) == "FRAGILE"
    assert assess_robustness_level(0.0) == "FRAGILE"


def test_generate_risk_flags_high_return_variation():
    """Test risk flag for high return variation."""
    baseline = {"total_return_pct": 20.0}
    variants = [
        {"total_return_pct": 5.0},
        {"total_return_pct": 30.0},
    ]
    cvs = {"total_return_pct": 0.6}

    flags = generate_risk_flags(baseline, variants, cvs)

    assert any("Return varies >50%" in flag for flag in flags)


def test_generate_risk_flags_negative_variants():
    """Test risk flag when variants have negative returns."""
    baseline = {"total_return_pct": 10.0}
    variants = [
        {"total_return_pct": -5.0},
        {"total_return_pct": 8.0},
    ]
    cvs = {"total_return_pct": 0.3}

    flags = generate_risk_flags(baseline, variants, cvs)

    assert any("negative returns" in flag for flag in flags)


def test_generate_risk_flags_poor_sharpe_variants():
    """Test risk flag when Sharpe drops below 1.0."""
    baseline = {"sharpe_ratio": 2.0}
    variants = [
        {"sharpe_ratio": 0.8},
        {"sharpe_ratio": 1.5},
    ]
    cvs = {"sharpe_ratio": 0.2}

    flags = generate_risk_flags(baseline, variants, cvs)

    assert any("Sharpe < 1.0" in flag for flag in flags)


def test_generate_risk_flags_no_issues():
    """Test that no flags are generated when metrics are stable."""
    baseline = {"total_return_pct": 15.0, "sharpe_ratio": 1.8, "win_rate": 65.0}
    variants = [
        {"total_return_pct": 14.0, "sharpe_ratio": 1.7, "win_rate": 63.0},
        {"total_return_pct": 16.0, "sharpe_ratio": 1.9, "win_rate": 67.0},
    ]
    cvs = {"total_return_pct": 0.05, "sharpe_ratio": 0.05, "win_rate": 0.03}

    flags = generate_risk_flags(baseline, variants, cvs)

    assert len(flags) == 0


def test_generate_recommendation_robust():
    """Test recommendation for robust strategy."""
    rec = generate_recommendation("ROBUST", [], 0.9)

    assert "robust" in rec.lower()
    assert "safe to deploy" in rec.lower()


def test_generate_recommendation_robust_with_flags():
    """Test recommendation for robust strategy with risk flags."""
    rec = generate_recommendation("ROBUST", ["Some concern"], 0.85)

    assert "good parameter stability" in rec.lower()
    assert "review risk flags" in rec.lower()


def test_generate_recommendation_moderate():
    """Test recommendation for moderate strategy."""
    rec = generate_recommendation("MODERATE", [], 0.7)

    assert "moderate" in rec.lower()
    assert "use with caution" in rec.lower()


def test_generate_recommendation_fragile():
    """Test recommendation for fragile strategy."""
    rec = generate_recommendation("FRAGILE", [], 0.4)

    assert "fragile" in rec.lower()
    assert "do not deploy" in rec.lower()
    assert "overfitting" in rec.lower()
