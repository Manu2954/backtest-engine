# Backtest Engine V1 - New Improvements & Features

## Table of Contents
1. [Overview](#overview)
2. [Dynamic Stop Loss System](#dynamic-stop-loss-system)
3. [Condition Engine Enhancements](#condition-engine-enhancements)
4. [Ichimoku Cloud Strategy Support](#ichimoku-cloud-strategy-support)
5. [Bug Fixes](#bug-fixes)
6. [Exit Reason Intelligence](#exit-reason-intelligence)
7. [Usage Examples](#usage-examples)
8. [API Reference](#api-reference)

---

## Overview

This document covers all recent improvements made to the backtest engine, including dynamic stops, new operators, Ichimoku support, and intelligent exit reason labeling.

**Key Highlights:**
- ✅ Dynamic trailing stops (indicator-based)
- ✅ New condition engine operators (IS_RISING, IS_FALLING)
- ✅ Ichimoku Cloud indicator with 5 lines
- ✅ Fixed P&L calculation bugs
- ✅ Intelligent exit reason labeling
- ✅ Enhanced trade transparency (commission tracking)

---

## Dynamic Stop Loss System

### Overview

Dynamic stops allow you to use **indicator values** as stop levels instead of fixed percentages. The stop level updates every bar based on the indicator, creating a trailing stop effect.

### Key Features

**✅ Indicator-Based Stops**
- Use any indicator column as a stop level
- Stop level updates automatically each bar
- Exits when price drops below indicator value

**✅ Trailing Stop Behavior**
- As indicator moves up, stop follows (locks in profit)
- As indicator moves down, stop follows (adjusts to volatility)
- More adaptive than fixed percentage stops

**✅ Intelligent Exit Labeling**
- Positive P&L → `trailing_stop` (profit protection)
- Negative P&L → `stop_loss` (loss prevention)
- Clear distinction between outcomes

### Implementation

**New Parameter in `run_backtest()`:**
```python
def run_backtest(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    initial_capital: float,
    # ... other params ...
    dynamic_stop_column: str | None = None,  # 🆕 NEW!
    # ... other params ...
) -> tuple[list[dict[str, Any]], pd.Series]:
```

**Parameter Details:**
- **Type:** `str | None`
- **Default:** `None` (no dynamic stop)
- **Usage:** Column name from DataFrame to use as stop level
- **Examples:** `"ichimoku_kijun"`, `"sma_50"`, `"atr_stop_level"`

### How It Works

**1. At Entry:**
```python
entry_price = $100
dynamic_stop_value = $95  # Captured from indicator at entry
```

**2. Each Bar (at bar open):**
```python
current_price = $110
current_indicator_value = $105  # Indicator has moved up

# Check stop
if current_price < current_indicator_value:
    exit("trailing_stop" or "stop_loss")  # Based on P&L
```

**3. Exit Logic:**
```python
# Calculate P&L first
pnl = (exit_price - entry_price) * shares - commissions

# Label based on outcome
if pnl >= 0:
    exit_reason = "trailing_stop"  # Locked in profit
else:
    exit_reason = "stop_loss"  # Cut loss
```

### Usage Examples

#### Example 1: Ichimoku Kijun-sen Stop
```python
# Compute Ichimoku indicator
indicators = [
    {
        "indicator_type": "ICHIMOKU",
        "alias": "ichimoku",
        "params": {"tenkan": 9, "kijun": 26, "senkou": 52}
    }
]
df = compute_indicators(df, indicators)

# Run backtest with Kijun-sen as trailing stop
trades, equity = run_backtest(
    df=df,
    entry_signal=entry_signal,
    exit_signal=exit_signal,
    initial_capital=10000.0,
    dynamic_stop_column="ichimoku_kijun",  # 🎯 Kijun-sen stop
    commission_pct=0.1,
)
```

**Behavior:**
- Entry captured Kijun at $95
- Kijun rises to $105 → stop trails up
- Price drops to $104 → still above Kijun, no exit
- Price drops to $103 → below Kijun, exit with profit
- Exit reason: `trailing_stop` (P&L positive)

#### Example 2: Moving Average Stop
```python
# Compute 50-day SMA
indicators = [
    {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50}}
]
df = compute_indicators(df, indicators)

# Use SMA as trailing stop
trades, equity = run_backtest(
    df=df,
    entry_signal=entry_signal,
    exit_signal=exit_signal,
    initial_capital=10000.0,
    dynamic_stop_column="sma_50",  # Exit if price < SMA
)
```

#### Example 3: Custom ATR-Based Stop
```python
# Compute ATR
indicators = [
    {"indicator_type": "ATR", "alias": "atr_14", "params": {"period": 14}}
]
df = compute_indicators(df, indicators)

# Create custom stop: Close - 2x ATR
df['atr_stop'] = df['close'] - (2 * df['atr_14'])

# Use custom stop
trades, equity = run_backtest(
    df=df,
    entry_signal=entry_signal,
    exit_signal=exit_signal,
    initial_capital=10000.0,
    dynamic_stop_column="atr_stop",  # Custom ATR stop
)
```

#### Example 4: Chandelier Exit
```python
# Calculate highest high and ATR
df['highest_high'] = df['high'].rolling(20).max()
df['chandelier_stop'] = df['highest_high'] - (3 * df['atr_14'])

# Use Chandelier Exit as stop
trades, equity = run_backtest(
    df=df,
    entry_signal=entry_signal,
    exit_signal=exit_signal,
    initial_capital=10000.0,
    dynamic_stop_column="chandelier_stop",
)
```

#### Example 5: Combined Dynamic + Fixed Stop
```python
# Layered protection: Dynamic primary, fixed backup
trades, equity = run_backtest(
    df=df,
    entry_signal=entry_signal,
    exit_signal=exit_signal,
    initial_capital=10000.0,
    dynamic_stop_column="ichimoku_kijun",  # Primary trailing stop
    stop_loss_pct=5.0,  # Backup disaster stop (-5%)
)
```

**Priority:** Dynamic stop checked first, then fixed stop if not triggered.

### Comparison: Dynamic vs Fixed Stops

| Feature | Fixed Stop | Dynamic Stop |
|---------|-----------|--------------|
| **Stop Level** | Fixed % from entry price | Updates with indicator |
| **Movement** | Never moves | Trails with indicator |
| **Formula** | `entry_price * (1 - pct/100)` | Current indicator value |
| **Best For** | Strict risk management | Profit protection |
| **Exit Reason** | Always `stop_loss` | `trailing_stop` or `stop_loss` |
| **Example** | -5% hard stop | Kijun-sen trailing |
| **Adapts to Volatility** | ❌ No | ✅ Yes (if indicator does) |
| **Locks in Profit** | ❌ No (only cuts loss) | ✅ Yes (trails upward) |

### When to Use Dynamic Stops

**✅ Use Dynamic Stops For:**
- Trend-following strategies (Ichimoku, MA crossovers)
- Volatile markets (ATR-based stops adjust)
- Profit protection (trailing stops)
- Adaptive risk management

**❌ Don't Use Dynamic Stops For:**
- Mean reversion (want fixed exit points)
- Short-term scalping (too slow to update)
- When you need guaranteed max loss % (use fixed)

---

## Condition Engine Enhancements

### New Operators: IS_RISING and IS_FALLING

**Added:** Direction detection operators for trend analysis

#### IS_RISING

**Detects:** Indicator value increasing (current > previous)

**Syntax:**
```python
{
    "left_operand_type": "INDICATOR",
    "left_operand_value": "adx_14",
    "operator": "IS_RISING",
    "right_operand_type": "SCALAR",
    "right_operand_value": "0",  # Dummy value (ignored)
}
```

**Logic:**
```python
# Returns True when:
current_value > previous_value

# Example:
# Bar 1: ADX = 23
# Bar 2: ADX = 25 → IS_RISING = True
# Bar 3: ADX = 24 → IS_RISING = False
```

**Use Cases:**
- ADX rising (trend strengthening)
- RSI gaining momentum
- Volume increasing
- MACD histogram growing

#### IS_FALLING

**Detects:** Indicator value decreasing (current < previous)

**Syntax:**
```python
{
    "left_operand_type": "INDICATOR",
    "left_operand_value": "adx_14",
    "operator": "IS_FALLING",
    "right_operand_type": "SCALAR",
    "right_operand_value": "0",  # Dummy value (ignored)
}
```

**Logic:**
```python
# Returns True when:
current_value < previous_value

# Example:
# Bar 1: ADX = 35
# Bar 2: ADX = 33 → IS_FALLING = True
# Bar 3: ADX = 34 → IS_FALLING = False
```

**Use Cases:**
- ADX peaking (trend losing momentum)
- RSI turning down
- Momentum indicators weakening
- Volume declining

### Complete Operator Reference

| Operator | Description | Operands Required | Use Case |
|----------|-------------|-------------------|----------|
| **GT** | Greater than | 2 (any type) | RSI > 70 |
| **LT** | Less than | 2 (any type) | RSI < 30 |
| **EQ** | Equal to | 2 (any type) | Volume == 0 |
| **GTE** | Greater than or equal | 2 (any type) | Price >= SMA |
| **LTE** | Less than or equal | 2 (any type) | Price <= Resistance |
| **CROSSES_ABOVE** | Bullish crossover | 2 (both Series) | MACD crosses Signal |
| **CROSSES_BELOW** | Bearish crossover | 2 (both Series) | Price crosses MA |
| **IS_RISING** | 🆕 Increasing | 1 (Series) | ADX rising |
| **IS_FALLING** | 🆕 Decreasing | 1 (Series) | ADX falling |

### Usage Example: ADX Strategy

```python
# Entry: ADX > 25, ADX rising, +DI > -DI
entry_group = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "adx_14",
            "operator": "GT",
            "right_operand_type": "SCALAR",
            "right_operand_value": "25",
        },
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "adx_14",
            "operator": "IS_RISING",  # 🆕 NEW OPERATOR
            "right_operand_type": "SCALAR",
            "right_operand_value": "0",
        },
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "adx_14_dmp",
            "operator": "GT",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "adx_14_dmn",
        },
    ],
}

# Exit: ADX falling (momentum loss)
exit_group = {
    "logic": "OR",
    "conditions": [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "adx_14",
            "operator": "IS_FALLING",  # 🆕 NEW OPERATOR
            "right_operand_type": "SCALAR",
            "right_operand_value": "0",
        },
    ],
}
```

### When to Use Condition Engine vs Manual Filters

#### ✅ Use Condition Engine For:

**Simple Comparisons:**
```python
# Indicator > Scalar
{"left": "rsi_14", "operator": "GT", "right": "70"}

# Indicator > Indicator
{"left": "sma_50", "operator": "GT", "right": "sma_200"}
```

**Crossovers:**
```python
# Bullish cross
{"left": "macd", "operator": "CROSSES_ABOVE", "right": "macd_signal"}
```

**Direction:**
```python
# Rising/Falling
{"left": "adx_14", "operator": "IS_RISING", "right": "0"}
```

#### ❌ Use Manual Filters For:

**Time-Shifted Comparisons:**
```python
# Requires .shift()
df['filter'] = df['chikou'] > df['close'].shift(26)
```

**Rolling Windows:**
```python
# Requires .rolling()
df['filter'] = df['close'] == df['close'].rolling(20).max()
```

**Complex Formulas:**
```python
# Multi-step calculations
df['distance'] = ((df['close'] - df['sma']) / df['sma']) * 100
df['filter'] = df['distance'] > 2
```

**See:** `CONDITION_ENGINE_GUIDE.md` for complete decision tree

---

## Ichimoku Cloud Strategy Support

### Overview

Full Ichimoku Cloud indicator support with all 5 lines implemented.

### Indicator Implementation

**Syntax:**
```python
{
    "indicator_type": "ICHIMOKU",
    "alias": "ichimoku",
    "params": {
        "tenkan": 9,   # Conversion Line period
        "kijun": 26,   # Base Line period
        "senkou": 52,  # Leading Span B period
    }
}
```

**Output Columns:**
- `{alias}_tenkan` - Tenkan-sen (Conversion Line) = (9-period high + 9-period low) / 2
- `{alias}_kijun` - Kijun-sen (Base Line) = (26-period high + 26-period low) / 2
- `{alias}_span_a` - Senkou Span A (Leading Span A) = (Tenkan + Kijun) / 2, shifted +26
- `{alias}_span_b` - Senkou Span B (Leading Span B) = (52-period high + 52-period low) / 2, shifted +26
- `{alias}_chikou` - Chikou Span (Lagging Span) = Close, shifted -26

### Complete Ichimoku Strategy Example

**File:** `backend/scripts/test_ichimoku_strategy.py`

**Entry Rules (ALL required):**
```python
entry_group = {
    "logic": "AND",
    "conditions": [
        # 1. Price above cloud
        {"left": "close", "operator": "GT", "right": "ichimoku_span_a"},
        {"left": "close", "operator": "GT", "right": "ichimoku_span_b"},

        # 2. Tenkan crosses above Kijun
        {"left": "ichimoku_tenkan", "operator": "CROSSES_ABOVE", "right": "ichimoku_kijun"},

        # 3. Cross occurs above cloud
        {"left": "ichimoku_tenkan", "operator": "GT", "right": "ichimoku_span_a"},
        {"left": "ichimoku_tenkan", "operator": "GT", "right": "ichimoku_span_b"},

        # 4. Future cloud is bullish
        {"left": "ichimoku_span_a", "operator": "GT", "right": "ichimoku_span_b"},
    ],
}

# Manual filter (requires .shift())
df['chikou_filter'] = df['ichimoku_chikou'] > df['close'].shift(26)
entry_signal = evaluate_conditions(df, entry_group) & df['chikou_filter']
```

**Exit Rules (OR logic - first trigger):**
```python
exit_group = {
    "logic": "OR",
    "conditions": [
        # Exit 1: Close below Kijun
        {"left": "close", "operator": "LT", "right": "ichimoku_kijun"},

        # Exit 2: Tenkan crosses below Kijun
        {"left": "ichimoku_tenkan", "operator": "CROSSES_BELOW", "right": "ichimoku_kijun"},
    ],
}
```

**Dynamic Kijun-sen Stop:**
```python
trades, equity = run_backtest(
    df=df,
    entry_signal=entry_signal,
    exit_signal=exit_signal,
    initial_capital=10000.0,
    dynamic_stop_column="ichimoku_kijun",  # Trailing stop
    position_size_type="percent_capital",
    position_size_value=100.0,  # Full capital (no pyramiding)
    commission_pct=0.1,
)
```

### Ichimoku Cloud Color

**Bullish Cloud:** Span A > Span B (green/blue cloud)
```python
df['bullish_cloud'] = df['ichimoku_span_a'] > df['ichimoku_span_b']
```

**Bearish Cloud:** Span A < Span B (red cloud)
```python
df['bearish_cloud'] = df['ichimoku_span_a'] < df['ichimoku_span_b']
```

**Usage in Conditions:**
```python
# Filter for bullish cloud
{
    "left_operand_type": "INDICATOR",
    "left_operand_value": "ichimoku_span_a",
    "operator": "GT",
    "right_operand_type": "INDICATOR",
    "right_operand_value": "ichimoku_span_b",
}
```

---

## Bug Fixes

### 1. P&L Percentage Calculation Fix

**Issue:** `pnl_pct` was calculated as percentage of **total initial capital** instead of **trade investment**.

**Before:**
```python
pnl_pct = pnl / initial_capital  # ❌ WRONG
# $500 profit / $10,000 capital = 5% (misleading)
```

**After:**
```python
trade_cost = entry_price * shares + entry_commission
pnl_pct = (pnl / trade_cost * 100)  # ✅ CORRECT
# $500 profit / $5,000 invested = 10% (accurate)
```

**Impact:**
- **Old calculation:** Entry $76.36, Exit $84.25 → showed 0.05% return
- **New calculation:** Entry $76.36, Exit $84.25 → shows 10.34% return

**Example:**
```python
Entry: $100 x 50 shares = $5,000 invested
Exit: $110 x 50 shares = $5,500
P&L: $500

Old: $500 / $10,000 = 5%  ❌
New: $500 / $5,000 = 10%  ✅
```

### 2. Missing Report Metrics

**Issue:** Report dictionary was missing key metrics that were calculated but not returned.

**Fixed - Added to Report:**
- `avg_win` - Average winning trade amount ($)
- `avg_loss` - Average losing trade amount ($)
- `largest_win` - Biggest winning trade ($)
- `largest_loss` - Biggest losing trade ($)
- `avg_trade_duration_days` - Average trade length (days)

**Before:**
```python
report = {
    "total_return_pct": ...,
    "avg_win_loss": ...,  # Only ratio, not individual values
}
```

**After:**
```python
report = {
    "total_return_pct": ...,
    "avg_win": 234.56,           # 🆕 NEW
    "avg_loss": -89.12,          # 🆕 NEW
    "avg_win_loss": 2.63,        # Ratio
    "largest_win": 523.42,       # 🆕 NEW
    "largest_loss": -156.78,     # 🆕 NEW
    "avg_trade_duration_days": 18.5,  # 🆕 NEW (renamed)
}
```

### 3. Commission Tracking in TradeRecord

**Issue:** Individual trade records didn't show commission breakdown.

**Fixed - Added to TradeRecord:**
```python
@dataclass
class TradeRecord:
    # ... existing fields ...
    entry_commission: float  # 🆕 Commission paid on entry
    exit_commission: float   # 🆕 Commission paid on exit
    total_commission: float  # 🆕 Total commission (entry + exit)
```

**Trade Output Now Shows:**
```python
Trade #1:
  Entry: 2020-05-19 @ $76.36
  Exit:  2020-06-10 @ $84.25
  Shares: 64.00
  P&L: $494.26 (10.11%)
  Commissions: $12.34 (Entry: $6.11, Exit: $6.23)  # 🆕 NEW
  Exit Reason: take_profit
  Duration: 22 days
```

---

## Exit Reason Intelligence

### Overview

Enhanced exit reason labeling to distinguish between profit-taking and loss-cutting exits.

### Exit Reason Types

| Exit Reason | Meaning | When It Triggers |
|-------------|---------|------------------|
| **`trailing_stop`** | 🆕 Dynamic stop with profit | Price < indicator, P&L ≥ 0 |
| **`stop_loss`** | Stop with loss | Fixed or dynamic stop, P&L < 0 |
| **`signal`** | Strategy exit signal | Entry/exit condition triggered |
| **`take_profit`** | Profit target hit | Fixed profit % reached |
| **`force_close`** | End of backtest | Position closed at last bar |

### Implementation

**State Machine Logic:**
```python
# Calculate P&L first
pnl = (exit_price - entry_price) * shares - commissions

# Dynamic stop labeling
if dynamic_stop_triggered:
    if pnl >= 0:
        exit_reason = "trailing_stop"  # Locked in profit ✅
    else:
        exit_reason = "stop_loss"      # Cut loss ❌
```

### Example Analysis

**Before (Confusing):**
```
Exit Reason Breakdown:
Stop Loss                                     20 trades (66.7%)
Exit Signal                                   10 trades (33.3%)
```
- Can't tell if stops were profitable or not
- "Stop Loss" implies all lost money

**After (Clear):**
```
Exit Reason Breakdown:
Trailing Stop (Dynamic Stop - Profit)         15 trades (50.0%)
Exit Signal (Close < Kijun)                   10 trades (33.3%)
Stop Loss (Dynamic Stop - Loss)                5 trades (16.7%)
```
- **15 trades** exited with profit via trailing stop ✅
- **5 trades** exited with loss via stop loss ❌
- **10 trades** exited via strategy signal

### Performance Insights

**Winning Trailing Stops:** Good profit protection
```python
trailing_stop_trades = [t for t in trades if t['exit_reason'] == 'trailing_stop']
avg_profit = sum(t['pnl'] for t in trailing_stop_trades) / len(trailing_stop_trades)
# Shows how well your trailing stop captures profit
```

**Stop Loss Exits:** Risk management effectiveness
```python
stop_loss_trades = [t for t in trades if t['exit_reason'] == 'stop_loss']
avg_loss = sum(t['pnl'] for t in stop_loss_trades) / len(stop_loss_trades)
# Shows how well your stop limits losses
```

---

## Usage Examples

### Complete Strategy: Ichimoku Cloud

**File:** `backend/scripts/test_ichimoku_strategy.py`

```python
from app.engine.data_layer import fetch_ohlcv
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.condition_engine import evaluate_conditions
from app.engine.state_machine import run_backtest
from app.engine.report_generator import generate_report, calculate_buy_and_hold_equity

# 1. Fetch data
df = fetch_ohlcv("AAPL", "2020-01-01", "2023-12-31", "1d", "STOCK")

# 2. Compute Ichimoku
indicators = [
    {
        "indicator_type": "ICHIMOKU",
        "alias": "ichimoku",
        "params": {"tenkan": 9, "kijun": 26, "senkou": 52}
    }
]
df = compute_indicators(df, indicators)
df, warmup_bars = trim_warmup_period(df)

# 3. Define entry (6 conditions in engine)
entry_group = {
    "logic": "AND",
    "conditions": [
        {"left": "close", "operator": "GT", "right": "ichimoku_span_a"},
        {"left": "close", "operator": "GT", "right": "ichimoku_span_b"},
        {"left": "ichimoku_tenkan", "operator": "CROSSES_ABOVE", "right": "ichimoku_kijun"},
        {"left": "ichimoku_tenkan", "operator": "GT", "right": "ichimoku_span_a"},
        {"left": "ichimoku_tenkan", "operator": "GT", "right": "ichimoku_span_b"},
        {"left": "ichimoku_span_a", "operator": "GT", "right": "ichimoku_span_b"},
    ],
}
entry_signal = evaluate_conditions(df, entry_group)

# Manual filter (requires .shift())
df['chikou_filter'] = df['ichimoku_chikou'] > df['close'].shift(26)
entry_signal = entry_signal & df['chikou_filter'].fillna(False)

# 4. Define exit (OR logic)
exit_group = {
    "logic": "OR",
    "conditions": [
        {"left": "close", "operator": "LT", "right": "ichimoku_kijun"},
        {"left": "ichimoku_tenkan", "operator": "CROSSES_BELOW", "right": "ichimoku_kijun"},
    ],
}
exit_signal = evaluate_conditions(df, exit_group)

# 5. Run backtest with dynamic Kijun stop
trades, equity = run_backtest(
    df=df,
    entry_signal=entry_signal,
    exit_signal=exit_signal,
    initial_capital=10000.0,
    asset_class="STOCK",
    position_size_type="percent_capital",
    position_size_value=100.0,
    dynamic_stop_column="ichimoku_kijun",  # 🎯 Dynamic trailing stop
    commission_pct=0.1,
    slippage_pct=0.05,
)

# 6. Generate report with benchmark
benchmark_equity = calculate_buy_and_hold_equity(df, 10000.0, "STOCK")
report = generate_report(trades, equity, 10000.0, benchmark_equity=benchmark_equity)

# 7. Analyze results
print(f"Total Trades: {report['total_trades']}")
print(f"Win Rate: {report['win_rate']:.2f}%")
print(f"Total Return: {report['total_return_pct']:.2f}%")
print(f"Alpha vs Buy&Hold: {report['alpha']:.2f}%")
print(f"Sharpe Ratio: {report['sharpe_ratio']:.4f}")

# Analyze exit reasons
for trade in trades:
    print(f"{trade['exit_reason']}: {trade['pnl_pct']:.2f}%")
```

### Complete Strategy: ADX Trend Following

**File:** `backend/scripts/test_adx_all_exit_rules.py`

```python
# 1. Compute ADX
indicators = [
    {"indicator_type": "ADX", "alias": "adx_14", "params": {"period": 14}},
    {"indicator_type": "ATR", "alias": "atr_14", "params": {"period": 14}},
]
df = compute_indicators(df, indicators)

# 2. Entry: ADX > 25, rising, +DI > -DI
entry_group = {
    "logic": "AND",
    "conditions": [
        {"left": "adx_14", "operator": "GT", "right": "25"},
        {"left": "adx_14", "operator": "IS_RISING", "right": "0"},
        {"left": "adx_14_dmp", "operator": "GT", "right": "adx_14_dmn"},
    ],
}

# 3. Exit: DI crossover OR ADX falling
exit_group = {
    "logic": "OR",
    "conditions": [
        {"left": "adx_14_dmn", "operator": "CROSSES_ABOVE", "right": "adx_14_dmp"},
        {"left": "adx_14", "operator": "IS_FALLING", "right": "0"},
    ],
}

# 4. Run with stop loss and take profit
trades, equity = run_backtest(
    df=df,
    entry_signal=evaluate_conditions(df, entry_group),
    exit_signal=evaluate_conditions(df, exit_group),
    initial_capital=10000.0,
    position_size_type="percent_capital",
    position_size_value=50.0,
    stop_loss_pct=2.0,
    take_profit_pct=6.0,
    commission_pct=0.1,
)
```

---

## API Reference

### run_backtest()

**Signature:**
```python
def run_backtest(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    initial_capital: float,
    asset_class: str = "STOCK",
    shares: float = 0.0,
    periodic_contribution: dict[str, Any] | None = None,
    # Position sizing
    position_size_type: str = "full_capital",
    position_size_value: float = 100.0,
    # Risk management
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    dynamic_stop_column: str | None = None,  # 🆕 NEW
    # Transaction costs
    commission_per_trade: float = 0.0,
    commission_pct: float = 0.0,
    slippage_pct: float = 0.0,
) -> tuple[list[dict[str, Any]], pd.Series]:
```

**New Parameter:**

**`dynamic_stop_column`**
- **Type:** `str | None`
- **Default:** `None`
- **Description:** Column name from DataFrame to use as dynamic stop level
- **Behavior:**
  - Captures indicator value at entry
  - Checks `price < indicator_value` each bar
  - Exits with `trailing_stop` (profit) or `stop_loss` (loss)
- **Examples:** `"ichimoku_kijun"`, `"sma_50"`, `"atr_stop"`

**Priority Order:**
1. Dynamic stop (if set)
2. Fixed percentage stop (if no dynamic stop)
3. Take profit (after stops)

### TradeRecord

**Updated Structure:**
```python
@dataclass
class TradeRecord:
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float               # 🔧 FIXED (now per-trade %)
    trade_duration_days: int
    exit_reason: str             # 🔧 ENHANCED (intelligent labeling)
    entry_commission: float      # 🆕 NEW
    exit_commission: float       # 🆕 NEW
    total_commission: float      # 🆕 NEW
```

### Report Dictionary

**Updated Structure:**
```python
report = {
    "total_return_pct": float,
    "cagr": float,
    "total_trades": int,
    "win_rate": float,
    "avg_win": float,                   # 🆕 NEW
    "avg_loss": float,                  # 🆕 NEW
    "avg_win_loss": float,
    "largest_win": float,               # 🆕 NEW
    "largest_loss": float,              # 🆕 NEW
    "max_drawdown_pct": float,
    "sharpe_ratio": float,
    "profit_factor": float,
    "avg_trade_duration_days": float,   # 🆕 RENAMED
    "longest_drawdown_days": int,
    "final_capital": float,
    # Benchmark comparison (if provided)
    "benchmark_return_pct": float,
    "benchmark_final_capital": float,
    "benchmark_sharpe_ratio": float,
    "benchmark_max_drawdown_pct": float,
    "alpha": float,
    "beta": float,
}
```

### Condition Engine Operators

**Complete List:**
```python
OPERATORS = {
    "GT",              # Greater than
    "LT",              # Less than
    "EQ",              # Equal to
    "GTE",             # Greater than or equal
    "LTE",             # Less than or equal
    "CROSSES_ABOVE",   # Bullish crossover
    "CROSSES_BELOW",   # Bearish crossover
    "IS_RISING",       # 🆕 Value increasing
    "IS_FALLING",      # 🆕 Value decreasing
}
```

### Indicator Types

**Updated List:**
```python
SUPPORTED_INDICATORS = [
    "RSI",         # Relative Strength Index
    "SMA",         # Simple Moving Average
    "EMA",         # Exponential Moving Average
    "MACD",        # Moving Average Convergence Divergence
    "BB",          # Bollinger Bands
    "ATR",         # Average True Range
    "STOCH",       # Stochastic Oscillator
    "ADX",         # Average Directional Index (with +DI, -DI)
    "ICHIMOKU",    # 🆕 Ichimoku Cloud (5 lines)
]
```

---

## File Reference

### New/Modified Files

**Core Engine:**
- `backend/app/engine/state_machine.py` - Dynamic stops, exit reason logic
- `backend/app/engine/condition_engine.py` - IS_RISING, IS_FALLING operators
- `backend/app/engine/indicator_layer.py` - Ichimoku Cloud implementation
- `backend/app/engine/report_generator.py` - Fixed P&L calc, added metrics

**Test Files:**
- `backend/scripts/test_ichimoku_strategy.py` - Complete Ichimoku strategy
- `backend/scripts/test_adx_all_exit_rules.py` - ADX with all 4 exit rules
- `backend/scripts/test_dynamic_stop.py` - Dynamic stop verification

**Documentation:**
- `backend/IMPROVEMENTS.md` - This file
- `backend/CONDITION_ENGINE_GUIDE.md` - Condition engine vs manual filters guide

---

## Migration Guide

### From Previous Version

**If you were using:**

**1. Fixed stops only:**
```python
# Old (still works)
run_backtest(df, ..., stop_loss_pct=5.0)

# New option (dynamic trailing)
run_backtest(df, ..., dynamic_stop_column="sma_50")

# Combined
run_backtest(df, ..., dynamic_stop_column="sma_50", stop_loss_pct=5.0)
```

**2. Manual ADX direction checks:**
```python
# Old (manual)
df['adx_rising'] = df['adx_14'] > df['adx_14'].shift(1)
entry_signal = entry_signal & df['adx_rising']

# New (condition engine)
entry_group = {
    "conditions": [
        {"left": "adx_14", "operator": "IS_RISING", "right": "0"}
    ]
}
entry_signal = evaluate_conditions(df, entry_group)
```

**3. Analyzing stop losses:**
```python
# Old (all stops labeled "stop_loss")
stop_trades = [t for t in trades if t['exit_reason'] == 'stop_loss']

# New (distinguish profit vs loss)
profit_stops = [t for t in trades if t['exit_reason'] == 'trailing_stop']
loss_stops = [t for t in trades if t['exit_reason'] == 'stop_loss']
```

---

## Performance Considerations

### Dynamic Stops

**Overhead:** Minimal
- One extra column read per bar
- One comparison operation per bar
- Negligible impact on backtest speed

**Memory:** No additional memory
- Uses existing DataFrame columns
- No new data structures created

### New Operators

**IS_RISING / IS_FALLING:**
- One shift operation per evaluation
- Cached in condition engine
- No performance impact

### Recommendations

**Best Practices:**
- Pre-calculate custom stops before backtest
- Use condition engine for 80%+ of logic
- Reserve manual filters for .shift() / .rolling() operations
- Test strategies with and without dynamic stops to compare

---

## Future Enhancements

### Potential Additions

**1. Time-Based Stops**
```python
# Exit after N days regardless of price
max_trade_duration_days=30
```

**2. Volatility-Adjusted Stops**
```python
# Auto-adjust stop based on ATR
volatility_adjusted_stop=True
volatility_multiplier=2.0
```

**3. Multiple Dynamic Stops**
```python
# Use different stops for different conditions
dynamic_stop_columns=["kijun", "atr_stop"]  # Exit on either
```

**4. Partial Exits**
```python
# Scale out at multiple levels
partial_exits=[
    {"pnl_pct": 5, "exit_pct": 50},   # Exit 50% at +5%
    {"pnl_pct": 10, "exit_pct": 100}, # Exit rest at +10%
]
```

**5. Entry Filters**
```python
# Minimum bars since last trade
min_bars_between_trades=10
```

---

## Conclusion

These improvements significantly enhance the backtest engine's capabilities:

**✅ More Realistic:**
- Dynamic stops mirror real trading behavior
- Intelligent exit labeling shows true performance

**✅ More Flexible:**
- Use any indicator as a stop
- Combine multiple risk management techniques

**✅ More Accurate:**
- Fixed P&L calculations show true returns
- Full commission transparency

**✅ More Powerful:**
- New operators enable complex strategies
- Full Ichimoku Cloud support

**✅ Better Analysis:**
- Understand why trades exit
- Separate profit-taking from loss-cutting
- Measure trailing stop effectiveness

**Next Steps:**
1. Review test files for implementation examples
2. Read `CONDITION_ENGINE_GUIDE.md` for best practices
3. Implement your strategy with dynamic stops
4. Analyze exit reason breakdown for insights

---

**Version:** V1.1
**Last Updated:** 2026-03-08
**Author:** Backtest Engine Team
