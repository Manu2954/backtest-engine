import { Link } from "react-router-dom";

export default function Dashboard() {
  return (
    <div className="container fade-in">
      <div className="card">
        <h1>Build, Run, Learn</h1>
        <p>
          Start by creating a strategy with indicators and conditions. Then submit a backtest
          and review performance metrics.
        </p>
        <div className="row" style={{ marginTop: "16px" }}>
          <Link className="btn" to="/strategies/new">
            Create Strategy
          </Link>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3>What you can do in M8</h3>
          <ul>
            <li>Create strategies with indicator + condition steps</li>
            <li>Submit a backtest and watch status updates</li>
            <li>View reports and trade logs</li>
          </ul>
        </div>
        <div className="card">
          <h3>Quick links</h3>
          <div className="row">
            <Link className="btn secondary" to="/strategies/new">
              Strategy Builder
            </Link>
            <Link className="btn secondary" to="/strategies">
              Strategy List
            </Link>
            <Link className="btn secondary" to="/backtests">
              Backtest Jobs
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
