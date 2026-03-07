"""
CONDITION ENGINE vs MANUAL FILTERS - When to Use Each

This guide explains when to use the condition engine vs manual pandas filters
in your backtesting strategies.
"""

## CONDITION ENGINE - Use For:

### ✅ Simple Comparisons
- Indicator > Scalar: `RSI > 70`
- Indicator > Indicator: `SMA_50 > SMA_200`
- Price > Indicator: `close > EMA_20`

**Example:**
```python
{
    "left_operand_type": "INDICATOR",
    "left_operand_value": "rsi_14",
    "operator": "GT",
    "right_operand_type": "SCALAR",
    "right_operand_value": "70",
}
```

### ✅ Crossovers
- Bullish cross: `MACD crosses above Signal`
- Bearish cross: `Price crosses below SMA`

**Example:**
```python
{
    "left_operand_type": "INDICATOR",
    "left_operand_value": "macd",
    "operator": "CROSSES_ABOVE",
    "right_operand_type": "INDICATOR",
    "right_operand_value": "macd_signal",
}
```

### ✅ Direction Detection
- Rising: `ADX is rising`
- Falling: `RSI is falling`

**Example:**
```python
{
    "left_operand_type": "INDICATOR",
    "left_operand_value": "adx_14",
    "operator": "IS_RISING",
    "right_operand_type": "SCALAR",
    "right_operand_value": "0",  # dummy value
}
```

### ✅ Logical Combinations
- AND logic: All conditions must be true
- OR logic: Any condition can be true

**Example:**
```python
{
    "logic": "AND",
    "conditions": [
        # Multiple conditions here
    ]
}
```

---

## MANUAL FILTERS - Use For:

### ❌ Time-Shifted Comparisons
Requires `.shift()` to access past/future values

**Example:**
```python
# Chikou Span > price from 26 bars ago
df['filter'] = df['ichimoku_chikou'] > df['close'].shift(26)

# Close above yesterday's high
df['filter'] = df['close'] > df['high'].shift(1)

# RSI crossed 50 in last 3 bars
df['filter'] = (df['rsi_14'] > 50) & (df['rsi_14'].shift(1) <= 50) | \
               (df['rsi_14'].shift(2) <= 50)
```

**Why manual?** Condition engine compares current values only, doesn't support
accessing different time periods.

### ❌ Rolling Window Calculations
Requires `.rolling()` for moving windows

**Example:**
```python
# Close is highest in last 20 bars
df['filter'] = df['close'] == df['close'].rolling(20).max()

# Price above 20-day high
df['filter'] = df['close'] > df['high'].rolling(20).max()

# Volume spike (2x average)
df['filter'] = df['volume'] > df['volume'].rolling(50).mean() * 2
```

**Why manual?** Condition engine doesn't support rolling window aggregations.

### ❌ Rank/Percentile Operations
Requires `.rank()` or `.quantile()`

**Example:**
```python
# RSI in bottom 10% of last 100 bars
df['filter'] = df['rsi_14'] <= df['rsi_14'].rolling(100).quantile(0.10)

# Volume in top 5% of last 50 bars
df['filter'] = df['volume'].rolling(50).rank(pct=True) > 0.95
```

**Why manual?** Condition engine doesn't support ranking or percentile operations.

### ❌ Complex Multi-Step Logic
Requires intermediate calculations

**Example:**
```python
# ATR-based volatility filter
df['atr_avg'] = df['atr_14'].rolling(20).mean()
df['atr_ratio'] = df['atr_14'] / df['atr_avg']
df['filter'] = df['atr_ratio'] > 1.5

# Normalized RSI (0-1 scale over 100 bars)
df['rsi_min'] = df['rsi_14'].rolling(100).min()
df['rsi_max'] = df['rsi_14'].rolling(100).max()
df['rsi_norm'] = (df['rsi_14'] - df['rsi_min']) / (df['rsi_max'] - df['rsi_min'])
df['filter'] = df['rsi_norm'] < 0.2
```

**Why manual?** Condition engine evaluates single conditions, not multi-step
calculations with intermediate variables.

