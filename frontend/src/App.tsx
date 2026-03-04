import { Link, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import StrategyBuilder from "./pages/StrategyBuilder";
import BacktestReport from "./pages/BacktestReport";
import TradeLog from "./pages/TradeLog";
import StrategyList from "./pages/StrategyList";
import BacktestList from "./pages/BacktestList";

export default function App() {
  return (
    <div className="app-shell">
      <header>
        <div className="brand">
          <div className="brand-badge" />
          <div>
            <div style={{ fontWeight: 700 }}>Backtest Engine</div>
            <div className="tag">Indicator Strategies</div>
          </div>
        </div>
        <nav>
          <Link to="/">Dashboard</Link>
          <Link to="/strategies">Strategy List</Link>
          <Link to="/strategies/new">New Strategy</Link>
          <Link to="/backtests">Backtest Jobs</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/strategies" element={<StrategyList />} />
          <Route path="/strategies/new" element={<StrategyBuilder />} />
          <Route path="/strategies/:id" element={<StrategyBuilder />} />
          <Route path="/backtests" element={<BacktestList />} />
          <Route path="/backtests/:id" element={<BacktestReport />} />
          <Route path="/backtests/:id/trades" element={<TradeLog />} />
        </Routes>
      </main>
    </div>
  );
}
