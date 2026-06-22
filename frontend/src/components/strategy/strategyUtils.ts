import type { IndicatorType, ConditionInput, OperatorType } from "../../types";

export const sourceOptions = ["open", "high", "low", "close", "volume"];

export const operatorOptions: OperatorType[] = [
  "CROSSES_ABOVE",
  "CROSSES_BELOW",
  "IS_RISING",
  "IS_FALLING",
  "GT",
  "LT",
  "EQ",
  "GTE",
  "LTE",
];

export const indicatorParamConfig: Record<
  IndicatorType,
  Array<{ key: string; label: string; type: "number" | "select" }>
> = {
  RSI: [
    { key: "period", label: "Period", type: "number" },
    { key: "source", label: "Source", type: "select" },
  ],
  EMA: [
    { key: "period", label: "Period", type: "number" },
    { key: "source", label: "Source", type: "select" },
  ],
  SMA: [
    { key: "period", label: "Period", type: "number" },
    { key: "source", label: "Source", type: "select" },
  ],
  MACD: [
    { key: "fast", label: "Fast", type: "number" },
    { key: "slow", label: "Slow", type: "number" },
    { key: "signal", label: "Signal", type: "number" },
    { key: "source", label: "Source", type: "select" },
  ],
  BB: [
    { key: "period", label: "Period", type: "number" },
    { key: "std_dev", label: "Std Dev", type: "number" },
    { key: "source", label: "Source", type: "select" },
  ],
  ATR: [{ key: "period", label: "Period", type: "number" }],
  STOCH: [
    { key: "k_period", label: "K Period", type: "number" },
    { key: "d_period", label: "D Period", type: "number" },
  ],
  ADX: [{ key: "period", label: "Period", type: "number" }],
  ICHIMOKU: [
    { key: "tenkan", label: "Tenkan", type: "number" },
    { key: "kijun", label: "Kijun", type: "number" },
    { key: "senkou", label: "Senkou", type: "number" },
  ],
  ROC: [
    { key: "period", label: "Period", type: "number" },
    { key: "source", label: "Source", type: "select" },
  ],
  OBV: [],
};

export const indicatorDefaults: Record<
  IndicatorType,
  Record<string, number | string>
> = {
  RSI: { period: 14, source: "close" },
  EMA: { period: 20, source: "close" },
  SMA: { period: 50, source: "close" },
  MACD: { fast: 12, slow: 26, signal: 9, source: "close" },
  BB: { period: 20, std_dev: 2, source: "close" },
  ATR: { period: 14 },
  STOCH: { k_period: 14, d_period: 3 },
  ADX: { period: 14 },
  ICHIMOKU: { tenkan: 9, kijun: 26, senkou: 52 },
  ROC: { period: 12, source: "close" },
  OBV: {},
};

export const indicatorPresets: Array<{
  label: string;
  type: IndicatorType;
  params: Record<string, number | string>;
}> = [
  { label: "RSI 14", type: "RSI", params: { period: 14, source: "close" } },
  { label: "SMA 50", type: "SMA", params: { period: 50, source: "close" } },
  { label: "SMA 200", type: "SMA", params: { period: 200, source: "close" } },
  { label: "EMA 20", type: "EMA", params: { period: 20, source: "close" } },
  {
    label: "MACD Default",
    type: "MACD",
    params: { fast: 12, slow: 26, signal: 9, source: "close" },
  },
  { label: "BB 20", type: "BB", params: { period: 20, std_dev: 2, source: "close" } },
  { label: "ATR 14", type: "ATR", params: { period: 14 } },
];

export function generateAlias(
  type: IndicatorType,
  params: Record<string, number | string>
): string {
  const base = type.toLowerCase();
  const period =
    params.period || params.k_period || params.fast || params.tenkan;
  if (period) {
    return `${base}_${period}`;
  }
  return base;
}

export function getIndicatorColumns(
  type: IndicatorType,
  alias: string
): string[] {
  const columns: string[] = [alias];

  switch (type) {
    case "MACD":
      columns.push(`${alias}_macd`, `${alias}_signal`, `${alias}_hist`);
      break;
    case "BB":
      columns.push(`${alias}_upper`, `${alias}_mid`, `${alias}_lower`);
      break;
    case "STOCH":
      columns.push(`${alias}_k`, `${alias}_d`);
      break;
    case "ADX":
      columns.push(`${alias}_dmp`, `${alias}_dmn`);
      break;
    case "ICHIMOKU":
      columns.push(
        `${alias}_tenkan`,
        `${alias}_kijun`,
        `${alias}_span_a`,
        `${alias}_span_b`,
        `${alias}_chikou`
      );
      break;
  }

  return columns;
}

export function operatorToEnglish(operator: OperatorType): string {
  switch (operator) {
    case "CROSSES_ABOVE":
      return "crosses above";
    case "CROSSES_BELOW":
      return "crosses below";
    case "IS_RISING":
      return "is rising";
    case "IS_FALLING":
      return "is falling";
    case "GT":
      return ">";
    case "LT":
      return "<";
    case "EQ":
      return "=";
    case "GTE":
      return ">=";
    case "LTE":
      return "<=";
    default:
      return operator;
  }
}

export function conditionToEnglish(condition: ConditionInput): string {
  const left = condition.left_operand_value;
  const op = operatorToEnglish(condition.operator);

  if (condition.operator === "IS_RISING" || condition.operator === "IS_FALLING") {
    return `${left} ${op}`;
  }

  const right = condition.right_operand_value;
  return `${left} ${op} ${right}`;
}

export function validateLookbackFormat(value: string): boolean {
  if (!value) return true;
  return /^[\w_]+:-\d+$/.test(value);
}

export function isUnaryOperator(operator: OperatorType): boolean {
  return operator === "IS_RISING" || operator === "IS_FALLING";
}
