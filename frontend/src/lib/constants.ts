// Indicator type definitions with their parameters and outputs
export const INDICATOR_CONFIGS = {
  RSI: {
    name: "RSI",
    description: "Relative Strength Index - momentum oscillator",
    params: [
      { key: "period", label: "Period", type: "number", default: 14 },
      { key: "source", label: "Source", type: "select", options: ["close", "open", "high", "low"], default: "close" },
    ],
    outputs: (alias: string) => [alias],
  },
  SMA: {
    name: "SMA",
    description: "Simple Moving Average",
    params: [
      { key: "period", label: "Period", type: "number", default: 20 },
      { key: "source", label: "Source", type: "select", options: ["close", "open", "high", "low"], default: "close" },
    ],
    outputs: (alias: string) => [alias],
  },
  EMA: {
    name: "EMA",
    description: "Exponential Moving Average",
    params: [
      { key: "period", label: "Period", type: "number", default: 20 },
      { key: "source", label: "Source", type: "select", options: ["close", "open", "high", "low"], default: "close" },
    ],
    outputs: (alias: string) => [alias],
  },
  MACD: {
    name: "MACD",
    description: "Moving Average Convergence Divergence",
    params: [
      { key: "fast", label: "Fast Period", type: "number", default: 12 },
      { key: "slow", label: "Slow Period", type: "number", default: 26 },
      { key: "signal", label: "Signal Period", type: "number", default: 9 },
    ],
    outputs: (alias: string) => [`${alias}_macd`, `${alias}_signal`, `${alias}_hist`],
  },
  BB: {
    name: "Bollinger Bands",
    description: "Volatility bands around a moving average",
    params: [
      { key: "period", label: "Period", type: "number", default: 20 },
      { key: "std_dev", label: "Std Dev", type: "number", default: 2 },
    ],
    outputs: (alias: string) => [`${alias}_upper`, `${alias}_mid`, `${alias}_lower`],
  },
  ATR: {
    name: "ATR",
    description: "Average True Range - volatility indicator",
    params: [
      { key: "period", label: "Period", type: "number", default: 14 },
    ],
    outputs: (alias: string) => [alias],
  },
  STOCH: {
    name: "Stochastic",
    description: "Stochastic Oscillator",
    params: [
      { key: "k_period", label: "K Period", type: "number", default: 14 },
      { key: "d_period", label: "D Period", type: "number", default: 3 },
    ],
    outputs: (alias: string) => [`${alias}_k`, `${alias}_d`],
  },
  ADX: {
    name: "ADX",
    description: "Average Directional Index - trend strength",
    params: [
      { key: "period", label: "Period", type: "number", default: 14 },
    ],
    outputs: (alias: string) => [alias, `${alias}_dmp`, `${alias}_dmn`],
  },
  DONCHIAN: {
    name: "Donchian Channel",
    description: "Highest high and lowest low over period",
    params: [
      { key: "period", label: "Period", type: "number", default: 20 },
    ],
    outputs: (alias: string) => [`${alias}_upper`, `${alias}_lower`, `${alias}_mid`],
  },
  SUPERTREND: {
    name: "Supertrend",
    description: "Trend-following indicator using ATR",
    params: [
      { key: "period", label: "Period", type: "number", default: 10 },
      { key: "multiplier", label: "Multiplier", type: "number", default: 3 },
    ],
    outputs: (alias: string) => [alias, `${alias}_trend`, `${alias}_long`, `${alias}_short`],
  },
  HEIKINASHI: {
    name: "Heikin Ashi",
    description: "Smoothed candlesticks",
    params: [],
    outputs: (alias: string) => [`${alias}_open`, `${alias}_high`, `${alias}_low`, `${alias}_close`],
  },
  ROC: {
    name: "ROC",
    description: "Rate of Change",
    params: [
      { key: "period", label: "Period", type: "number", default: 10 },
    ],
    outputs: (alias: string) => [alias],
  },
  OBV: {
    name: "OBV",
    description: "On-Balance Volume",
    params: [],
    outputs: (alias: string) => [alias],
  },
  ICHIMOKU: {
    name: "Ichimoku Cloud",
    description: "Ichimoku Kinko Hyo - comprehensive trend indicator",
    params: [
      { key: "tenkan", label: "Tenkan Period", type: "number", default: 9 },
      { key: "kijun", label: "Kijun Period", type: "number", default: 26 },
      { key: "senkou", label: "Senkou Span B Period", type: "number", default: 52 },
    ],
    outputs: (alias: string) => [`${alias}_tenkan`, `${alias}_kijun`, `${alias}_span_a`, `${alias}_span_b`, `${alias}_chikou`],
  },
} as const;

