# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Instructions

**Important:** Any generic important instructions or preferences should be documented in this file so they persist across sessions and all future Claude Code instances can follow them consistently.

### Communication Style

- **Do NOT include code examples in discussions unless explicitly requested**
- Keep discussions focused on concepts, architecture, and strategy
- Use high-level descriptions and pseudocode when explaining technical approaches
- Only write actual code when:
  1. User explicitly asks for code
  2. User asks to implement a feature
  3. User is debugging and needs code fixes
- In planning and discussion phases, describe what needs to be done without showing implementation details

### Git Commit Guidelines

- **Commit messages must be concise, clear, and ONE-LINER only**
- Never use multi-line commit messages with detailed descriptions
- Keep the entire commit message under 100 characters when possible
- Make a commit for every significant change, feature implementation, or improvement
- Do not bundle multiple unrelated changes into a single commit
- Use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, etc.
- Examples:
  - ✅ GOOD: `feat: add LOOKBACK operand type for historical comparisons`
  - ✅ GOOD: `fix: prevent negative cash in commission calculation`
  - ❌ BAD: Multi-paragraph commit message with bullet points and detailed explanations

### Git Branching Workflow

- **Never commit directly to `master`** - Always create a feature/bugfix branch
- Branch naming conventions:
  - `feature/feature-name` for new features
  - `bugfix/bug-description` for bug fixes
  - `refactor/component-name` for refactoring work
- Create a branch before making changes: `git checkout -b bugfix/description`
- Commit changes to the branch
- When ready, the branch can be merged to master via PR or direct merge

### Pull Request Guidelines

- **ALWAYS provide PR title and description after committing all changes**
- User will create the PR, but you must provide the content
- PR title should be concise and descriptive (same style as commit messages)
- PR description should include:
  - Summary of changes
  - Why the changes were made
  - What was tested
  - Any breaking changes or important notes
- Format PR description as markdown
- Example:
  ```
  ## PR Title
  feat: add LOOKBACK operand type for historical comparisons

  ## PR Description

  ### Summary
  Implements lookback comparisons to enable checking if indicators are rising/falling.

  ### Changes
  - Added LOOKBACK operand type with format "column:offset"
  - 14 comprehensive unit tests
  - Demo script showing usage examples

  ### Testing
  All tests passing ✅
  ```

### Development Priorities

- **UI is currently the least priority** - Do not make any changes to the frontend (`frontend/` directory) unless explicitly requested
- Focus on backend functionality, engine improvements, and core features

### File Format Preferences

- Generate `.txt` files for reports, documentation, and analysis by default
- Only generate `.md` (Markdown) files when explicitly requested by the user
- **All documentation files should be placed in `docs/` folder** (e.g., `docs/BUG_SUMMARY.txt`, `docs/ANALYSIS.txt`)
- Exception: Project root files like `README.md`, `CLAUDE.md` stay in root

### Documentation Organization

Feature-specific documentation is organized in `docs/`:
- **POSITION_SIZING.txt** - Position sizing methods (full_capital, percent_capital, fixed_amount, risk_based)
- **INDICATORS.txt** - All supported indicators with parameters and examples
- **OPERATORS.txt** - Condition operators and operand types reference
- **V1_LIMITATIONS.txt** - Known limitations and V2 roadmap

When adding new features, update the relevant documentation file. If a feature is significant enough, create a new dedicated doc file.

## Project Overview

This is a full-stack backtesting application for evaluating technical indicator-based trading strategies. The system uses FastAPI (backend), React/TypeScript (frontend), PostgreSQL (data store), Redis (caching/message broker), and Celery (async task processing).

## Development Setup

### Prerequisites
- Python 3.12+ (managed with `.python-version`)
- Node.js 18+
- Docker and Docker Compose (for PostgreSQL and Redis)

### Initial Setup

Start infrastructure:
```bash
docker-compose up -d
```

