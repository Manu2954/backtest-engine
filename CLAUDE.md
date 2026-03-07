# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Instructions

**Important:** Any generic important instructions or preferences should be documented in this file so they persist across sessions and all future Claude Code instances can follow them consistently.

### Git Commit Guidelines

- Commits should be concise, clear, and one-liner
- Make a commit for every significant change, feature implementation, or improvement
- Do not bundle multiple unrelated changes into a single commit
- Use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, etc.

### Git Branching Workflow

- **Never commit directly to `master`** - Always create a feature/bugfix branch
- Branch naming conventions:
  - `feature/feature-name` for new features
  - `bugfix/bug-description` for bug fixes
  - `refactor/component-name` for refactoring work
- Create a branch before making changes: `git checkout -b bugfix/description`
- Commit changes to the branch
- When ready, the branch can be merged to master via PR or direct merge

### Development Priorities

- **UI is currently the least priority** - Do not make any changes to the frontend (`frontend/` directory) unless explicitly requested
- Focus on backend functionality, engine improvements, and core features

### File Format Preferences

- Generate `.txt` files for reports, documentation, and analysis by default
- Only generate `.md` (Markdown) files when explicitly requested by the user
- **All documentation files should be placed in `docs/` folder** (e.g., `docs/BUG_SUMMARY.txt`, `docs/ANALYSIS.txt`)
- Exception: Project root files like `README.md`, `CLAUDE.md` stay in root

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
1. `app/engine/data_layer.py` - Fetches OHLCV data from Yahoo Finance, caches in Redis
2. `app/engine/indicator_layer.py` - Computes technical indicators using pandas-ta
3. `app/engine/condition_engine.py` - Evaluates entry/exit conditions
4. `app/engine/state_machine.py` - Executes backtest simulation (position management, fills, P&L)
5. `app/engine/report_generator.py` - Calculates performance metrics (returns, Sharpe, drawdown)

**API Layer:**
- `app/api/routes/strategies.py` - Strategy CRUD endpoints
- `app/api/routes/backtests.py` - Backtest execution and results
- `app/api/routes/tickers.py` - Ticker search

**Database Models:**
- `app/models/strategy.py` - Strategy, Indicator, ConditionGroup, Condition
- `app/models/backtest.py` - BacktestRun, TradeLog
- `app/models/ohlcv.py` - OHLCVBar (cached price data)

**Background Tasks:**
- `app/tasks/backtest_task.py` - Celery task for async backtest execution

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

**Position Management:**
- Supports fractional shares (crypto) and integer shares (stocks)
- Position sizing: full_capital, percent_capital, fixed_amount
- Dynamic stop loss: trailing stop based on indicator (e.g., ATR)
- Risk management: max position size limits
- Transaction costs: commission per trade

**Indicator Warmup:**
- Moving averages and oscillators need historical data to initialize
- `trim_warmup_period()` removes leading NaN bars after indicator computation
- Ensures at least 30 bars remain after warmup for meaningful backtest

**Operators:**
- Comparison: GT, LT, EQ, GTE, LTE
- Crossover: CROSSES_ABOVE, CROSSES_BELOW
- Trend: IS_RISING, IS_FALLING

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
- **Commission**: Deducted from cash on entry and exit trades
- **Force Close**: Open positions closed at last bar

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
- `backend/alembic/env.py` - Migration environment setup
- `frontend/src/App.tsx` - React application routes
- `docker-compose.yml` - Infrastructure services
