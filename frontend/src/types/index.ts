export type IndicatorType =
  | "RSI"
  | "EMA"
  | "SMA"
  | "MACD"
  | "BB"
  | "ATR"
  | "STOCH"
  | "ADX"
  | "ICHIMOKU"
  | "ROC"
  | "OBV";

export type OperandType = "INDICATOR" | "OHLCV" | "SCALAR" | "LOOKBACK";
export type OperatorType =
  | "CROSSES_ABOVE"
  | "CROSSES_BELOW"
  | "IS_RISING"
  | "IS_FALLING"
  | "GT"
  | "LT"
  | "EQ"
  | "GTE"
  | "LTE";

export interface IndicatorInput {
  indicator_type: IndicatorType;
  alias: string;
  params: Record<string, number | string>;
  display_order: number;
}

export interface ConditionInput {
  left_operand_type: OperandType;
  left_operand_value: string;
  operator: OperatorType;
  right_operand_type: OperandType;
  right_operand_value: string;
  display_order: number;
}

export interface ConditionGroupInput {
  logic: "AND" | "OR";
  conditions: ConditionInput[];
}

export interface StrategyCreate {
  name: string;
  description?: string | null;
  indicators: IndicatorInput[];
  entry: ConditionGroupInput;
  exit: ConditionGroupInput;
}

export interface StrategyOut {
  id: string;
  name: string;
  description?: string | null;
  indicators: IndicatorInput[];
  condition_groups: Array<{
    id: string;
    group_type: "ENTRY" | "EXIT";
    logic: "AND" | "OR";
    conditions: ConditionInput[];
  }>;
}

export interface BacktestCreate {
  strategy_id: string;
  ticker: string;
  asset_class: "STOCK" | "CRYPTO";
  start_date: string;
  end_date: string;
  bar_resolution: string;
  initial_capital: number;
  position_size_type?: string;
  position_size_value?: number;
  stop_loss_pct?: number | null;
  take_profit_pct?: number | null;
  dynamic_stop_column?: string | null;
  commission_per_trade?: number;
  commission_pct?: number;
  slippage_pct?: number;
  periodic_contribution?: {
    amount: number;
    frequency: "daily" | "weekly" | "monthly" | "interval_days";
    interval_days?: number;
    include_start?: boolean;
  } | null;
}

export interface BacktestOut {
  id: string;
  strategy_id: string;
  ticker: string;
  asset_class: string;
  start_date: string;
  end_date: string;
  bar_resolution: string;
  initial_capital: number;
  status: string;
  celery_task_id?: string | null;
  error_message?: string | null;
  report?: Record<string, number> | null;
  position_size_type?: string;
  position_size_value?: number;
  stop_loss_pct?: number | null;
  take_profit_pct?: number | null;
  commission_per_trade?: number;
  commission_pct?: number;
  slippage_pct?: number;
  dynamic_stop_column?: string | null;
  periodic_contribution?: {
    amount: number;
    frequency: "daily" | "weekly" | "monthly" | "interval_days";
    interval_days?: number;
    include_start?: boolean;
  } | null;
}

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
  exit_reason?: string;
}
