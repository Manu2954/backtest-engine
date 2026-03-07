# Priority 1 Implementation: Position Sizing & Stop Loss/Take Profit

## Summary
Implemented position sizing options and risk management (stop loss/take profit) for the backtest engine. These features allow users to:
- Control how much capital to allocate per trade
- Automatically exit losing positions (stop loss)
- Automatically lock in profits (take profit)

## Changes Made

### 1. Core Engine (`state_machine.py`)

#### A. TradeRecord Enhancement
- **Added:** `exit_reason` field to track how trades exit
- **Values:** "signal", "stop_loss", "take_profit", "force_close"
- **Why:** Helps analyze strategy behavior and understand trade outcomes

#### B. New Function Parameters
```python
position_size_type: str = "full_capital"  # How to size positions
position_size_value: float = 100.0        # Percentage or dollar amount
stop_loss_pct: float | None = None        # Auto-exit if loss >= X%
take_profit_pct: float | None = None      # Auto-exit if gain >= X%
```

#### C. Position Sizing Modes
1. **full_capital** (default): Use all available cash (original behavior)
2. **percent_capital**: Use X% of total account value
   - Example: 25% of $100,000 = $25,000 per trade
3. **fixed_amount**: Use fixed dollar amount per trade
   - Example: Always invest $10,000

#### D. Helper Function: `_calculate_position_size()`
- Centralizes position sizing logic
- Handles cash constraints (can't invest more than available)
- Supports fractional shares (crypto) vs integer shares (stocks)

#### E. Risk Management Logic
- **Checked:** Every bar after entry, at open price
- **Stop Loss:** Exits if `price_change_pct <= -stop_loss_pct`
  - Example: Entry $100, stop 5% → exits at $95 or below
- **Take Profit:** Exits if `price_change_pct >= take_profit_pct`
  - Example: Entry $100, profit 10% → exits at $110 or above
- **Priority:** Stop/profit overrides signal exits (risk management first)

### 2. API Schema (`api/schemas/backtest.py`)

#### BacktestCreate (Input)
- Added 4 new optional parameters with backwards-compatible defaults
- Validated by Pydantic before reaching engine

#### BacktestOut (Output)
- Returns configured position sizing and risk parameters
- Shows what settings were used for each backtest

#### TradeLogOut (Output)
- Added `exit_reason` field to show how each trade exited

### 3. Database Models (`models/backtest.py`)

#### BacktestRun Table
New columns:
- `position_size_type`: VARCHAR(32), default "full_capital"
- `position_size_value`: NUMERIC(18,2), default 100.0
- `stop_loss_pct`: NUMERIC(8,4), nullable
- `take_profit_pct`: NUMERIC(8,4), nullable

#### TradeLog Table
New column:
- `exit_reason`: VARCHAR(32), default "signal"

### 4. Celery Task (`tasks/backtest_task.py`)
- Passes new parameters from database to `run_backtest()`
- Persists `exit_reason` when saving trades
- Handles NULL values with fallback defaults

### 5. Database Migration
- File: `0004_add_position_sizing_and_risk_management.py`
- Adds 5 new columns with server defaults
- Backwards compatible (existing data gets defaults)

## Usage Examples

### Example 1: Basic Stop Loss & Take Profit
```python
{
  "strategy_id": "...",
  "ticker": "AAPL",
  "initial_capital": 10000,
  "position_size_type": "full_capital",  # Use all cash
  "stop_loss_pct": 5.0,                   # Exit if -5%
  "take_profit_pct": 10.0                 # Exit if +10%
}
```
**Result:** Buys maximum shares, exits at -5% loss or +10% gain

### Example 2: Conservative Position Sizing
```python
{
  "strategy_id": "...",
  "ticker": "AAPL",
  "initial_capital": 100000,
  "position_size_type": "percent_capital",
  "position_size_value": 25.0,           # Use only 25% per trade
  "stop_loss_pct": 2.0,                  # Tight stop
  "take_profit_pct": 5.0                 # Quick profit
}
```
**Result:** Invests $25,000 per trade, can diversify across 4 positions

### Example 3: Fixed Dollar Amount
```python
{
  "strategy_id": "...",
  "ticker": "AAPL",
  "initial_capital": 50000,
  "position_size_type": "fixed_amount",
  "position_size_value": 10000,          # Always $10,000
  "stop_loss_pct": 3.0
}
```
**Result:** Every trade uses exactly $10,000 (if available)

## Benefits

### Position Sizing
1. **Risk Control:** Limit exposure to single positions
2. **Diversification:** Spread capital across multiple trades
3. **Flexibility:** Test different allocation strategies
4. **Realistic:** Matches professional trading practices

### Stop Loss & Take Profit
1. **Downside Protection:** Automatically cut losses
2. **Profit Taking:** Lock in gains before reversals
3. **Discipline:** Removes emotional decision-making
4. **Strategy Analysis:** See which exits were from signals vs risk rules

## Testing Checklist

Before deploying, verify:
- [ ] Database migration runs successfully
- [ ] Backwards compatibility (old backtests still work)
- [ ] Position sizing calculates correctly for all 3 modes
- [ ] Stop loss triggers at correct percentage
- [ ] Take profit triggers at correct percentage
- [ ] Exit reasons stored correctly in database
- [ ] API endpoints accept new parameters
- [ ] Trade log shows exit reasons

## Next Steps

Remaining V1 enhancements:
- [ ] #5: Add commission/transaction costs
- [ ] #6: Add data quality validation
- [ ] #4: Fix indicator warmup period handling
- [ ] #1: Add buy-and-hold benchmark comparison

## Technical Notes

### Why Check Stop/Profit at Open Price
- Realistic: You see the opening price and can react
- Avoids look-ahead bias: Can't use close price you haven't seen yet
- Conservative: In reality, might get worse fill due to slippage

### Why Clear pending_exit After Stop/Profit
- If stop loss hits, don't also process the signal exit
- Risk management takes priority over strategy signals
- Prevents double-exiting (impossible but good defensive code)

### Floating Point Precision
- Used `abs(cash) < 1e-8` to handle rounding errors
- Numeric(8,4) for percentages: 4 decimal places precision
- Numeric(18,2) for dollar amounts: cent-level precision

### Backwards Compatibility
- All new fields nullable or have defaults
- Existing backtests continue working
- Old trades get "signal" as default exit_reason
- API remains compatible with old clients
