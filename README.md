# Backtest Engine

A full-stack backtesting application for evaluating technical indicator-based trading strategies. The system allows users to define custom trading strategies using technical indicators, run backtests against historical market data, and analyze performance metrics.

## Overview

The Backtest Engine is designed to help traders and investors test their technical analysis strategies before risking real capital. It provides a visual strategy builder, asynchronous backtest execution, and comprehensive performance reporting.

### Key Features

- **Visual Strategy Builder**: Create trading strategies using technical indicators with a user-friendly interface
- **Flexible Indicator Support**: Support for multiple technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, etc.) via pandas-ta
- **Conditional Logic**: Define entry and exit conditions with complex logic (AND/OR)
- **Asynchronous Backtesting**: Run backtests as background jobs using Celery
- **Historical Data**: Fetch and cache OHLCV (Open, High, Low, Close, Volume) data from Yahoo Finance
- **Performance Analytics**: Generate comprehensive reports with equity curves, trade logs, and key metrics
- **Periodic Contributions**: Test dollar-cost averaging strategies with configurable contribution schedules
- **Asset Class Support**: Handle both stocks (integer shares) and fractional assets

## Architecture

### Technology Stack

**Backend:**
- **FastAPI**: Modern Python web framework for building APIs
- **SQLAlchemy**: ORM for database interactions
- **PostgreSQL**: Primary data store for strategies and backtest results
- **Celery**: Distributed task queue for asynchronous backtest execution
- **Redis**: Message broker for Celery and caching layer for OHLCV data
- **Alembic**: Database migration management
- **pandas**: Data manipulation and analysis
- **pandas-ta**: Technical analysis indicator library
- **yfinance**: Yahoo Finance data fetching

**Frontend:**
- **React 18**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **React Router**: Client-side routing
- **Recharts**: Data visualization for equity curves
- **Axios**: HTTP client

**Infrastructure:**
- **Docker Compose**: Container orchestration for PostgreSQL and Redis
- **Python 3.12**: Backend runtime

### System Components

```
┌─────────────────┐         ┌─────────────────┐
│  React Frontend │────────▶│   FastAPI API   │
│   (Port 5173)   │         │   (Port 8000)   │
└─────────────────┘         └─────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              ┌──────────┐     ┌─────────┐    ┌──────────┐
              │PostgreSQL│     │  Redis  │    │  Celery  │
              │(Port 5432)     │(Port 6379)   │  Worker  │
              └──────────┘     └─────────┘    └──────────┘
```

## Project Structure

```
backtest-engine/
├── backend/
│   ├── alembic/                 # Database migrations
│   │   └── versions/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/          # API endpoints
│   │   │   │   ├── backtests.py
│   │   │   │   ├── strategies.py
│   │   │   │   └── tickers.py
│   │   │   └── schemas/         # Pydantic models
│   │   ├── core/
│   │   │   ├── config.py        # Application settings
│   │   │   └── database.py      # Database connection
│   │   ├── engine/
│   │   │   ├── condition_engine.py  # Strategy condition evaluation
│   │   │   ├── data_layer.py        # OHLCV data management
│   │   │   ├── indicator_layer.py   # Technical indicator computation
│   │   │   ├── report_generator.py  # Performance metrics
│   │   │   └── state_machine.py     # Backtest execution engine
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── backtest.py
│   │   │   ├── ohlcv.py
│   │   │   └── strategy.py
│   │   ├── tasks/
│   │   │   └── backtest_task.py # Celery background tasks
│   │   ├── celery_app.py
│   │   └── main.py              # FastAPI application
│   ├── scripts/                 # Utility scripts and smoke tests
│   ├── tests/
│   │   ├── integration/
│   │   └── unit/
│   ├── alembic.ini
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts        # API client
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # Main dashboard
│   │   │   ├── StrategyBuilder.tsx  # Strategy creation/editing
│   │   │   ├── StrategyList.tsx
│   │   │   ├── BacktestList.tsx
│   │   │   ├── BacktestReport.tsx   # Performance visualization
│   │   │   └── TradeLog.tsx         # Trade details
│   │   ├── types/
│   │   │   └── index.ts         # TypeScript type definitions
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── docker-compose.yml           # PostgreSQL and Redis services
└── .env                         # Environment variables
```