Backend setup:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
```

Frontend setup:
```bash
cd frontend
npm install
```

### Running the Application

**Backend API (Terminal 1):**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Celery Worker (Terminal 2):**
```bash
cd backend
source .venv/bin/activate
celery -A app.celery_app.celery_app worker --loglevel=info
```

**Frontend Dev Server (Terminal 3):**
```bash
cd frontend
npm run dev
```

Access at: http://localhost:5173

### Testing

Run all backend tests:
```bash
cd backend
pytest tests/
```

Run specific test types:
```bash
pytest tests/unit/
pytest tests/integration/
```

Run smoke tests (milestone validation):
```bash
python scripts/m1_smoke.py
python scripts/m2_smoke.py
python scripts/m3_smoke.py
python scripts/m4_smoke.py
python scripts/m5_smoke.py
```

### Database Migrations

Create a new migration:
```bash
cd backend
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback last migration:
```bash
alembic downgrade -1
```

## Architecture

### Component Communication Flow

```
React Frontend (Port 5173)
    │
    ├─► FastAPI API (Port 8000)
    │       │
    │       ├─► PostgreSQL (Port 5432) - Persistent storage
    │       ├─► Redis (Port 6379) - OHLCV data cache
    │       └─► Celery Worker
    │               │
    │               ├─► Data Layer (fetch_ohlcv_async)
    │               ├─► Indicator Layer (compute_indicators)
    │               ├─► Condition Engine (evaluate_conditions)
    │               ├─► State Machine (run_backtest)
    │               └─► Report Generator (generate_report)
```

### Core Backend Modules

**Data Pipeline:**
1. `app/engine/data_layer.py` - Multi-provider OHLCV orchestration (Yahoo Finance for stocks, Binance for crypto), Redis + PostgreSQL caching
2. `app/engine/indicator_layer.py` - Computes technical indicators using pandas-ta
3. `app/engine/condition_engine.py` - Evaluates entry/exit conditions (stateless, bar-level)
4. `app/engine/state_machine.py` - Executes backtest simulation (position management, fills, P&L, leverage, shorts, exit rules)
5. `app/engine/report_generator.py` - Calculates performance metrics (returns, Sharpe, drawdown)
6. `app/engine/exit_rules.py` - Pluggable ExitRule dataclass for runtime-configurable exit conditions

**Robustness Module:**
- `app/engine/robustness/regime_detection.py` - Market regime detection (PELT directional/volatility, L1 trend)
- `app/engine/robustness/walk_forward.py` - Walk-forward validation with consistency scoring
- `app/engine/robustness/parameter_sensitivity.py` - Parameter sensitivity analysis (±20% variation)
- `app/engine/robustness/feature_conditioning.py` - Statistical feature conditioning (quartile binning)
- `app/engine/robustness/segmentation/` - Pluggable segmentation strategies (factory pattern)

**Data Providers:**
- `app/providers/factory.py` - Provider factory (creates yfinance or binance provider)
- `app/providers/base.py` - Abstract provider interface
- `app/providers/yfinance_provider.py` - Yahoo Finance (stocks + crypto fallback)
- `app/providers/binance_provider.py` - Binance REST API (crypto, 1000-bar chunked pagination)

**API Layer:**
- `app/api/routes/strategies.py` - Strategy CRUD endpoints
- `app/api/routes/backtests.py` - Backtest execution and results
- `app/api/routes/tickers.py` - Ticker search
- `app/api/routes/robustness.py` - Robustness analysis endpoints (param sensitivity, walk-forward, regime, feature conditioning)

**Database Models:**
- `app/models/strategy.py` - Strategy, Indicator, ConditionGroup, Condition
- `app/models/backtest.py` - BacktestRun, TradeLog
- `app/models/ohlcv.py` - OHLCVBar (cached price data)

**Background Tasks:**
- `app/tasks/backtest_task.py` - Celery task for async backtest execution
- `app/tasks/robustness_task.py` - Celery tasks for robustness analyses (param sensitivity, walk-forward, regime detection, feature conditioning)

### Key Concepts

**Strategy Structure:**
- A Strategy contains multiple Indicators (SMA, EMA, RSI, MACD, etc.)
- Each Indicator has an alias and parameters (e.g., `rsi_14` with `period=14`)
- ConditionGroups define ENTRY and EXIT rules
- Each ConditionGroup contains Conditions with logic (AND/OR)
- Conditions compare operands (INDICATOR, OHLCV, SCALAR) using operators (GT, LT, CROSSES_ABOVE, IS_RISING, etc.)