export type IndicatorType = keyof typeof INDICATOR_CONFIGS;

// Operators for conditions
export const OPERATORS = [
  { value: "GT", label: ">", description: "Greater than" },
  { value: "LT", label: "<", description: "Less than" },
  { value: "GTE", label: ">=", description: "Greater than or equal" },
  { value: "LTE", label: "<=", description: "Less than or equal" },
  { value: "EQ", label: "=", description: "Equal to" },
  { value: "CROSSES_ABOVE", label: "Crosses Above", description: "Crosses above" },
  { value: "CROSSES_BELOW", label: "Crosses Below", description: "Crosses below" },
  { value: "IS_RISING", label: "Is Rising", description: "Value is increasing" },
  { value: "IS_FALLING", label: "Is Falling", description: "Value is decreasing" },
] as const;

export type OperatorType = typeof OPERATORS[number]["value"];

// Operand types
export const OPERAND_TYPES = [
  { value: "INDICATOR", label: "Indicator" },
  { value: "OHLCV", label: "Price (OHLCV)" },
  { value: "SCALAR", label: "Number" },
  { value: "LOOKBACK", label: "Lookback" },
] as const;

export type OperandType = typeof OPERAND_TYPES[number]["value"];

// OHLCV columns
export const OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"] as const;

// Asset classes
export const ASSET_CLASSES = [
  { value: "STOCK", label: "Stock" },
  { value: "CRYPTO", label: "Crypto" },
] as const;

// Bar resolutions
export const BAR_RESOLUTIONS = [
  { value: "1m", label: "1 Minute" },
  { value: "5m", label: "5 Minutes" },
  { value: "15m", label: "15 Minutes" },
  { value: "30m", label: "30 Minutes" },
  { value: "1h", label: "1 Hour" },
  { value: "4h", label: "4 Hours" },
  { value: "1d", label: "1 Day" },
] as const;

// Position sizing types
export const POSITION_SIZE_TYPES = [
  { value: "full_capital", label: "Full Capital", description: "Use all available capital" },
  { value: "percent_capital", label: "Percent of Capital", description: "Use a percentage of capital" },
  { value: "fixed_amount", label: "Fixed Amount", description: "Use a fixed dollar amount" },
  { value: "risk_based", label: "Risk-Based", description: "Size based on stop loss risk" },
] as const;

// Backtest statuses
export const BACKTEST_STATUSES = {
  PENDING: { label: "Pending", color: "bg-yellow-500" },
  RUNNING: { label: "Running", color: "bg-blue-500" },
  COMPLETE: { label: "Complete", color: "bg-green-500" },
  FAILED: { label: "Failed", color: "bg-red-500" },
} as const;

// Helper functions for indicator configuration
export function getIndicatorConfig(type: string) {
  return INDICATOR_CONFIGS[type as IndicatorType] || null;
}

export function getIndicatorOutputs(type: string, alias: string): string[] {
  const config = getIndicatorConfig(type);
  if (!config) return [alias];
  return config.outputs(alias);
}

export function getDefaultParams(type: string): Record<string, number | string> {
  const config = getIndicatorConfig(type);
  if (!config) return {};
  const params: Record<string, number | string> = {};
  config.params.forEach((p) => {
    params[p.key] = p.default;
  });
  return params;
}

// Helper to get indicator configs as array for filtering
export function getIndicatorConfigsArray() {
  return Object.entries(INDICATOR_CONFIGS).map(([type, config]) => ({
    type,
    name: config.name,
    description: config.description,
    params: config.params,
  }));
}

// Check if operator is unary
export function isUnaryOperator(operator: string): boolean {
  return operator === "IS_RISING" || operator === "IS_FALLING";
}