## How It Works

### Strategy Definition

1. **Indicators**: Define technical indicators with parameters (e.g., SMA with period=20)
2. **Conditions**: Create entry and exit conditions comparing indicators or prices
3. **Logic**: Combine multiple conditions with AND/OR logic

Example Strategy:
```
Entry Conditions (ALL must be true):
  - Close > SMA_20
  - RSI < 30

Exit Conditions (ANY must be true):
  - Close < SMA_20
  - RSI > 70
```

### Backtest Execution

1. User submits a backtest request with:
   - Strategy ID
   - Ticker symbol
   - Date range
   - Initial capital
   - Asset class
   - Optional periodic contributions

2. System fetches or caches OHLCV data from Yahoo Finance

3. Celery worker:
   - Computes all indicators on historical data
   - Evaluates entry/exit conditions for each bar
   - Simulates trades with realistic fill assumptions
   - Applies periodic contributions if configured
   - Generates equity curve and trade log

4. Results stored in database with status tracking

5. Frontend displays performance metrics and visualizations

### Core Engine Logic

The `state_machine.py` implements the backtest execution:
- **Pending Entry**: Entry signal detected, fill at next bar's open
- **Pending Exit**: Exit signal detected, fill at next bar's open
- **Mark-to-Market**: Equity calculated at each bar's close
- **Periodic Contributions**: Cash added at configured intervals
- **Force Close**: Open positions closed at last bar

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker and Docker Compose

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd backtest-engine
```

2. **Start infrastructure services**
```bash
docker-compose up -d
```

3. **Backend setup**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

4. **Frontend setup**
```bash
cd frontend
npm install
```

### Running the Application

**Terminal 1 - Backend API:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
cd backend
source .venv/bin/activate
celery -A app.celery_app.celery_app worker --loglevel=info
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

Access the application at: `http://localhost:5173`

### Environment Variables

Create a `.env` file in the root directory:

```env
DATABASE_URL=postgresql+asyncpg://backtest:backtest@localhost:5432/backtest
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_BACKEND_URL=redis://localhost:6379/2
OHLCV_CACHE_TTL_SECONDS=86400
```

## API Endpoints

### Strategies
- `GET /api/strategies` - List all strategies
- `GET /api/strategies/{id}` - Get strategy details
- `POST /api/strategies` - Create new strategy
- `PUT /api/strategies/{id}` - Update strategy
- `DELETE /api/strategies/{id}` - Delete strategy

### Backtests
- `GET /api/backtests` - List all backtest runs
- `GET /api/backtests/{id}` - Get backtest results
- `POST /api/backtests/run` - Submit new backtest
- `GET /api/backtests/{id}/trades` - Get trade log

### Tickers
- `GET /api/tickers/search?q={query}` - Search for ticker symbols

## Testing

### Run Backend Tests
```bash
cd backend
pytest tests/
```

### Run Unit Tests
```bash
pytest tests/unit/
```

### Run Integration Tests
```bash
pytest tests/integration/
```

### Smoke Tests
```bash
# Run milestone smoke tests
python scripts/m1_smoke.py
python scripts/m2_smoke.py
python scripts/m3_smoke.py
```

## Database Schema

### Core Tables
- **users**: User accounts
- **strategies**: Strategy definitions
- **indicators**: Technical indicators for strategies
- **condition_groups**: Entry/exit condition groups
- **conditions**: Individual conditions
- **backtest_runs**: Backtest execution metadata and results
- **ohlcv_bars**: Cached historical price data

## Performance Metrics

The system calculates comprehensive performance statistics:

- **Total Return**: Percentage gain/loss
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Sharpe Ratio**: Risk-adjusted return
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Average Trade Duration**: Mean holding period
- **Trade Statistics**: Win/loss breakdown, P&L distribution

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Acknowledgments

- **pandas-ta**: Comprehensive technical analysis library
- **yfinance**: Yahoo Finance API wrapper
- **FastAPI**: Modern Python web framework
- **React**: UI library

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.

---

**Built with Python, FastAPI, React, and PostgreSQL**