**Backtest Execution:**
- Runs asynchronously via Celery worker
- Fetches historical OHLCV data (with Redis caching)
- Computes all indicators on full dataset
- Trims warmup period (bars where indicators are NaN)
- Evaluates entry/exit signals per bar
- Simulates trades with realistic fills (entry/exit at next bar's open)
- Tracks position, cash, equity over time
- Generates equity curve and trade log

**Data Layer Architecture:**
- Multi-provider: Yahoo Finance (stocks) and Binance (crypto) via factory pattern
- Provider auto-selection: STOCK → yfinance, CRYPTO → binance (overridable)
- Three-layer caching: Redis (24h TTL, msgpack) → PostgreSQL (permanent, batch 500) → Provider API
- Gap detection: validates cached DB data covers request range before returning
- Binance pagination: fetches 1000-bar chunks, auto-advances until end date
- Timezone: defaults to Asia/Kolkata (IST), full ZoneInfo conversion for all providers
- Supported crypto resolutions: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1mo
- Supported stock resolutions: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
- Stock intraday limitation: Yahoo Finance caps at 60 days history
- Symbol normalization: handles BTC-USD, BTC/USDT → BTCUSDT for Binance
- Split/dividend adjustment: yfinance auto_adjust=True

**Position Management:**
- Supports fractional shares (crypto) and integer shares (stocks)
- Position sizing: full_capital, percent_capital, fixed_amount, risk_based
- Dynamic stop loss: trailing stop based on indicator (e.g., ATR)
- Risk management: max position size limits
- Transaction costs: commission per trade (fixed or percentage)
- Slippage: direction-aware (buys pay more, sells receive less)
- Leverage: Binance-style isolated margin with liquidation price
- Short selling: independent short position state machine

**Leverage System:**
- `leverage` param multiplies share count by leverage factor
- Margin = notional_value / leverage (only margin deducted from cash)
- Liquidation price calculated at entry: LONG = entry × (1 - 1/leverage), SHORT = entry × (1 + 1/leverage)
- Liquidation fires when bar_low (LONG) or bar_high (SHORT) crosses liquidation price
- Exit reason: "liquidation" with -100% PnL on the position (not account)

**Short Selling:**
- Independent `short_entry_signal` and `short_exit_signal` params
- Dual position state: `long_pos` and `short_pos` tracked simultaneously
- Direction-aware PnL: SHORT profit = (entry_price - exit_price) × shares
- Direction-aware stops: SL triggers on bar_high (price rising), TP on bar_low (price falling)
- Direction-aware slippage: SHORT entry is a sell (receive less), exit is a buy (pay more)

**Pluggable Exit Rules (ExitRule system):**
- Runtime-configurable exit conditions via `exit_rules=[ExitRule(...)]` param
- Each rule is an `ExitRule` dataclass (in `app/engine/exit_rules.py`)
- Fields: name, ref_col, monitor_col, operator, activation_threshold, activation_operator, min_loss_pct, skip_col, fixed_threshold
- At entry: captures `ref_col` value (frozen for trade lifetime)
- Per bar: compares `monitor_col` against captured ref using operator (LT/GT)
- `fixed_threshold`: compares monitor against a static value (no ref capture needed)
- `activation_threshold`: rule only active if ref meets threshold at entry
- `min_loss_pct`: rule only fires if trade is losing >= this %
- `skip_col`: per-bar boolean column to suppress evaluation
- `name`: stamps trade's `exit_reason` field for attribution
- Engine internals: `_capture_exit_rule_states()` at entry, `_check_exit_rules()` per bar

**Dynamic Take Profit:**
- `dynamic_tp_pct_column` param: column name containing per-bar TP % values
- Captured at entry bar, overrides static `take_profit_pct` for that trade
- Enables strategies with variable TP (e.g., TP = candle range %)

**Indicator Warmup:**
- Moving averages and oscillators need historical data to initialize
- `trim_warmup_period()` removes leading NaN bars after indicator computation
- Ensures at least 30 bars remain after warmup for meaningful backtest

**Operators:**
- Comparison: GT, LT, EQ, GTE, LTE
- Crossover: CROSSES_ABOVE, CROSSES_BELOW
- Trend: IS_RISING, IS_FALLING

**Robustness Analysis Module:**
Four analysis types, all accessible via API endpoints and Celery tasks:

1. **Parameter Sensitivity** (`parameter_sensitivity.py`):
   - Generates ±20% variants of all numeric indicator params
   - Runs backtest for each variant, calculates CV of key metrics
   - Stability score: 1.0 - mean(CVs), capped [0, 1]
   - Levels: ROBUST (≥0.8), MODERATE (0.6-0.8), FRAGILE (<0.6)

2. **Walk-Forward Validation** (`walk_forward.py`):
   - Divides data into N equal windows (default 5)
   - Runs independent backtest per window
   - Consistency score from per-metric coefficient of variation
   - Levels: ROBUST (score ≥0.8 AND ≥80% profitable), MODERATE (≥0.6 AND ≥60%), FRAGILE
   - Windows with <10 trades excluded from CV

3. **Regime Detection** (`regime_detection.py` + `segmentation/`):
   - Three strategies via factory pattern:
     - `pelt_directional`: BULL/BEAR/CHOPPY/RANGING from return slope + R²
     - `pelt_volatility`: HIGH_VOL/LOW_VOL/TRANSITION from rolling volatility
     - `l1_trend`: BULL/BEAR from L1 trend filter (cvxpy solver)
   - Analyzes trade performance per regime
   - Dependency: CV of regime returns → INDEPENDENT (<0.3), MODERATE (0.3-0.6), DEPENDENT (>0.6)

4. **Feature Conditioning** (`feature_conditioning.py`):
   - Extracts market features at each trade entry (all real-time computable)
   - Features: volatility, trend_strength, trend_slope, price_vs_sma50, returns_autocorr, rsi_level, atr_pct
   - Quartile binning: identifies which market conditions produce best/worst trades
   - Importance: variance of win rates across quartiles, normalized 0-1

**Robustness API Endpoints:**
- `POST /robustness/parameter-sensitivity` - Start param sensitivity analysis
- `POST /robustness/walk-forward` - Start walk-forward validation
- `POST /robustness/regime-detection` - Start regime detection (strategy: l1_trend/pelt_directional/pelt_volatility)
- `POST /robustness/feature-conditioning` - Start feature conditioning analysis
- `GET /robustness/{analysis_id}` - Get analysis status/results
- `DELETE /robustness/{analysis_id}` - Delete analysis

### Database Schema

**Core Tables:**
- `users` - User accounts
- `strategies` - Strategy definitions
- `indicators` - Technical indicators (belongs to strategy)
- `condition_groups` - Entry/exit condition groups (belongs to strategy)
- `conditions` - Individual conditions (belongs to condition_group)
- `backtest_runs` - Backtest execution metadata and results
- `trade_logs` - Individual trade records (belongs to backtest_run)
- `ohlcv_bars` - Cached historical price data

**Important Relationships:**
- Strategy → Indicators (1:N, cascade delete)
- Strategy → ConditionGroups (1:N, cascade delete)
- ConditionGroup → Conditions (1:N, cascade delete)
- Strategy → BacktestRuns (1:N, cascade delete)
- BacktestRun → TradeLogs (1:N, cascade delete)

### Environment Configuration

Required `.env` file (root directory):
```env
DATABASE_URL=postgresql+asyncpg://backtest:backtest@localhost:5432/backtest
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_BACKEND_URL=redis://localhost:6379/2
OHLCV_CACHE_TTL_SECONDS=86400
```

Configuration loaded via `app/core/config.py` using `pydantic-settings`.

## Development Guidelines

### Code Organization

- Backend uses async/await pattern with SQLAlchemy async sessions
- All database queries use AsyncSession from `app/core/database.py`
- API schemas defined with Pydantic in `app/api/schemas/`
- Engine modules are pure Python functions (no FastAPI dependencies)
- Frontend uses TypeScript with strict type checking

### Testing Strategy

- Unit tests: Test individual engine modules in isolation
- Integration tests: Test API endpoints with test database
- Smoke tests: End-to-end validation of specific features/milestones
- Mock external dependencies (yfinance) in tests

### Database Conventions

- Use UUID primary keys for all tables
- Timestamps: `created_at` (server default), `updated_at` (auto-update)
- Use cascade deletes for parent-child relationships
- Use JSONB for flexible data (indicator params, backtest results)
- Eager load relationships with `selectinload()` to avoid N+1 queries

### Indicator Implementation

When adding new indicators:
1. Add computation logic in `indicator_layer.py` using pandas-ta
2. Extract the correct column from pandas-ta output (may return DataFrame)
3. Add indicator type to the elif chain in `compute_indicators()`
4. Update indicator warmup detection if indicator requires special handling
5. Add tests in `tests/unit/test_indicator_layer.py`

### Condition Operators

When adding new operators:
1. Add operator string to `OPERATORS` set in `condition_engine.py`
2. Implement logic in `_apply_operator()` function
3. Add tests in `tests/unit/test_condition_engine.py`
4. Update frontend operator dropdown if applicable

### Backtest State Machine

The `state_machine.py` implements the core simulation:
- **States**: NO_POSITION, PENDING_ENTRY, IN_POSITION, PENDING_EXIT
- **Fills**: Entry/exit at next bar's open price (lookahead bias prevention)
- **Periodic Contributions**: Cash added at configured frequency (e.g., weekly, monthly)
- **Dynamic Stop Loss**: Exit when price crosses below indicator-based stop
- **Commission**: Deducted from cash on entry and exit trades (fixed or percentage)
- **Slippage**: Direction-aware price impact applied before commission
- **Force Close**: Open positions closed at last bar
- **Leverage**: Margin-based entry, liquidation price tracking, -100% on wipe
- **Short Selling**: Dual position state (long_pos + short_pos), independent fills
- **Exit Rules**: Pluggable `ExitRule` objects evaluated per bar (stateful, per-trade refs)
- **Dynamic TP**: Per-trade take profit from DataFrame column captured at entry
- **Attribution**: Optional indicator snapshots, alpha calculation, condition tracking

**run_backtest() Full Parameter Signature:**
```python
def run_backtest(
    df, entry_signal, exit_signal, initial_capital,
    asset_class="STOCK",
    shares=0.0,
    periodic_contribution=None,       # {"amount", "frequency", "interval_days", "include_start"}
    position_size_type="full_capital", # full_capital|percent_capital|fixed_amount|risk_based
    position_size_value=100.0,
    stop_loss_pct=None,
    take_profit_pct=None,
    dynamic_stop_column=None,          # Column for indicator-based trailing stop
    dynamic_tp_pct_column=None,        # Column for per-trade TP %
    dynamic_exit_monitor_column=None,  # Legacy: column to monitor for conditional exit
    dynamic_exit_ref_column=None,      # Legacy: column to capture ref at entry
    dynamic_exit_skip_column=None,     # Legacy: skip column for conditional exit
    dynamic_exit_min_loss_pct=None,    # Legacy: min loss gate for conditional exit
    commission_per_trade=0.0,          # Fixed $ per entry/exit
    commission_pct=0.0,                # % of trade value
    slippage_pct=0.0,
    enable_attribution=True,
    entry_conditions=None,
    exit_conditions=None,
    short_entry_signal=None,
    short_exit_signal=None,
    short_entry_conditions=None,
    short_exit_conditions=None,
    leverage=1.0,                      # 1.0 = no leverage
    exit_rules=None,                   # list[ExitRule] - pluggable exit conditions
) -> tuple[list[dict], pd.Series]:     # Returns (trade_log, equity_curve)
```

**Key Helper Functions:**
- `_calculate_position_size()` - Handles all sizing modes including risk_based
- `_apply_slippage()` - Direction-aware price impact
- `_fill_entry()` - Leverage-aware entry with margin/liquidation calculation
- `_execute_exit()` - Direction-aware PnL, commission, proceeds
- `_check_stops()` - Liquidation → dynamic stop → static SL/TP (priority order)
- `_mark_to_market()` - Leveraged MTM for equity curve
- `_capture_exit_rule_states()` - Freeze rule refs at entry
- `_check_exit_rules()` - Evaluate rules per bar

**TradeRecord Fields:**
- Core: entry_date, entry_price, exit_date, exit_price, shares, pnl, pnl_pct, trade_duration_days, exit_reason, direction
- Commission: entry_commission, exit_commission, total_commission
- Attribution (optional): entry_conditions_met, exit_conditions_met, entry_signal_strength, market_return_during_trade, alpha, indicator_snapshot_entry, indicator_snapshot_exit

Do not modify state machine logic without understanding the full trade lifecycle.

### Performance Metrics

Calculated in `report_generator.py`:
- Total return, Sharpe ratio, max drawdown
- Win rate, profit factor, avg win/loss
- Total trades, winning/losing trades
- Trade duration statistics
- Buy-and-hold comparison

## Common Workflows

### Adding a New Technical Indicator

1. Update `backend/app/engine/indicator_layer.py`
2. Add indicator type to `compute_indicators()` function
3. Use pandas-ta library method (e.g., `ta.atr()`)
4. Add to indicator warmup tracking if needed
5. Test with `pytest tests/unit/test_indicator_layer.py`

### Adding a New Condition Operator

1. Update `backend/app/engine/condition_engine.py`
2. Add to `OPERATORS` set
3. Implement in `_apply_operator()` function
4. Test with `pytest tests/unit/test_condition_engine.py`

### Modifying Backtest Logic

1. Update `backend/app/engine/state_machine.py`
2. Ensure fills occur at correct prices (no lookahead bias)
3. Update `TradeRecord` dataclass if adding trade metadata
4. Test with `pytest tests/unit/test_state_machine.py`
5. Run smoke tests to validate end-to-end

### Frontend Changes

- Component files in `frontend/src/pages/`
- API client in `frontend/src/api/client.ts`
- Type definitions in `frontend/src/types/index.ts`
- Build with `npm run build`

### Writing Strategy Smoke Scripts

Smoke scripts (`backend/scripts/smoke_*.py`) are standalone backtest scripts that bypass the API/Celery layer:

1. Import engine modules directly: `fetch_ohlcv`, `compute_indicators`, `trim_warmup_period`, `evaluate_conditions`, `run_backtest`, `generate_report`
2. Define indicators list and entry condition groups
3. Compute custom filters (volume, trend, body/wick ratios) as boolean Series
4. Combine into `entry_signal` (AND of all conditions)
5. Optionally apply deferred entry logic (e.g., wait for close > SMA50)
6. Define `ExitRule` objects for conditional exits
7. Call `run_backtest()` with all parameters
8. Print formatted results with trade log

**Pattern for deferred entry (confirmation candle):**
```python
above_sma50 = df["close"] > df["sma_50"]
deferred_signal = pd.Series(False, index=df.index)
armed = False
for i in range(len(df)):
    if entry_signal.iloc[i]:
        armed = True
    if armed and above_sma50.iloc[i]:
        deferred_signal.iloc[i] = True
        armed = False
entry_signal = deferred_signal
```

**Pattern for ExitRule usage:**
```python
from app.engine.exit_rules import ExitRule

atr_exit = ExitRule(name="atr_exit", ref_col="atr_mean_24", monitor_col="atr_14",
                    min_loss_pct=1.0, skip_col="skip_atr_exit")
rsi_exit = ExitRule(name="rsi_exit", ref_col="rsi_14", monitor_col="rsi_14",
                    activation_threshold=30.0, min_loss_pct=1.0)
rsi_20 = ExitRule(name="rsi_20", monitor_col="rsi_14",
                  fixed_threshold=20.0, min_loss_pct=1.0)

trades, equity = run_backtest(..., exit_rules=[atr_exit, rsi_exit, rsi_20])
```

### Adding a New Exit Rule Type

1. No engine changes needed — ExitRule dataclass covers most patterns
2. For ref-vs-monitor comparison: set `ref_col` + `monitor_col` + `operator`
3. For fixed threshold: set `fixed_threshold` + `monitor_col` (no ref_col needed)
4. For activation gates: set `activation_threshold` + `activation_operator`
5. For loss gates: set `min_loss_pct`
6. For conditional suppression: set `skip_col` (True = skip this bar)
7. Test with `pytest tests/unit/test_state_machine.py`

## Known Patterns

### Async Database Operations

Always use async context managers:
```python
from app.core.database import get_session

async with get_session() as session:
    result = await session.execute(select(Strategy))
    strategies = result.scalars().all()
```

### Eager Loading Relationships

Avoid N+1 queries:
```python
from sqlalchemy.orm import selectinload

stmt = select(Strategy).options(
    selectinload(Strategy.indicators),
    selectinload(Strategy.condition_groups).selectinload(ConditionGroup.conditions)
)
result = await session.execute(stmt)
strategy = result.scalar_one()
```

### Redis Caching Pattern

OHLCV data cached with msgpack serialization:
```python
import redis
import msgpack

redis_client = redis.Redis.from_url(settings.redis_url)
cache_key = f"ohlcv:{ticker}:{start}:{end}"

# Try cache first
cached = redis_client.get(cache_key)
if cached:
    data = msgpack.unpackb(cached)
else:
    # Fetch from yfinance, then cache
    redis_client.setex(cache_key, ttl, msgpack.packb(data))
```

### Celery Task Pattern

Background tasks in `app/tasks/`:
```python
from app.celery_app import celery_app

@celery_app.task(name="task.name")
def my_task(arg1, arg2):
    # Task logic here
    pass
```

## Troubleshooting

### Database Migration Issues
- Check `alembic/versions/` for migration order
- Verify PostgreSQL container is running: `docker ps`
- Reset database: `docker-compose down -v && docker-compose up -d`

### Celery Worker Not Processing
- Ensure Redis is running: `redis-cli ping`
- Check worker logs for errors
- Verify `CELERY_BROKER_URL` in `.env`

### Indicator Warmup Errors
- Increase date range to allow more historical bars
- Reduce indicator periods (e.g., SMA 200 → SMA 50)
- Check `trim_warmup_period()` logic

### Frontend API Connection
- Verify backend running on port 8000
- Check CORS settings in `app/main.py`
- Inspect browser console for errors

## Important Files Reference

- `backend/app/main.py` - FastAPI application entrypoint
- `backend/app/celery_app.py` - Celery configuration
- `backend/app/core/config.py` - Settings and environment variables
- `backend/app/core/database.py` - Database session management
- `backend/app/engine/state_machine.py` - Core backtest engine (positions, fills, leverage, shorts, exit rules)
- `backend/app/engine/exit_rules.py` - ExitRule dataclass for pluggable exit conditions
- `backend/app/engine/data_layer.py` - OHLCV data orchestration (providers, caching, persistence)
- `backend/app/engine/indicator_layer.py` - Technical indicator computation
- `backend/app/engine/condition_engine.py` - Condition evaluation (stateless, bar-level)
- `backend/app/engine/report_generator.py` - Performance metrics calculation
- `backend/app/engine/robustness/regime_detection.py` - Market regime detection
- `backend/app/engine/robustness/walk_forward.py` - Walk-forward validation
- `backend/app/engine/robustness/parameter_sensitivity.py` - Parameter sensitivity analysis
- `backend/app/engine/robustness/feature_conditioning.py` - Feature conditioning
- `backend/app/engine/robustness/segmentation/factory.py` - Segmentation strategy factory
- `backend/app/providers/factory.py` - Data provider factory (yfinance, binance)
- `backend/app/providers/binance_provider.py` - Binance REST API provider
- `backend/app/tasks/robustness_task.py` - Celery tasks for robustness analyses
- `backend/alembic/env.py` - Migration environment setup
- `frontend/src/App.tsx` - React application routes
- `docker-compose.yml` - Infrastructure services
