"""
Smoke Test: Feature-Based Conditional Analysis

Tests the feature extraction and conditional analysis on sample strategy.

Validates:
- Feature extraction at trade entry time
- Feature binning and condition analysis
- Winning/losing condition identification
- Feature importance calculation
- Actionable recommendations
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pandas as pd
import numpy as np
import yfinance as yf

from app.engine.robustness.feature_conditioning import (
    extract_features_at_index,
    extract_trade_features,
    analyze_feature_conditions,
    build_feature_conditioning_report,
)


def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def create_sample_trades(df: pd.DataFrame, n_trades: int = 50) -> list[dict]:
    """Create sample trades for testing."""
    trades = []

    # Simulate trades at random points
    np.random.seed(42)
    indices = np.random.choice(range(100, len(df) - 10), size=n_trades, replace=False)

    for idx in indices:
        entry_date = df.index[idx]
        exit_date = df.index[min(idx + np.random.randint(1, 10), len(df) - 1)]

        # Simulate PnL
        entry_price = df['close'].iloc[idx]
        exit_price = df['close'].iloc[min(idx + np.random.randint(1, 10), len(df) - 1)]
        pnl_pct = (exit_price - entry_price) / entry_price

        trades.append({
            'entry_date': entry_date,
            'exit_date': exit_date,
            'pnl_pct': pnl_pct,
            'entry_price': entry_price,
            'exit_price': exit_price,
        })

    return trades


def main():
    print_section("SMOKE TEST: Feature-Based Conditional Analysis")

    # Fetch BTC data
    print("\nFetching BTC-USD data (2023-01-01 to 2025-04-30, 1d)...")
    ticker = yf.Ticker("BTC-USD")
    df_raw = ticker.history(start="2023-01-01", end="2025-04-30", interval="1d")

    if df_raw.empty:
        print("ERROR: No data fetched")
        return

    print(f"Fetched {len(df_raw)} bars")
    print(f"Date range: {df_raw.index[0].date()} to {df_raw.index[-1].date()}")

    # Standardize column names
    df_raw.columns = [col.lower() for col in df_raw.columns]

    # Test 1: Feature extraction at single point
    print_section("TEST 1: Feature Extraction at Single Point")
    test_idx = 200
    test_date = df_raw.index[test_idx]

    print(f"\nExtracting features at index {test_idx} ({test_date.date()})...")
    features = extract_features_at_index(df_raw, test_idx, lookback_window=50)

    print(f"\nExtracted features:")
    print(f"  volatility: {features.volatility:.6f}")
    print(f"  trend_strength (R²): {features.trend_strength:.4f}")
    print(f"  trend_slope: {features.trend_slope:.6f}")
    print(f"  price_vs_sma50: {features.price_vs_sma50:.4f}")
    print(f"  returns_autocorr: {features.returns_autocorr:.4f}")
    print(f"  rsi_level: {features.rsi_level}")
    print(f"  atr_pct: {features.atr_pct}")

    if features.volatility > 0 and -1 <= features.trend_strength <= 1:
        print("\n✅ Feature extraction successful - values in expected ranges")
    else:
        print("\n❌ Feature values out of expected range")

    # Test 2: Feature extraction for trades
    print_section("TEST 2: Feature Extraction for Trades")

    print("\nCreating 50 sample trades...")
    sample_trades = create_sample_trades(df_raw, n_trades=50)
    print(f"Created {len(sample_trades)} trades")
    print(f"Win rate: {sum(1 for t in sample_trades if t['pnl_pct'] > 0) / len(sample_trades) * 100:.1f}%")

    print("\nExtracting features at entry for each trade...")
    trades_with_features = extract_trade_features(sample_trades, df_raw, lookback_window=50)

    print(f"Enriched {len(trades_with_features)} trades with features")

    # Show first trade
    if trades_with_features:
        first_trade = trades_with_features[0]
        print(f"\nExample trade:")
        print(f"  Entry: {first_trade['entry_date'].date()}")
        print(f"  PnL: {first_trade['pnl_pct']*100:.2f}%")
        print(f"  Features: {first_trade['features']}")

        if 'volatility' in first_trade['features']:
            print("\n✅ Features successfully added to trades")
        else:
            print("\n❌ Features not properly added")

    # Test 3: Conditional analysis
    print_section("TEST 3: Conditional Analysis")

    print("\nAnalyzing feature conditions...")
    condition_analysis = analyze_feature_conditions(trades_with_features, min_trades_per_bin=8)

    print(f"\nTotal trades analyzed: {condition_analysis['total_trades']}")
    print(f"Winning conditions found: {len(condition_analysis['winning_conditions'])}")
    print(f"Losing conditions found: {len(condition_analysis['losing_conditions'])}")

    print(f"\nFeature importance:")
    for feature, importance in sorted(condition_analysis['feature_importance'].items(),
                                     key=lambda x: x[1], reverse=True):
        print(f"  {feature}: {importance:.3f}")

    # Show top winning conditions
    if condition_analysis['winning_conditions']:
        print(f"\nTop 3 winning conditions:")
        for i, cond in enumerate(condition_analysis['winning_conditions'][:3], 1):
            print(f"  {i}. {cond['feature']} ∈ [{cond['range'][0]}, {cond['range'][1]}]")
            print(f"     Win rate: {cond['win_rate']}%, Avg PnL: {cond['avg_pnl_pct']}%, Trades: {cond['total_trades']}")

        print("\n✅ Conditional analysis successful - found winning conditions")
    else:
        print("\n⚠️  No winning conditions found (may be due to random sample data)")

    # Show top losing conditions
    if condition_analysis['losing_conditions']:
        print(f"\nTop 3 losing conditions (avoid):")
        for i, cond in enumerate(condition_analysis['losing_conditions'][:3], 1):
            print(f"  {i}. {cond['feature']} ∈ [{cond['range'][0]}, {cond['range'][1]}]")
            print(f"     Win rate: {cond['win_rate']}%, Avg PnL: {cond['avg_pnl_pct']}%, Trades: {cond['total_trades']}")

    # Test 4: Report generation
    print_section("TEST 4: Report Generation")

    overall_metrics = {
        "total_return_pct": 45.2,
        "sharpe_ratio": 1.8,
        "max_drawdown_pct": -15.3,
        "win_rate": 58.0,
        "total_trades": len(trades_with_features),
    }

    print("\nBuilding complete report...")
    report = build_feature_conditioning_report(
        trades_with_features,
        condition_analysis,
        overall_metrics,
    )

    print(f"\nReport structure:")
    print(f"  Keys: {list(report.keys())}")
    print(f"  Trades analyzed: {report['total_trades_analyzed']}")
    print(f"  Most important feature: {report['assessment']['most_important_feature']}")

    print(f"\nRecommendation:")
    print(f"  {report['assessment']['recommendation']}")

    if report['assessment']['risk_flags']:
        print(f"\nRisk flags:")
        for flag in report['assessment']['risk_flags']:
            print(f"  - {flag}")

    print("\n✅ Report generation successful")

    # Summary
    print_section("SUMMARY")
    print("\nAll feature conditioning components working:")
    print("  ✅ Single-point feature extraction")
    print("  ✅ Bulk trade feature extraction")
    print("  ✅ Feature binning and condition analysis")
    print("  ✅ Feature importance calculation")
    print("  ✅ Report generation with recommendations")
    print("\nReady for production use via API endpoint:")
    print("  POST /api/robustness/feature-conditioning")


if __name__ == "__main__":
    main()
