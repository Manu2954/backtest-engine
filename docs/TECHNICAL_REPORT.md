# Backtest Engine - Comprehensive Technical Report

**Generated:** 2026-06-17  
**Repository:** `/Users/I749340/backtest-engine`  
**Version:** Post-v1 (includes leverage, short selling, exit rules, robustness analysis)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Layer](#3-data-layer)
4. [Indicator Layer](#4-indicator-layer)
5. [Condition Engine](#5-condition-engine)
6. [State Machine (Backtest Engine)](#6-state-machine-backtest-engine)
7. [Exit Rules System](#7-exit-rules-system)
8. [Report Generator](#8-report-generator)
9. [Robustness Analysis Module](#9-robustness-analysis-module)
10. [Data Providers](#10-data-providers)
11. [API Layer](#11-api-layer)
12. [Database Models](#12-database-models)
13. [Background Tasks (Celery)](#13-background-tasks-celery)
14. [Usage Patterns](#14-usage-patterns)
15. [File Reference](#15-file-reference)

---

## 1. Executive Summary

The Backtest Engine is a production-grade quantitative trading strategy backtesting platform built with:

- **Backend:** FastAPI (async), SQLAlchemy (async ORM), Celery (background tasks)
- **Database:** PostgreSQL (persistence), Redis (caching, message broker)
- **Frontend:** React/TypeScript (currently lower priority)
- **Data Sources:** Yahoo Finance (stocks), Binance REST API (crypto)

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Multi-Asset Support** | Stocks via yfinance, Crypto via Binance Futures API |
| **14+ Technical Indicators** | SMA, EMA, RSI, MACD, BB, ATR, Stochastic, ADX, Ichimoku, ROC, OBV, Donchian, Heikin Ashi, Supertrend |
| **8 Condition Operators** | GT, LT, EQ, GTE, LTE, CROSSES_ABOVE, CROSSES_BELOW, IS_RISING, IS_FALLING |
| **5 Operand Types** | INDICATOR, OHLCV, SCALAR, LOOKBACK, EXPRESSION |
| **Position Management** | Long/Short positions, leverage with liquidation, margin tracking |
| **Risk Management** | Stop loss, take profit, dynamic stops, pluggable exit rules |
| **Position Sizing** | Full capital, percent capital, fixed amount, risk-based |
| **Transaction Costs** | Fixed commission, percentage commission, slippage |
| **Robustness Analysis** | Parameter sensitivity, walk-forward validation, regime detection, feature conditioning |
| **Trade Attribution** | Condition tracking, signal strength, alpha calculation |

### Key Metrics

- **API Endpoints:** 16 across 5 route groups
- **Database Tables:** 9 core tables with cascade relationships
- **Celery Tasks:** 5 async task types (backtest + 4 robustness analyses)
- **Supported Resolutions:** 1m to 1mo (provider-dependent)

---

## 2. Architecture Overview

### Component Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        React Frontend (Port 5173)                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Port 8000)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  /strategies │  │  /backtests  │  │ /robustness  │  │  /tickers   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐
│   PostgreSQL    │  │      Redis      │  │       Celery Worker         │
│   (Port 5432)   │  │   (Port 6379)   │  │                             │
│                 │  │                 │  │  ┌───────────────────────┐  │
│  - Strategies   │  │  - OHLCV Cache  │  │  │    Engine Pipeline    │  │
│  - Backtests    │  │  - Task Broker  │  │  │                       │  │
│  - Trades       │  │  - Results      │  │  │  fetch_ohlcv_async()  │  │
│  - OHLCV Cache  │  │                 │  │  │         ▼             │  │
│  - Robustness   │  │                 │  │  │  compute_indicators() │  │
│                 │  │                 │  │  │         ▼             │  │
└─────────────────┘  └─────────────────┘  │  │ evaluate_conditions() │  │
                                          │  │         ▼             │  │
                                          │  │    run_backtest()     │  │
                                          │  │         ▼             │  │
                                          │  │  generate_report()    │  │
                                          │  └───────────────────────┘  │
                                          └─────────────────────────────┘
```

### Data Flow Pipeline

```
Request
   │
   ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Data Layer     │ ──▶ │  Indicator Layer │ ──▶ │ Condition Engine │
│                  │     │                  │     │                  │
│ • Provider fetch │     │ • 14+ indicators │     │ • 8 operators    │
│ • Redis cache    │     │ • Warmup detect  │     │ • 5 operand types│
│ • DB persistence │     │ • Column mapping │     │ • Expressions    │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                                          │
                                                          ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Report Generator │ ◀── │   State Machine  │ ◀── │   Exit Rules     │
│                  │     │                  │     │                  │
│ • 15+ metrics    │     │ • Position mgmt  │     │ • Dynamic exits  │
│ • Benchmarks     │     │ • Leverage       │     │ • Activation     │
│ • Attribution    │     │ • Short selling  │     │ • Min loss gates │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## 3. Data Layer

**File:** `backend/app/engine/data_layer.py`

### Purpose
Central hub for OHLCV data retrieval with multi-tier caching and provider orchestration.

### Three-Layer Cache Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     fetch_ohlcv_async()                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Redis Cache                                           │
│  • Key: ohlcv:{TICKER}:{resolution}:{start}:{end}               │
│  • TTL: 86400s (24 hours, configurable)                         │
│  • Format: msgpack binary serialization                         │
│  • HIT → Return immediately                                     │
└─────────────────────────────────────────────────────────────────┘
                              │ MISS
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: PostgreSQL (ohlcv_bars table)                         │
│  • Unique: (ticker, asset_class, resolution, ts)                │
│  • Gap detection via bar count heuristics                       │
│  • Daily: 60% coverage threshold (weekends/holidays)            │
│  • Intraday: 1+ bar minimum (market hours variation)            │
│  • HIT (complete) → Cache to Redis → Return                     │
└─────────────────────────────────────────────────────────────────┘
                              │ MISS or INCOMPLETE
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: External Provider API                                 │
│  • STOCK → YFinanceProvider (auto_adjust=True)                  │
│  • CRYPTO → BinanceProvider (Futures API, 1000-bar pagination)  │
│  • Normalize → Store to DB (batch 500) → Cache to Redis         │
└─────────────────────────────────────────────────────────────────┘
```

### Key Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `fetch_ohlcv_async` | `(ticker, start, end, resolution, asset_class, session, provider, timezone)` | Primary async fetcher with full cache logic |
| `fetch_ohlcv` | `(ticker, start, end, resolution, asset_class, provider, timezone)` | Sync wrapper for non-async contexts |
| `validate_ticker` | `(ticker, asset_class)` | Validates ticker by fetching 7-day data |
| `_normalize_df` | `(df)` | Normalizes columns, handles MultiIndex, drops NaN |
| `_load_db_ohlcv` | `(session, ticker, asset_class, resolution, start, end)` | Load from PostgreSQL with gap detection |
| `_store_db_ohlcv` | `(session, ticker, asset_class, resolution, df)` | Batch upsert (500 rows) with ON CONFLICT |

### Resolution Support

| Asset Class | Supported Intervals |
|-------------|---------------------|
| STOCK (yfinance) | 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo |
| CRYPTO (Binance) | 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1mo |

### Configuration

- **Default Timezone:** Asia/Kolkata (IST)
- **Cache TTL:** Configurable via `settings.ohlcv_cache_ttl_seconds`
- **Stock Intraday Limit:** 60 days (Yahoo Finance limitation)
- **Binance Rate Limit:** 600 requests/minute with sleep backoff

---

## 4. Indicator Layer

**File:** `backend/app/engine/indicator_layer.py`

### Purpose
Computes technical indicators using pandas-ta library with warmup period management.

### Supported Indicators (14 types)

| Indicator | Type | Params | Output Columns |
|-----------|------|--------|----------------|
| RSI | RSI | period, source | `{alias}` |
| EMA | EMA | period, source | `{alias}` |
| SMA | SMA | period, source | `{alias}` |
| MACD | MACD | fast, slow, signal, source | `{alias}_macd`, `{alias}_signal`, `{alias}_hist` |
| Bollinger Bands | BB/BBANDS | period, std_dev, source | `{alias}_upper`, `{alias}_mid`, `{alias}_lower` |
| ATR | ATR | period | `{alias}` |
| Stochastic | STOCH | k_period, d_period | `{alias}_k`, `{alias}_d` |
| ADX | ADX | period | `{alias}`, `{alias}_dmp`, `{alias}_dmn` |
| Ichimoku | ICHIMOKU | tenkan, kijun, senkou | `{alias}_tenkan`, `{alias}_kijun`, `{alias}_span_a`, `{alias}_span_b`, `{alias}_chikou` |
| ROC | ROC | period, source | `{alias}` |
| OBV | OBV | (none) | `{alias}` |
| Donchian | DONCHIAN | period | `{alias}_upper`, `{alias}_lower`, `{alias}_mid` |
| Heikin Ashi | HEIKINASHI | (none) | `{alias}_open`, `{alias}_high`, `{alias}_low`, `{alias}_close` |
| Supertrend | SUPERTREND | period, multiplier | `{alias}_trend`, `{alias}`, `{alias}_long`, `{alias}_short` |

### Key Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `compute_indicators` | `(df, indicators: list[dict])` | Adds indicator columns to DataFrame copy |
| `get_warmup_period` | `(df)` | Returns index of first fully valid bar |
| `trim_warmup_period` | `(df)` | Removes NaN warmup bars, returns (trimmed_df, count) |

### Indicator Configuration Format

```python
indicators = [
    {
        "indicator_type": "MACD",
        "alias": "macd_12_26",
        "params": {
            "fast": 12,
            "slow": 26,
            "signal": 9,
            "source": "close"  # optional, defaults to "close"
        }
    }
]
```

### Warmup Period Handling

- Indicators requiring N bars of history produce NaN for first N-1 bars
- `get_warmup_period()` finds first row where ALL indicators are valid
- `trim_warmup_period()` removes leading NaN rows before backtest
- Metadata stored in `df.attrs["indicator_columns"]` for tracking

---

## 5. Condition Engine

**File:** `backend/app/engine/condition_engine.py`

### Purpose
Evaluates boolean conditions against DataFrames with support for complex expressions.

### Operators (8 types)

| Operator | Operands | Behavior |
|----------|----------|----------|
| GT | Any | Left > Right |
| LT | Any | Left < Right |
| EQ | Any | Left == Right |
| GTE | Any | Left >= Right |
| LTE | Any | Left <= Right |
| CROSSES_ABOVE | Series | prev(left) < prev(right) AND now(left) > now(right) |
| CROSSES_BELOW | Series | prev(left) > prev(right) AND now(left) < now(right) |
| IS_RISING | Series | Left > shift(1) |
| IS_FALLING | Series | Left < shift(1) |

### Operand Types (5 types)

| Type | Format | Example |
|------|--------|---------|
| INDICATOR | Column name | `"sma_50"`, `"rsi_14"` |
| OHLCV | Built-in column | `"open"`, `"high"`, `"low"`, `"close"`, `"volume"` |
| SCALAR | Numeric string | `"30"`, `"0.5"`, `"-10"` |
| LOOKBACK | `column:offset` | `"close:-3"` (3 bars ago), `"adx:-5"` |
| EXPRESSION | Math formula | `"high - low"`, `"sma_200 + atr_14 * 2"` |

### Key Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `evaluate_conditions` | `(df, condition_group)` | Returns boolean Series for condition group |
| `evaluate_expression` | `(df, condition_groups, expression)` | Combines groups with boolean expression |
| `evaluate_conditions_with_attribution` | `(df, condition_group, bar_idx, context)` | Single-bar evaluation with attribution data |

### Condition Group Format

```python
condition_group = {
    "logic": "AND",  # or "OR"
    "conditions": [
        {
            "id": "entry-1",
            "left_operand_type": "INDICATOR",
            "left_operand_value": "sma_20",
            "operator": "CROSSES_ABOVE",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "sma_50"
        },
        {
            "id": "entry-2",
            "left_operand_type": "INDICATOR",
            "left_operand_value": "rsi_14",
            "operator": "GT",
            "right_operand_type": "SCALAR",
            "right_operand_value": "40"
        }
    ]
}
```

### Boolean Expression Evaluation

```python
# Named condition groups
groups = {
    "oversold": oversold_group,
    "trending": trending_group,
    "reversal": reversal_group
}

# Boolean expression combining groups
expression = "(oversold && trending) || reversal"

# Evaluate
signal = evaluate_expression(df, groups, expression)
```

### Multi-Column Indicator Mapping

When referencing multi-column indicators by base alias:

| Reference | Maps To |
|-----------|---------|
| `"macd"` | `"macd_macd"` |
| `"bb"` | `"bb_mid"` |
| `"stoch"` | `"stoch_k"` |
| `"ichimoku"` | `"ichimoku_tenkan"` |

---

## 6. State Machine (Backtest Engine)

**File:** `backend/app/engine/state_machine.py`

### Purpose
Core backtest simulation engine with dual position state machines for long/short positions.

### PositionState Dataclass

```python
@dataclass
class PositionState:
    direction: str              # "LONG" or "SHORT"
    shares: float               # Quantity held
    entry_price: float | None   # Fill price at entry
    entry_date: Timestamp | None
    entry_commission: float
    leverage: float             # Position multiplier (1.0 = no leverage)
    margin: float               # Capital required for leveraged positions
    liquidation_price: float | None  # Auto-liquidation level
    
    # Pending states
    pending_entry: bool         # Awaiting fill at next bar
    pending_exit: bool          # Exit triggered, awaiting fill
    entry_bar_idx: int | None
    exit_bar_idx: int | None
    
    # Dynamic exit fields
    dynamic_tp_pct: float | None
    dynamic_exit_ref: float | None
    pending_exit_reason: str | None
    
    # Exit rules state
    exit_rule_states: list[dict]
    
    # Attribution
    entry_attribution_data: dict
    exit_attribution_data: dict
```

### State Transitions

```
                    ┌─────────────────┐
                    │      IDLE       │
                    │  (shares = 0)   │
                    └────────┬────────┘
                             │ entry_signal
                             ▼
                    ┌─────────────────┐
                    │ PENDING_ENTRY   │
                    │  (next bar fill)│
                    └────────┬────────┘
                             │ _fill_entry()
                             ▼
                    ┌─────────────────┐
                    │  IN_POSITION    │◄─────────────────┐
                    │  (shares > 0)   │                  │
                    └────────┬────────┘                  │
                             │                           │
            ┌────────────────┼────────────────┐          │
            │                │                │          │
            ▼                ▼                ▼          │
    ┌───────────┐    ┌───────────┐    ┌───────────┐      │
    │ Liquidation│   │  Stops    │    │Exit Signal│      │
    │  (lev>1)   │   │ (SL/TP)   │    │           │      │
    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘      │
          │                │                │            │
          └────────────────┼────────────────┘            │
                           │ pending_exit=True           │
                           ▼                             │
                    ┌─────────────────┐                  │
                    │  PENDING_EXIT   │                  │
                    │ (next bar fill) │                  │
                    └────────┬────────┘                  │
                             │ _execute_exit()           │
                             ▼                           │
                    ┌─────────────────┐                  │
                    │   TRADE LOG     │──────────────────┘
                    │  (record trade) │    (if counter-trade enabled)
                    └────────┬────────┘
                             │ reset()
                             ▼
                    ┌─────────────────┐
                    │      IDLE       │
                    └─────────────────┘
```

### run_backtest() Full Signature

```python
def run_backtest(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    initial_capital: float,
    
    # Asset configuration
    asset_class: str = "STOCK",
    shares: float = 0.0,
    
    # Periodic contributions
    periodic_contribution: dict | None = None,  # {"amount", "frequency", "interval_days", "include_start"}
    
    # Position sizing
    position_size_type: str = "full_capital",   # full_capital|percent_capital|fixed_amount|risk_based
    position_size_value: float = 100.0,
    
    # Stop loss / Take profit
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    dynamic_stop_column: str | None = None,     # Indicator-based trailing stop
    dynamic_tp_pct_column: str | None = None,   # Per-trade TP from column
    
    # Legacy dynamic exit (deprecated in favor of exit_rules)
    dynamic_exit_monitor_column: str | None = None,
    dynamic_exit_ref_column: str | None = None,
    dynamic_exit_skip_column: str | None = None,
    dynamic_exit_min_loss_pct: float | None = None,
    
    # Transaction costs
    commission_per_trade: float = 0.0,
    commission_pct: float = 0.0,
    slippage_pct: float = 0.0,
    
    # Attribution
    enable_attribution: bool = True,
    entry_conditions: list | None = None,
    exit_conditions: list | None = None,
    
    # Short selling
    short_entry_signal: pd.Series | None = None,
    short_exit_signal: pd.Series | None = None,
    short_entry_conditions: list | None = None,
    short_exit_conditions: list | None = None,
    
    # Leverage
    leverage: float = 1.0,
    
    # Pluggable exit rules
    exit_rules: list[ExitRule] | None = None,
    
    # Counter-trades
    enable_counter_trades: bool = False,
    counter_tp_multiplier: float = 1.5,
    
) -> tuple[list[dict], pd.Series]:  # (trade_log, equity_curve)
```

### Position Sizing Modes

| Mode | Formula | Use Case |
|------|---------|----------|
| `full_capital` | `shares = cash / price` | Use all available capital |
| `percent_capital` | `shares = (cash × pct/100) / price` | Fixed percentage of capital |
| `fixed_amount` | `shares = fixed_amount / price` | Constant dollar amount |
| `risk_based` | `shares = (capital × risk_pct) / stop_distance` | Size based on stop loss distance |

### Leverage Mechanics

```
Entry:
  notional = shares × entry_price
  margin = notional / leverage
  cash_deducted = margin + commission

Liquidation Price:
  LONG:  liquidation_price = entry_price × (1 - 1/leverage)
  SHORT: liquidation_price = entry_price × (1 + 1/leverage)

Example (2x leverage, entry at $100):
  LONG liquidation  = $100 × (1 - 0.5) = $50  (50% drop)
  SHORT liquidation = $100 × (1 + 0.5) = $150 (50% rise)
```

### Short Selling

Independent state machine for short positions:

| Aspect | LONG | SHORT |
|--------|------|-------|
| Entry | Buy (pay more with slippage) | Sell (receive less with slippage) |
| Exit | Sell (receive less with slippage) | Buy (pay more with slippage) |
| PnL | (exit - entry) × shares | (entry - exit) × shares |
| SL Trigger | bar_low ≤ SL price | bar_high ≥ SL price |
| TP Trigger | bar_high ≥ TP price | bar_low ≤ TP price |
| MTM Value | shares × current_price | shares × (2 × entry - current) |

### Stop Loss Priority Order

1. **Liquidation** (leveraged positions only)
2. **Dynamic Stop** (indicator-based trailing stop)
3. **Static Stop Loss** (percentage from entry)
4. **Take Profit** (percentage from entry)
5. **Exit Rules** (pluggable rule system)

### TradeRecord Fields

```python
@dataclass
class TradeRecord:
    # Core fields
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float
    shares: float
    pnl: float                    # Absolute profit/loss
    pnl_pct: float                # Percentage return
    trade_duration_days: int
    exit_reason: str              # "signal", "stop_loss", "take_profit", "liquidation", "force_close", rule.name
    direction: str = "LONG"       # "LONG" or "SHORT"
    
    # Commissions
    entry_commission: float
    exit_commission: float
    total_commission: float
    
    # Attribution (optional)
    entry_conditions_met: list[str] | None
    exit_conditions_met: list[str] | None
    entry_signal_strength: float | None
    market_return_during_trade: float | None
    alpha: float | None
    indicator_snapshot_entry: dict | None
    indicator_snapshot_exit: dict | None
```

---

## 7. Exit Rules System

**File:** `backend/app/engine/exit_rules.py`

### Purpose
Pluggable exit conditions evaluated per-bar with state captured at entry.

### ExitRule Dataclass

```python
@dataclass
class ExitRule:
    name: str = "exit_rule"                       # Rule identifier (becomes exit_reason)
    ref_col: str = ""                             # Column to capture at entry
    monitor_col: str = ""                         # Column to monitor each bar
    operator: str = "LT"                          # LT, GT, EQ, GTE, LTE
    activation_threshold: float | None = None    # Gate: only apply if ref meets threshold
    activation_operator: str = "LT"              # Operator for activation check
    min_loss_pct: float | None = None            # Only fire if losing ≥ this %
    skip_col: str | None = None                  # Skip if this column is True
    fixed_threshold: float | None = None         # Use fixed value instead of ref_col
```

### Workflow

```
At Entry (_capture_exit_rule_states):
  1. For each ExitRule:
     - Capture ref_col value at entry bar (or use fixed_threshold)
     - Check activation_threshold with activation_operator
     - Store {rule, ref_value, activated} in position state

Per Bar (_check_exit_rules):
  1. For each active rule:
     - Read monitor_col at current bar
     - Check skip_col (if True, skip this bar)
     - Compare monitor_val vs ref_value using operator
     - If triggered AND (min_loss_pct met or not specified):
       - Set pending_exit = True
       - Set exit_reason = rule.name
       - Exit fills at next bar open
```

### Example Rules

```python
# ATR-based exit: exit when ATR drops below entry ATR
atr_exit = ExitRule(
    name="atr_exit",
    ref_col="atr_14",           # Captured at entry
    monitor_col="atr_14",       # Checked each bar
    operator="LT",              # Exit when monitor < ref
    min_loss_pct=1.0           # Only if losing ≥ 1%
)

# RSI threshold exit: exit when RSI drops below 20
rsi_20 = ExitRule(
    name="rsi_20",
    monitor_col="rsi_14",
    fixed_threshold=20.0,       # Fixed value, no ref capture
    operator="LT",
    min_loss_pct=1.0
)

# Conditional activation: only activate if RSI < 30 at entry
rsi_conditional = ExitRule(
    name="rsi_exit",
    ref_col="rsi_14",
    monitor_col="rsi_14",
    operator="GT",
    activation_threshold=30.0,   # Only activates if entry RSI < 30
    activation_operator="LT"
)
```

---

## 8. Report Generator

**File:** `backend/app/engine/report_generator.py`

### Performance Metrics

| Metric | Formula | Notes |
|--------|---------|-------|
| **Total Return %** | (final - initial) / initial × 100 | Cumulative return |
| **CAGR** | (final/initial)^(1/years) - 1 | Annualized return |
| **Sharpe Ratio** | (mean_daily - rf) / std_daily × √252 | Risk-adjusted return |
| **Max Drawdown %** | min(equity - running_max) / running_max × 100 | Peak-to-trough decline |
| **Win Rate %** | wins / total × 100 | Percentage profitable |
| **Profit Factor** | gross_profit / gross_loss | Win/loss ratio |
| **Avg Win** | sum(positive_pnl) / wins | Average winning trade |
| **Avg Loss** | sum(negative_pnl) / losses | Average losing trade |
| **Avg Win/Loss Ratio** | avg_win / abs(avg_loss) | Win magnitude vs loss |
| **Longest Drawdown** | max(drawdown_period_days) | Max underwater days |
| **Avg Trade Duration** | mean(trade_duration_days) | Holding period |

### Benchmark Comparison

| Metric | Description |
|--------|-------------|
| **Benchmark Return %** | Buy-and-hold return |
| **Alpha** | Strategy return - benchmark return |
| **Beta** | cov(strategy, benchmark) / var(benchmark) |
| **Benchmark Sharpe** | Buy-and-hold Sharpe ratio |
| **Benchmark Max DD** | Buy-and-hold max drawdown |

### Attribution Report

Generated when `enable_attribution=True`:

- **Total Alpha:** Sum of per-trade alpha values
- **Signal Strength Bins:** Strong (≥0.7), Medium (0.3-0.7), Weak (<0.3)
- **Win Rate by Bin:** Correlation between signal strength and profitability
- **Condition Frequency:** How often each condition triggered

### Binning Report

Requires ≥50 trades:

- Quintile analysis of indicator ranges vs. trade profitability
- Correlation coefficient and p-value significance
- Identifies profitable indicator value ranges

---

## 9. Robustness Analysis Module

**Directory:** `backend/app/engine/robustness/`

### 9.1 Parameter Sensitivity Analysis

**File:** `parameter_sensitivity.py`

**Algorithm:**
1. Generate ±variation_pct (default 20%) variants of all numeric indicator params
2. Run backtest for baseline and each variant
3. Calculate coefficient of variation (CV) for key metrics
4. Stability score = 1 - mean(CVs), capped [0, 1]

**Classification:**
| Score | Level | Interpretation |
|-------|-------|----------------|
| ≥ 0.8 | ROBUST | Safe to deploy |
| 0.6-0.8 | MODERATE | Use with caution |
| < 0.6 | FRAGILE | Possible overfitting |

### 9.2 Walk-Forward Validation

**File:** `walk_forward.py`

**Algorithm:**
1. Divide data into N equal windows by bar count
2. Run independent backtest per window with fixed parameters
3. Calculate consistency score from per-metric CV
4. Assess robustness from score and profitable window percentage

**Classification:**
| Criteria | Level |
|----------|-------|
| Score ≥ 0.8 AND ≥80% profitable windows | ROBUST |
| Score ≥ 0.6 AND ≥60% profitable windows | MODERATE |
| Otherwise | FRAGILE |

### 9.3 Regime Detection

**File:** `regime_detection.py`

**Segmentation Strategies:**

| Strategy | Method | Regimes |
|----------|--------|---------|
| `l1_trend` | L1 Trend Filter (cvxpy) | BULL, BEAR |
| `pelt_directional` | PELT on rolling mean + R² labeling | BULL, BEAR, CHOPPY, RANGING |
| `pelt_volatility` | PELT on rolling volatility | HIGH_VOL, LOW_VOL, TRANSITION |

**Dependency Assessment:**
| CV | Classification |
|----|----------------|
| < 0.3 | INDEPENDENT |
| 0.3-0.6 | MODERATE |
| > 0.6 | DEPENDENT |

### 9.4 Feature Conditioning

**File:** `feature_conditioning.py`

**Features Extracted at Trade Entry:**
- `volatility`: Rolling std of log returns
- `trend_strength`: R² from OLS regression
- `trend_slope`: OLS slope
- `price_vs_sma50`: (price - SMA50) / SMA50
- `returns_autocorr`: Lag-1 autocorrelation
- `rsi_level`: RSI value (if available)
- `atr_pct`: ATR as % of price (if available)

**Analysis:**
1. Bin each feature into quartiles
2. Calculate win rate and avg PnL per bin
3. Identify winning conditions (≥60% win rate) and losing conditions (≤40%)
4. Calculate feature importance from win rate variance across bins

### 9.5 Segmentation Factory

**File:** `segmentation/factory.py`

```python
SegmentationFactory.create_strategy(strategy_name, **kwargs)

# Available strategies:
# - "l1_trend": L1TrendStrategy(k=0.015)
# - "pelt_volatility": VolatilityStrategy()
# - "pelt_directional": DirectionalStrategy(r2_mode, r2_percentile, r2_fixed)
```

---

## 10. Data Providers

**Directory:** `backend/app/providers/`

### Provider Interface

```python
class DataProvider(ABC):
    def __init__(self, timezone: str = "Asia/Kolkata"):
        self.timezone = ZoneInfo(timezone)
    
    @abstractmethod
    async def fetch_ohlcv(
        self, ticker: str, start_date: date, end_date: date,
        interval: str = "1d", asset_class: str = "STOCK"
    ) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        pass
```

### YFinanceProvider

**File:** `yfinance_provider.py`

| Aspect | Details |
|--------|---------|
| Library | yfinance |
| Asset Classes | STOCK, CRYPTO (via ticker format) |
| Intervals | 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo |
| Intraday Limit | 60 days |
| Adjustments | auto_adjust=True (splits/dividends) |
| Rate Limiting | None (library handles) |

### BinanceProvider

**File:** `binance_provider.py`

| Aspect | Details |
|--------|---------|
| API | Binance Futures REST API (fapi) |
| Asset Classes | CRYPTO only |
| Intervals | 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1mo |
| Pagination | 1000-bar chunks with automatic continuation |
| Rate Limiting | 600 req/min with sleep backoff |
| Symbol Normalization | BTC-USD → BTCUSDT, BTC/USDT → BTCUSDT |

### Provider Factory

```python
ProviderFactory.create_provider(provider_name, timezone="Asia/Kolkata")

# provider_name options:
# - "yfinance": YFinanceProvider
# - "binance": BinanceProvider
```

---

## 11. API Layer

**Directory:** `backend/app/api/`

### Endpoint Summary

| Category | Method | Endpoint | Async | Description |
|----------|--------|----------|-------|-------------|
| **Strategies** | GET | `/strategies` | No | List strategies (paginated) |
| | POST | `/strategies` | No | Create strategy |
| | GET | `/strategies/{id}` | No | Get strategy |
| | PUT | `/strategies/{id}` | No | Update strategy |
| | DELETE | `/strategies/{id}` | No | Delete strategy (cascades) |
| **Backtests** | POST | `/backtests` | Yes (Celery) | Run backtest async |
| | GET | `/backtests` | No | List backtests |
| | GET | `/backtests/{id}` | No | Get backtest (poll for results) |
| | GET | `/backtests/{id}/trades` | No | Get trade log (paginated) |
| | DELETE | `/backtests/{id}` | No | Delete backtest |
| **Robustness** | POST | `/robustness/parameter-sensitivity` | Yes (Celery) | Parameter sensitivity |
| | POST | `/robustness/walk-forward` | Yes (Celery) | Walk-forward validation |
| | POST | `/robustness/regime-detection` | Yes (Celery) | Regime detection |
| | POST | `/robustness/feature-conditioning` | Yes (Celery) | Feature conditioning |
| | GET | `/robustness/{id}` | No | Get analysis results |
| | DELETE | `/robustness/{id}` | No | Delete analysis |
| **Tickers** | GET | `/tickers/validate` | No | Validate ticker |
| **Health** | GET | `/health` | No | Health check |

### Async Patterns

- **API Layer:** FastAPI with `async def` handlers
- **Database:** SQLAlchemy async engine with `AsyncSession`
- **Eager Loading:** `selectinload()` to avoid N+1 queries
- **Task Layer:** Celery tasks wrap async code with `asyncio.run()`
- **Polling:** Robustness endpoints poll database briefly (6 seconds) for record creation

---

## 12. Database Models

**Directory:** `backend/app/models/`

### Entity Relationship Diagram

```
┌──────────┐       ┌───────────────┐       ┌─────────────────┐
│   User   │──1:N──│   Strategy    │──1:N──│    Indicator    │
└──────────┘       └───────────────┘       └─────────────────┘
                          │
                          ├──1:N──┌─────────────────┐──1:N──┌─────────────┐
                          │       │ ConditionGroup  │       │  Condition  │
                          │       └─────────────────┘       └─────────────┘
                          │
                          ├──1:N──┌─────────────────┐──1:N──┌─────────────┐
                          │       │  BacktestRun    │       │  TradeLog   │
                          │       └─────────────────┘       └─────────────┘
                          │
                          └──1:N──┌─────────────────────┐──1:N──┌─────────────────────────┐
                                  │ RobustnessAnalysis  │       │RobustnessVariantBacktest│
                                  └─────────────────────┘       └─────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                            OhlcvBar                                     │
│  (Standalone cache table, unique on: ticker, asset_class, resolution, ts)│
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Tables

| Table | Primary Key | Foreign Keys | Cascade Delete |
|-------|-------------|--------------|----------------|
| users | id (UUID) | - | strategies |
| strategies | id (UUID) | user_id | indicators, condition_groups, backtest_runs, robustness_analyses |
| indicators | id (UUID) | strategy_id | - |
| condition_groups | id (UUID) | strategy_id | conditions |
| conditions | id (UUID) | group_id | - |
| backtest_runs | id (UUID) | strategy_id | trade_logs, robustness_variant_backtests |
| trade_logs | id (UUID) | run_id | - |
| robustness_analyses | id (UUID) | strategy_id | variant_backtests |
| robustness_variant_backtests | id (UUID) | analysis_id, backtest_run_id | - |
| ohlcv_bars | id (UUID) | - | - |

### Key Constraints

- **ohlcv_bars:** Unique constraint on (ticker, asset_class, resolution, ts)
- **All tables:** UUID primary keys
- **Timestamps:** created_at (server default), updated_at (auto-update)
- **Flexible data:** JSONB for indicator params, backtest reports, analysis results

---

## 13. Background Tasks (Celery)

**Directory:** `backend/app/tasks/`

### Task Registry

| Task | Function | Description |
|------|----------|-------------|
| `run_backtest_task` | `backtest_task.py` | Execute backtest pipeline |
| `run_parameter_sensitivity_analysis` | `robustness_task.py` | Parameter sensitivity analysis |
| `run_walk_forward_validation` | `robustness_task.py` | Walk-forward validation |
| `run_regime_detection` | `robustness_task.py` | Regime detection analysis |
| `run_feature_conditioning` | `robustness_task.py` | Feature conditioning analysis |

### Backtest Task Pipeline

```python
@celery_app.task
def run_backtest_task(run_id: str):
    1. Load BacktestRun and Strategy (eager-load indicators, conditions)
    2. Fetch OHLCV data via fetch_ohlcv_async()
    3. Compute indicators via compute_indicators()
    4. Trim warmup period
    5. Evaluate entry/exit conditions (or expressions)
    6. Handle short selling signals
    7. Run backtest via run_backtest()
    8. Calculate benchmark (buy-and-hold)
    9. Generate report via generate_report()
    10. Generate attribution/binning reports (if enabled)
    11. Persist trades to TradeLog table
    12. Update status to COMPLETE (or FAILED)
```

### Async Pattern

```python
@celery_app.task
def run_task(params):
    async def _inner():
        async with get_session() as session:
            # All async database operations here
            pass
    
    asyncio.run(_inner())
```

---

## 14. Usage Patterns

### Pattern 1: Simple Trend-Following

```python
# 1. Fetch & prepare data
df = fetch_ohlcv("AAPL", start, end, "1d", "STOCK")

# 2. Add indicators
df = compute_indicators(df, [
    {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20}},
    {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50}},
])

# 3. Trim warmup
df, warmup_bars = trim_warmup_period(df)

# 4. Define signals
entry_signal = evaluate_conditions(df, {
    "logic": "AND",
    "conditions": [
        {"left_operand_value": "sma_20", "operator": "CROSSES_ABOVE", "right_operand_value": "sma_50"}
    ]
})

# 5. Run backtest
trades, equity = run_backtest(
    df=df,
    entry_signal=entry_signal,
    exit_signal=exit_signal,
    initial_capital=10000,
    stop_loss_pct=3.0,
    take_profit_pct=8.0,
)

# 6. Generate report
report = generate_report(trades, equity, 10000)
```

### Pattern 2: Heikin Ashi with Donchian Breakout

```python
# Replace OHLC with Heikin Ashi
df = compute_indicators(df, [{"indicator_type": "HEIKINASHI", "alias": "ha", "params": {}}])
df["open"], df["high"], df["low"], df["close"] = df["ha_open"], df["ha_high"], df["ha_low"], df["ha_close"]

# Compute indicators on HA candles
df = compute_indicators(df, [
    {"indicator_type": "DONCHIAN", "alias": "dc_20", "params": {"period": 20}},
    {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50}},
])

# Manual crossover detection
long_entry = (df["dc_20_mid"] > df["sma_50"]) & (df["dc_20_mid"].shift(1) <= df["sma_50"].shift(1))
```

### Pattern 3: Deferred Entry (Two-Stage Confirmation)

```python
# Stage 1: Base signal
base_signal = evaluate_conditions(df, crossover_conditions)

# Stage 2: Wait for confirmation
armed = False
deferred_signal = pd.Series(False, index=df.index)
for i in range(len(df)):
    if base_signal.iloc[i]:
        armed = True
    if armed and df.iloc[i]["close"] > df.iloc[i]["sma_50"]:
        deferred_signal.iloc[i] = True
        armed = False

trades, equity = run_backtest(df, entry_signal=deferred_signal, ...)
```

### Pattern 4: Exit Rules with Activation Gates

```python
from app.engine.exit_rules import ExitRule

# ATR exit: only if losing and ATR drops
atr_exit = ExitRule(
    name="atr_exit",
    ref_col="atr_14",
    monitor_col="atr_14",
    operator="LT",
    min_loss_pct=1.0,
)

# RSI exit: only activates if RSI was oversold at entry
rsi_exit = ExitRule(
    name="rsi_oversold_exit",
    ref_col="rsi_14",
    monitor_col="rsi_14",
    operator="GT",
    activation_threshold=30.0,
    activation_operator="LT",
)

trades, equity = run_backtest(..., exit_rules=[atr_exit, rsi_exit])
```

### Pattern 5: Counter-Trades

```python
# Failed trades automatically trigger opposite direction
trades, equity = run_backtest(
    df=df,
    entry_signal=long_entry,
    exit_signal=long_exit,
    short_entry_signal=short_entry,
    short_exit_signal=short_exit,
    enable_counter_trades=True,
    counter_tp_multiplier=1.5,  # TP = |loss%| × 1.5
)
```

---

## 15. File Reference

### Engine Modules

| File | Purpose |
|------|---------|
| `backend/app/engine/data_layer.py` | OHLCV fetching, caching, provider orchestration |
| `backend/app/engine/indicator_layer.py` | Technical indicator computation |
| `backend/app/engine/condition_engine.py` | Condition evaluation, expressions |
| `backend/app/engine/state_machine.py` | Core backtest simulation |
| `backend/app/engine/exit_rules.py` | Exit rule dataclass |
| `backend/app/engine/report_generator.py` | Performance metrics calculation |
| `backend/app/engine/signal_transformers.py` | Signal preprocessing utilities |

### Robustness Modules

| File | Purpose |
|------|---------|
| `backend/app/engine/robustness/regime_detection.py` | Market regime detection |
| `backend/app/engine/robustness/walk_forward.py` | Walk-forward validation |
| `backend/app/engine/robustness/parameter_sensitivity.py` | Parameter sensitivity analysis |
| `backend/app/engine/robustness/feature_conditioning.py` | Feature conditioning analysis |
| `backend/app/engine/robustness/segmentation/factory.py` | Segmentation strategy factory |
| `backend/app/engine/robustness/segmentation/l1_trend_strategy.py` | L1 trend filter |
| `backend/app/engine/robustness/segmentation/volatility_strategy.py` | Volatility-based segmentation |
| `backend/app/engine/robustness/segmentation/directional_strategy.py` | Directional segmentation |

### Data Providers

| File | Purpose |
|------|---------|
| `backend/app/providers/base.py` | Abstract provider interface |
| `backend/app/providers/factory.py` | Provider factory |
| `backend/app/providers/yfinance_provider.py` | Yahoo Finance implementation |
| `backend/app/providers/binance_provider.py` | Binance REST API implementation |

### API Layer

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI application entrypoint |
| `backend/app/api/routes/strategies.py` | Strategy CRUD endpoints |
| `backend/app/api/routes/backtests.py` | Backtest execution endpoints |
| `backend/app/api/routes/robustness.py` | Robustness analysis endpoints |
| `backend/app/api/routes/tickers.py` | Ticker validation endpoint |

### Database & Tasks

| File | Purpose |
|------|---------|
| `backend/app/models/strategy.py` | Strategy, Indicator, Condition models |
| `backend/app/models/backtest.py` | BacktestRun, TradeLog models |
| `backend/app/models/robustness.py` | RobustnessAnalysis models |
| `backend/app/models/ohlcv.py` | OHLCVBar cache model |
| `backend/app/tasks/backtest_task.py` | Celery backtest task |
| `backend/app/tasks/robustness_task.py` | Celery robustness tasks |

### Configuration

| File | Purpose |
|------|---------|
| `backend/app/core/config.py` | Settings and environment variables |
| `backend/app/core/database.py` | Database session management |
| `backend/app/celery_app.py` | Celery configuration |
| `docker-compose.yml` | Infrastructure services |

---

## Appendix: Quick Reference

### Indicator Aliases → Output Columns

| Alias | Single Output | Multi-Output |
|-------|---------------|--------------|
| `sma_50` | `sma_50` | - |
| `macd` | - | `macd_macd`, `macd_signal`, `macd_hist` |
| `bb` | - | `bb_upper`, `bb_mid`, `bb_lower` |
| `stoch` | - | `stoch_k`, `stoch_d` |
| `ichimoku` | - | `ichimoku_tenkan`, `ichimoku_kijun`, `ichimoku_span_a`, `ichimoku_span_b`, `ichimoku_chikou` |

### Exit Reasons

| Reason | Trigger |
|--------|---------|
| `signal` | Exit signal condition met |
| `stop_loss` | Price dropped below SL |
| `take_profit` | Price rose above TP |
| `trailing_stop` | Dynamic stop triggered (profitable) |
| `liquidation` | Leveraged position wiped |
| `force_close` | Last bar of backtest |
| `{rule.name}` | Custom exit rule triggered |

### Status Values

| Entity | Statuses |
|--------|----------|
| BacktestRun | PENDING → RUNNING → COMPLETE / FAILED |
| RobustnessAnalysis | PENDING → RUNNING → COMPLETE / FAILED |

---

*End of Technical Report*
