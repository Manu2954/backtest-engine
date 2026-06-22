// Strategy Types
export interface Indicator {
  id?: string;
  indicator_type: string;
  alias: string;
  params: Record<string, number | string>;
  display_order?: number;
}

export interface Condition {
  id?: string;
  left_operand_type: string;
  left_operand_value: string;
  operator: string;
  right_operand_type: string;
  right_operand_value: string;
  display_order?: number;
}

export interface ConditionGroup {
  id?: string;
  group_type?: string;
  group_name?: string;
  logic: "AND" | "OR";
  conditions: Condition[];
}

export interface Strategy {
  id: string;
  name: string;
  description?: string;
  indicators: Indicator[];
  condition_groups: ConditionGroup[];
  entry_expression?: string;
  exit_expression?: string;
  short_entry_expression?: string;
  short_exit_expression?: string;
}

export interface StrategyCreate {
  name: string;
  description?: string;
  indicators: Omit<Indicator, "id">[];
  entry?: Omit<ConditionGroup, "id" | "group_type">;
  exit?: Omit<ConditionGroup, "id" | "group_type">;
  short_entry?: Omit<ConditionGroup, "id" | "group_type">;
  short_exit?: Omit<ConditionGroup, "id" | "group_type">;
  entry_groups?: Record<string, Omit<ConditionGroup, "id" | "group_type">>;
  exit_groups?: Record<string, Omit<ConditionGroup, "id" | "group_type">>;
  entry_expression?: string;
  exit_expression?: string;
}

// Backtest Types
export interface BacktestConfig {
  strategy_id: string;
  ticker: string;
  asset_class: string;
  start_date: string;
  end_date: string;
  bar_resolution: string;
  initial_capital: number;
  provider?: string;
  position_size_type: string;
  position_size_value: number;
  stop_loss_pct?: number | null;
  take_profit_pct?: number | null;
  commission_per_trade: number;
  commission_pct: number;
  slippage_pct: number;
  enable_attribution?: boolean;
  periodic_contribution?: {
    amount: number;
    frequency: string;
    interval_days?: number;
    include_start?: boolean;
  };
}

export interface BacktestResults {
  total_return: number;
  total_return_pct?: number;
  cagr: number;
  sharpe_ratio: number;
  sortino_ratio?: number;
  max_drawdown_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  avg_trade_duration_days: number;
  benchmark_return_pct?: number;
  alpha?: number;
  beta?: number;
  equity_curve?: Array<{ date: string; equity: number; benchmark?: number }>;
  benchmark_curve?: Array<{ date: string; equity: number }>;
}

export interface Backtest {
  id: string;
  strategy_id: string;
  ticker: string;
  asset_class: string;
  provider?: string;
  start_date: string;
  end_date: string;
  bar_resolution: string;
  initial_capital: number;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  celery_task_id?: string;
  created_at?: string;
  completed_at?: string;
  error_message?: string;
  results?: BacktestResults;
  report?: BacktestResults; // Legacy alias
  position_size_type?: string;
  position_size_value?: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  commission_per_trade?: number;
  commission_pct?: number;
  slippage_pct?: number;
}

// Alias for compatibility
export type BacktestRun = Backtest;

export interface Trade {
  id: string;
  run_id: string;
  entry_date: string;
  entry_price: number;
  exit_date: string;
  exit_price: number;
  shares: number;
  pnl: number;
  pnl_pct: number;
  trade_duration_days: number;
  direction: "LONG" | "SHORT";
  exit_reason?: string;
  entry_conditions_met?: string[];
  exit_conditions_met?: string[];
  alpha?: number;
}

// Robustness Types
export interface RobustnessAnalysis {
  id: string;
  strategy_id: string;
  analysis_type: string;
  status: "PENDING" | "RUNNING" | "COMPLETE" | "FAILED";
  params: Record<string, unknown>;
  report?: Record<string, unknown>;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}
