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
  position_size_type?: string;
  position_size_value?: number;
  stop_loss_pct?: number | null;
  take_profit_pct?: number | null;
  dynamic_stop_column?: string | null;
  commission_per_trade?: number;
  commission_pct?: number;
  slippage_pct?: number;
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
  final_capital?: number;
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
  largest_win?: number;
  largest_loss?: number;
  avg_trade_duration_days: number;
  longest_drawdown_days?: number;
  benchmark_return_pct?: number;
  benchmark_final_capital?: number;
  benchmark_sharpe_ratio?: number;
  benchmark_max_drawdown_pct?: number;
  alpha?: number;
  beta?: number;
  equity_curve?: Array<{ date: string; equity: number; benchmark?: number }>;
  benchmark_curve?: Array<{ date: string; equity: number }>;
  [key: string]: unknown; // Allow indexing by string for dynamic access
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
  status: "PENDING" | "RUNNING" | "COMPLETE" | "COMPLETED" | "FAILED";
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
  dynamic_stop_column?: string;
  commission_per_trade?: number;
  commission_pct?: number;
  slippage_pct?: number;
}

// Aliases for compatibility
export type BacktestRun = Backtest;
export type BacktestOut = Backtest;
export type StrategyOut = Strategy;
export type BacktestCreate = BacktestConfig;

// Indicator type enum - broad set of supported indicators
export type IndicatorType = string;

// Operator types
export type OperatorType = string;

// Operand types
export type OperandType = string;

// Input types for creating/editing
export interface IndicatorInput {
  indicator_type: string;
  alias: string;
  params: Record<string, number | string>;
  display_order?: number;
}

export interface ConditionInput {
  left_operand_type: string;
  left_operand_value: string;
  operator: string;
  right_operand_type: string;
  right_operand_value: string;
  display_order?: number;
}

export interface ConditionGroupInput {
  logic: "AND" | "OR";
  conditions: ConditionInput[];
  group_name?: string;
}

// Trade types
export interface TradeLog {
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
  entry_commission?: number;
  exit_commission?: number;
  total_commission?: number;
  market_return_during_trade?: number;
}

// Filter and sort types for TradeLog
export type SortField = "entry_date" | "exit_date" | "pnl" | "shares" | "trade_duration_days";
export type SortDirection = "asc" | "desc";

export interface TradeFilters {
  directions: ("LONG" | "SHORT")[];
  result: "all" | "winners" | "losers";
  exitReasons: string[];
  entryDateFrom: string;
  entryDateTo: string;
}

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

// Robustness Types - flexible to handle various backend response shapes
export type AnalysisType =
  | "parameter_sensitivity"
  | "walk_forward"
  | "regime_detection"
  | "feature_conditioning";

export type RegimeStrategy = "l1_trend" | "pelt_directional" | "pelt_volatility";

export interface RobustnessAnalysis {
  id: string;
  strategy_id: string;
  analysis_type: AnalysisType;
  status: "PENDING" | "RUNNING" | "COMPLETE" | "COMPLETED" | "FAILED";
  params: Record<string, unknown>;
  report?: Record<string, unknown>;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

// Parameter Sensitivity Report
export interface ParameterSensitivityReport {
  baseline: Record<string, number>;
  variants: Array<{
    indicator_alias: string;
    param_name: string;
    original_value: number;
    variant_value: number;
    direction: "up" | "down";
    deltas: Record<string, number>;
  }>;
  stability_metrics: {
    stability_score: number;
    metric_cvs: Record<string, number>;
  };
  assessment: {
    level: "ROBUST" | "MODERATE" | "FRAGILE";
    recommendation: string;
    flags: string[];
  };
}

// Walk-Forward Report - flexible shape
export interface WalkForwardWindow {
  window_id?: number;
  window_index?: number;
  start_date: string;
  end_date: string;
  total_return?: number;
  total_return_pct?: number;
  sharpe_ratio: number;
  max_drawdown?: number;
  max_drawdown_pct?: number;
  total_trades: number;
  win_rate: number;
}

export interface WalkForwardReport {
  windows: WalkForwardWindow[];
  summary?: {
    consistency_score: number;
    profitable_windows: number;
    total_windows: number;
    avg_return: number;
    avg_sharpe: number;
    avg_trades: number;
  };
  consistency_metrics?: {
    consistency_score: number;
    profitable_windows: number;
    metric_cvs: Record<string, number>;
  };
  assessment: {
    level: "ROBUST" | "MODERATE" | "FRAGILE";
    recommendation: string;
    flags: string[];
  };
}

// Regime Detection Report - flexible shape
export interface RegimeStats {
  regime: string;
  bar_count: number;
  trade_count: number;
  avg_return_pct: number;
  win_rate: number;
  sharpe_ratio?: number;
  start_date?: string;
  end_date?: string;
}

export interface RegimeDetectionReport {
  regimes?: RegimeStats[];
  regime_performance?: RegimeStats[];
  summary?: {
    dependency_level: string;
    cv_return: number;
  };
  regime_dependency?: {
    dependency_level: "INDEPENDENT" | "MODERATE" | "DEPENDENT";
    cv_return: number;
  };
  assessment: {
    level: "ROBUST" | "MODERATE" | "FRAGILE";
    recommendation: string;
    flags: string[];
  };
}

// Feature Conditioning Report - flexible shape
export interface FeatureQuartile {
  quartile: number;
  min_value: number;
  max_value: number;
  trade_count: number;
  win_rate: number;
  avg_return_pct: number;
}

export interface FeatureAnalysis {
  feature_name: string;
  importance: number;
  quartiles: FeatureQuartile[];
  best_quartile: number;
  worst_quartile: number;
}

export interface FeatureConditioningReport {
  features?: FeatureAnalysis[];
  winning_conditions?: Array<{
    feature: string;
    condition: string;
    win_rate: number;
  }>;
  losing_conditions?: Array<{
    feature: string;
    condition: string;
    win_rate: number;
  }>;
  summary?: {
    total_features: number;
    most_important: string;
  };
  assessment: {
    level: "ROBUST" | "MODERATE" | "FRAGILE";
    recommendation: string;
    flags: string[];
  };
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}