### ❌ Custom Formulas
Requires arithmetic operations between multiple indicators

**Example:**
```python
# Stochastic momentum
df['filter'] = (df['stoch_k'] - df['stoch_d']).abs() > 20

# MACD momentum strength
df['macd_momentum'] = df['macd_hist'].rolling(3).sum()
df['filter'] = df['macd_momentum'] > 0

# Distance from moving average (percentage)
df['distance'] = ((df['close'] - df['sma_50']) / df['sma_50']) * 100
df['filter'] = df['distance'] > 2
```

**Why manual?** Condition engine compares existing columns, doesn't perform
arithmetic operations to create new columns.

---

## DECISION TREE

```
Does your condition require:
│
├─ Comparing current values only (A operator B)?
│  └─ YES → Use Condition Engine ✅
│
├─ Accessing past/future values (.shift)?
│  └─ YES → Use Manual Filter ❌
│
├─ Rolling window calculations (.rolling)?
│  └─ YES → Use Manual Filter ❌
│
├─ Rank/percentile operations?
│  └─ YES → Use Manual Filter ❌
│
└─ Multi-step calculations with intermediate variables?
   └─ YES → Use Manual Filter ❌
```

---

## BEST PRACTICES

### 1. **Maximize Condition Engine Usage**
Use condition engine for as many rules as possible - it's:
- More readable (declarative JSON format)
- Easier to serialize/store in database
- Can be generated from UI or LLM
- Self-documenting (clear operator names)

### 2. **Document Manual Filters**
When using manual filters, add comments explaining:
- Why condition engine can't be used
- What pandas operation is required
- Example: `# MANUAL: Requires .shift(26) for Chikou comparison`

### 3. **Combine Efficiently**
Apply condition engine first, then manual filters:
```python
# Step 1: Condition engine (bulk of logic)
entry_signal = evaluate_conditions(df, entry_group)

# Step 2: Manual filters (only what's necessary)
df['chikou_filter'] = df['chikou'] > df['close'].shift(26)
entry_signal = entry_signal & df['chikou_filter']
```

### 4. **Consider Extending Condition Engine**
If you find yourself repeating the same manual filter pattern, consider
adding it to the condition engine:
- Example: We added `IS_RISING` and `IS_FALLING` operators
- Could add: `GT_SHIFTED`, `LT_SHIFTED` for common shift operations
- Could add: `GT_ROLLING_MAX`, `LT_ROLLING_MIN` for common rolling operations

---

## REAL EXAMPLES

### Ichimoku Strategy (test_ichimoku_strategy.py)
- **6 conditions in engine**: Price vs cloud, crossovers, cloud color
- **1 manual filter**: Chikou vs shifted price (requires `.shift(26)`)

### ADX Strategy (test_adx_all_exit_rules.py)
- **All conditions in engine**: ADX thresholds, DI crossovers, direction
- **0 manual filters**: No shift or rolling operations needed

### Future Strategy Ideas

**Mean Reversion (would need manual filters):**
```python
# Condition engine: RSI < 30
entry_group = {"conditions": [{"left": "rsi", "operator": "LT", "right": "30"}]}

# Manual filter: Price at 20-day low
df['at_low'] = df['close'] == df['close'].rolling(20).min()
entry_signal = evaluate_conditions(df, entry_group) & df['at_low']
```

**Breakout (would need manual filters):**
```python
# Condition engine: Volume > 2M
entry_group = {"conditions": [{"left": "volume", "operator": "GT", "right": "2000000"}]}

# Manual filter: Close above 50-day high
df['breakout'] = df['close'] > df['high'].rolling(50).max()
entry_signal = evaluate_conditions(df, entry_group) & df['breakout']
```

---

## SUMMARY

**Rule of Thumb:**
- **Condition Engine**: "A operator B" comparisons (current values only)
- **Manual Filters**: Pandas operations (shift, rolling, rank, formulas)

**Goal**: Use condition engine for 80%+ of your strategy logic, manual filters
only when pandas operations are absolutely necessary.
