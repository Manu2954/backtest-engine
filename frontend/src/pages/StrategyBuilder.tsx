import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  createBacktest,
  createStrategy,
  getStrategy,
  updateStrategy,
  validateTicker,
} from "../api/client";
import type {
  ConditionGroupInput,
  ConditionInput,
  IndicatorInput,
  IndicatorType,
  StrategyCreate,
} from "../types";

const sourceOptions = ["open", "high", "low", "close", "volume"];
const operatorOptions = [
  "CROSSES_ABOVE",
  "CROSSES_BELOW",
  "IS_RISING",
  "IS_FALLING",
  "GT",
  "LT",
  "EQ",
  "GTE",
  "LTE",
] as const;

const indicatorParamConfig: Record<IndicatorType, Array<{ key: string; label: string; type: "number" | "select" }>> = {
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

const indicatorDefaults: Record<IndicatorType, Record<string, number | string>> = {
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

const steps = ["Indicators", "Entry Rules", "Exit Rules", "Backtest", "Review"];

const emptyGroup = (): ConditionGroupInput => ({
  logic: "AND",
  conditions: [],
});

const emptyCondition = (aliases: string[]): ConditionInput => ({
  left_operand_type: "INDICATOR",
  left_operand_value: aliases[0] || "close",
  operator: "GT",
  right_operand_type: "SCALAR",
  right_operand_value: "0",
  display_order: 0,
});

export default function StrategyBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tickerValid, setTickerValid] = useState<boolean | null>(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [indicators, setIndicators] = useState<IndicatorInput[]>([]);
  const [entry, setEntry] = useState<ConditionGroupInput>(emptyGroup());
  const [exit, setExit] = useState<ConditionGroupInput>(emptyGroup());

  // Expression mode (Simple vs Advanced)
  const [useExpressions, setUseExpressions] = useState(false);
  const [entryGroups, setEntryGroups] = useState<Record<string, ConditionGroupInput>>({});
  const [exitGroups, setExitGroups] = useState<Record<string, ConditionGroupInput>>({});
  const [entryExpression, setEntryExpression] = useState("");
  const [exitExpression, setExitExpression] = useState("");

  const [ticker, setTicker] = useState("AAPL");
  const [assetClass, setAssetClass] = useState<"STOCK" | "CRYPTO">("STOCK");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");
  const [initialCapital, setInitialCapital] = useState("10000");
  const [resolution, setResolution] = useState("1d");
  const [contributionEnabled, setContributionEnabled] = useState(false);
  const [contributionAmount, setContributionAmount] = useState("2000");
  const [contributionFrequency, setContributionFrequency] = useState<
    "daily" | "weekly" | "monthly" | "interval_days"
  >("monthly");
  const [intervalDays, setIntervalDays] = useState("30");
  const [includeStart, setIncludeStart] = useState(false);

  // Advanced backtest options
  const [positionSizeType, setPositionSizeType] = useState<"full_capital" | "percent_capital" | "fixed_amount" | "risk_based">("full_capital");
  const [positionSizeValue, setPositionSizeValue] = useState("100");
  const [stopLossPct, setStopLossPct] = useState("");
  const [takeProfitPct, setTakeProfitPct] = useState("");
  const [dynamicStopColumn, setDynamicStopColumn] = useState("");
  const [commissionPerTrade, setCommissionPerTrade] = useState("0");
  const [commissionPct, setCommissionPct] = useState("0");
  const [slippagePct, setSlippagePct] = useState("0");


  // Generate all indicator column names including multi-output indicators
  const indicatorAliases = useMemo(() => {
    const aliases: string[] = [];
    indicators.forEach((ind) => {
      const type = ind.indicator_type;
      const alias = ind.alias;

      // Add base alias
      aliases.push(alias);

      // Add sub-columns for multi-output indicators
      if (type === "MACD") {
        aliases.push(`${alias}_macd`, `${alias}_signal`, `${alias}_hist`);
      } else if (type === "BB") {
        aliases.push(`${alias}_upper`, `${alias}_mid`, `${alias}_lower`);
      } else if (type === "STOCH") {
        aliases.push(`${alias}_k`, `${alias}_d`);
      } else if (type === "ADX") {
        aliases.push(`${alias}_dmp`, `${alias}_dmn`);
      } else if (type === "ICHIMOKU") {
        aliases.push(`${alias}_tenkan`, `${alias}_kijun`, `${alias}_span_a`, `${alias}_span_b`, `${alias}_chikou`);
      }
    });
    return aliases;
  }, [indicators]);

  const resolutionOptions =
    assetClass === "CRYPTO"
      ? ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1mo"]
      : ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"];

  const isIntraday = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"].includes(resolution);
  const rangeDays = Math.max(
    0,
    (new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24)
  );

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getStrategy(id)
      .then((strategy) => {
        setName(strategy.name);
        setDescription(strategy.description || "");
        setIndicators(
          strategy.indicators.map((ind, idx) => ({
            indicator_type: ind.indicator_type as IndicatorType,
            alias: ind.alias,
            params: ind.params || {},
            display_order: ind.display_order ?? idx,
          }))
        );

        // Check if strategy uses expressions (advanced mode)
        const hasExpressions = !!(strategy.entry_expression || strategy.exit_expression);

        if (hasExpressions) {
          // Advanced mode: Load named groups and expressions
          setUseExpressions(true);

          // Parse entry groups
          const entryGroupsObj: Record<string, ConditionGroupInput> = {};
          strategy.condition_groups
            .filter((g) => g.group_type === "ENTRY" && g.group_name)
            .forEach((g) => {
              entryGroupsObj[g.group_name!] = {
                group_name: g.group_name,
                logic: g.logic as "AND" | "OR",
                conditions: g.conditions.map((c, index) => ({
                  left_operand_type: c.left_operand_type,
                  left_operand_value: c.left_operand_value,
                  operator: c.operator,
                  right_operand_type: c.right_operand_type,
                  right_operand_value: c.right_operand_value,
                  display_order: c.display_order ?? index,
                })),
              };
            });

          // Parse exit groups
          const exitGroupsObj: Record<string, ConditionGroupInput> = {};
          strategy.condition_groups
            .filter((g) => g.group_type === "EXIT" && g.group_name)
            .forEach((g) => {
              exitGroupsObj[g.group_name!] = {
                group_name: g.group_name,
                logic: g.logic as "AND" | "OR",
                conditions: g.conditions.map((c, index) => ({
                  left_operand_type: c.left_operand_type,
                  left_operand_value: c.left_operand_value,
                  operator: c.operator,
                  right_operand_type: c.right_operand_type,
                  right_operand_value: c.right_operand_value,
                  display_order: c.display_order ?? index,
                })),
              };
            });

          setEntryGroups(entryGroupsObj);
          setExitGroups(exitGroupsObj);
          setEntryExpression(strategy.entry_expression || "");
          setExitExpression(strategy.exit_expression || "");
        } else {
          // Simple mode: Load single entry/exit groups (legacy format)
          setUseExpressions(false);

          const entryGroup = strategy.condition_groups.find((g) => g.group_type === "ENTRY");
          const exitGroup = strategy.condition_groups.find((g) => g.group_type === "EXIT");

          setEntry(
            entryGroup
              ? {
                  logic: entryGroup.logic as "AND" | "OR",
                  conditions: entryGroup.conditions.map((c, index) => ({
                    left_operand_type: c.left_operand_type,
                    left_operand_value: c.left_operand_value,
                    operator: c.operator,
                    right_operand_type: c.right_operand_type,
                    right_operand_value: c.right_operand_value,
                    display_order: c.display_order ?? index,
                  })),
                }
              : emptyGroup()
          );

          setExit(
            exitGroup
              ? {
                  logic: exitGroup.logic as "AND" | "OR",
                  conditions: exitGroup.conditions.map((c, index) => ({
                    left_operand_type: c.left_operand_type,
                    left_operand_value: c.left_operand_value,
                    operator: c.operator,
                    right_operand_type: c.right_operand_type,
                    right_operand_value: c.right_operand_value,
                    display_order: c.display_order ?? index,
                  })),
                }
              : emptyGroup()
          );
        }

        setStep(0);
      })
      .catch((err) => setError(err.message || "Failed to load strategy"))
      .finally(() => setLoading(false));
  }, [id]);


  const addIndicator = () => {
    const type: IndicatorType = "RSI";
    const nextIndex = indicators.length + 1;
    const alias = `rsi_${nextIndex}`;
    setIndicators((prev) => [
      ...prev,
      {
        indicator_type: type,
        alias,
        params: { ...indicatorDefaults[type] },
        display_order: prev.length,
      },
    ]);
  };

  const updateIndicator = (idx: number, patch: Partial<IndicatorInput>) => {
    setIndicators((prev) =>
      prev.map((ind, index) => (index === idx ? { ...ind, ...patch } : ind))
    );
  };

  const removeIndicator = (idx: number) => {
    setIndicators((prev) => prev.filter((_, index) => index !== idx));
  };

  const addCondition = (target: "entry" | "exit") => {
    const group = target === "entry" ? entry : exit;
    const updated = {
      ...group,
      conditions: [
        ...group.conditions,
        { ...emptyCondition(indicatorAliases), display_order: group.conditions.length },
      ],
    };
    target === "entry" ? setEntry(updated) : setExit(updated);
  };

  const updateCondition = (
    target: "entry" | "exit",
    idx: number,
    patch: Partial<ConditionInput>
  ) => {
    const group = target === "entry" ? entry : exit;
    const updated = {
      ...group,
      conditions: group.conditions.map((c, index) =>
        index === idx ? { ...c, ...patch } : c
      ),
    };
    target === "entry" ? setEntry(updated) : setExit(updated);
  };

  const removeCondition = (target: "entry" | "exit", idx: number) => {
    const group = target === "entry" ? entry : exit;
    const updated = {
      ...group,
      conditions: group.conditions.filter((_, index) => index !== idx),
    };
    target === "entry" ? setEntry(updated) : setExit(updated);
  };

  // Named group management for expression mode
  const addNamedGroup = (target: "entry" | "exit", groupName: string) => {
    const groups = target === "entry" ? entryGroups : exitGroups;
    const setter = target === "entry" ? setEntryGroups : setExitGroups;

    if (groups[groupName]) {
      setError(`Group "${groupName}" already exists`);
      return;
    }

    setter({
      ...groups,
      [groupName]: emptyGroup(),
    });
  };

  const removeNamedGroup = (target: "entry" | "exit", groupName: string) => {
    const groups = target === "entry" ? entryGroups : exitGroups;
    const setter = target === "entry" ? setEntryGroups : setExitGroups;

    const updated = { ...groups };
    delete updated[groupName];
    setter(updated);
  };

  const addConditionToGroup = (target: "entry" | "exit", groupName: string) => {
    const groups = target === "entry" ? entryGroups : exitGroups;
    const setter = target === "entry" ? setEntryGroups : setExitGroups;

    const group = groups[groupName];
    if (!group) return;

    setter({
      ...groups,
      [groupName]: {
        ...group,
        conditions: [
          ...group.conditions,
          { ...emptyCondition(indicatorAliases), display_order: group.conditions.length },
        ],
      },
    });
  };

  const updateConditionInGroup = (
    target: "entry" | "exit",
    groupName: string,
    idx: number,
    patch: Partial<ConditionInput>
  ) => {
    const groups = target === "entry" ? entryGroups : exitGroups;
    const setter = target === "entry" ? setEntryGroups : setExitGroups;

    const group = groups[groupName];
    if (!group) return;

    setter({
      ...groups,
      [groupName]: {
        ...group,
        conditions: group.conditions.map((c, index) =>
          index === idx ? { ...c, ...patch } : c
        ),
      },
    });
  };

  const removeConditionFromGroup = (target: "entry" | "exit", groupName: string, idx: number) => {
    const groups = target === "entry" ? entryGroups : exitGroups;
    const setter = target === "entry" ? setEntryGroups : setExitGroups;

    const group = groups[groupName];
    if (!group) return;

    setter({
      ...groups,
      [groupName]: {
        ...group,
        conditions: group.conditions.filter((_, index) => index !== idx),
      },
    });
  };

  const updateGroupLogic = (target: "entry" | "exit", groupName: string, logic: "AND" | "OR") => {
    const groups = target === "entry" ? entryGroups : exitGroups;
    const setter = target === "entry" ? setEntryGroups : setExitGroups;

    const group = groups[groupName];
    if (!group) return;

    setter({
      ...groups,
      [groupName]: {
        ...group,
        logic,
      },
    });
  };

  const handleValidateTicker = async () => {
    try {
      const valid = await validateTicker(ticker, assetClass);
      setTickerValid(valid);
    } catch (err) {
      setTickerValid(false);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      // Validate advanced mode requirements
      if (useExpressions) {
        if (Object.keys(entryGroups).length === 0 && Object.keys(exitGroups).length === 0) {
          setError("Advanced mode requires at least one entry or exit group");
          setLoading(false);
          return;
        }
        if (Object.keys(entryGroups).length > 0 && !entryExpression.trim()) {
          setError("Entry expression is required when entry groups are defined");
          setLoading(false);
          return;
        }
        if (Object.keys(exitGroups).length > 0 && !exitExpression.trim()) {
          setError("Exit expression is required when exit groups are defined");
          setLoading(false);
          return;
        }
      }

      const payload: StrategyCreate = {
        name,
        description,
        indicators,
        // Use expression mode or legacy mode
        ...(useExpressions
          ? {
              entry_groups: entryGroups,
              exit_groups: exitGroups,
              entry_expression: entryExpression,
              exit_expression: exitExpression,
            }
          : {
              entry,
              exit,
            }),
      };
      const strategy = id ? await updateStrategy(id, payload) : await createStrategy(payload);

      const periodicContribution = contributionEnabled
        ? {
            amount: Number(contributionAmount),
            frequency: contributionFrequency,
            interval_days:
              contributionFrequency === "interval_days" ? Number(intervalDays) : undefined,
            include_start: includeStart,
          }
        : null;

      const backtest = await createBacktest({
        strategy_id: strategy.id,
        ticker,
        asset_class: assetClass,
        start_date: startDate,
        end_date: endDate,
        bar_resolution: resolution,
        initial_capital: Number(initialCapital),
        position_size_type: positionSizeType,
        position_size_value: Number(positionSizeValue),
        stop_loss_pct: stopLossPct ? Number(stopLossPct) : null,
        take_profit_pct: takeProfitPct ? Number(takeProfitPct) : null,
        dynamic_stop_column: dynamicStopColumn || null,
        commission_per_trade: Number(commissionPerTrade),
        commission_pct: Number(commissionPct),
        slippage_pct: Number(slippagePct),
        periodic_contribution: periodicContribution,
      });
      navigate(`/backtests/${backtest.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to submit");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container fade-in">
      <div className="card">
        <h1>{id ? "Edit Strategy" : "New Strategy"}</h1>
        <div className="stepper">
          {steps.map((label, idx) => (
            <div key={label} className={`step ${idx === step ? "active" : ""}`}>
              {label}
            </div>
          ))}
        </div>
      </div>

      {error && <div className="notice">{error}</div>}

      {step === 0 && (
        <div className="card">
          <h2>Indicators</h2>
          <div className="row">
            <div>
              <label>Strategy Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <label>Description</label>
              <input value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
          </div>

          <div style={{ marginTop: "16px" }}>
            {indicators.map((indicator, idx) => (
              <div key={`${indicator.alias}-${idx}`} className="card" style={{ marginBottom: "12px" }}>
                <div className="row">
                  <div>
                    <label>Type</label>
                    <select
                      value={indicator.indicator_type}
                      onChange={(e) => {
                        const type = e.target.value as IndicatorType;
                        updateIndicator(idx, {
                          indicator_type: type,
                          params: { ...indicatorDefaults[type] },
                          alias: `${type.toLowerCase()}_${idx + 1}`,
                        });
                      }}
                    >
                      {Object.keys(indicatorDefaults).map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label>Alias</label>
                    <input
                      value={indicator.alias}
                      onChange={(e) => updateIndicator(idx, { alias: e.target.value })}
                    />
                  </div>
                  <div>
                    <label>Order</label>
                    <input
                      type="number"
                      value={indicator.display_order}
                      onChange={(e) =>
                        updateIndicator(idx, { display_order: Number(e.target.value) })
                      }
                    />
                  </div>
                </div>

                <div className="row" style={{ marginTop: "12px" }}>
                  {indicatorParamConfig[indicator.indicator_type].map((field) => (
                    <div key={field.key}>
                      <label>{field.label}</label>
                      {field.type === "select" ? (
                        <select
                          value={(indicator.params[field.key] as string) || "close"}
                          onChange={(e) =>
                            updateIndicator(idx, {
                              params: { ...indicator.params, [field.key]: e.target.value },
                            })
                          }
                        >
                          {sourceOptions.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="number"
                          value={Number(indicator.params[field.key] ?? 0)}
                          onChange={(e) =>
                            updateIndicator(idx, {
                              params: { ...indicator.params, [field.key]: Number(e.target.value) },
                            })
                          }
                        />
                      )}
                    </div>
                  ))}
                </div>

                <button className="btn secondary" onClick={() => removeIndicator(idx)}>
                  Remove
                </button>
              </div>
            ))}
            <button className="btn" onClick={addIndicator}>
              Add Indicator
            </button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="card">
          <div className="row" style={{ alignItems: "center", marginBottom: "16px" }}>
            <h2 style={{ margin: 0 }}>Entry Rules</h2>
            <div style={{ marginLeft: "auto", display: "flex", gap: "8px", alignItems: "center" }}>
              <span style={{ fontSize: "0.9rem", color: "var(--muted)" }}>Mode:</span>
              <button
                className={`btn ${!useExpressions ? "" : "secondary"}`}
                style={{ padding: "4px 12px" }}
                onClick={() => setUseExpressions(false)}
              >
                Simple
              </button>
              <button
                className={`btn ${useExpressions ? "" : "secondary"}`}
                style={{ padding: "4px 12px" }}
                onClick={() => setUseExpressions(true)}
              >
                Advanced
              </button>
            </div>
          </div>

          {!useExpressions ? (
            <>
              {/* Simple Mode - Single Group */}
              <div className="row">
                <div>
                  <label>Logic</label>
                  <select
                    value={entry.logic}
                    onChange={(e) => setEntry({ ...entry, logic: e.target.value as "AND" | "OR" })}
                  >
                    <option value="AND">AND</option>
                    <option value="OR">OR</option>
                  </select>
                </div>
              </div>
              {entry.conditions.map((condition, idx) => (
                <div key={idx} className="card" style={{ marginTop: "12px" }}>
                  <div className="row">
                    <div>
                      <label>Left Type</label>
                      <select
                        value={condition.left_operand_type}
                        onChange={(e) =>
                          updateCondition("entry", idx, {
                            left_operand_type: e.target.value as any,
                          })
                        }
                      >
                        <option value="INDICATOR">INDICATOR</option>
                        <option value="OHLCV">OHLCV</option>
                        <option value="SCALAR">SCALAR</option>
                        <option value="LOOKBACK">LOOKBACK</option>
                      </select>
                    </div>
                    <div>
                      <label>Left Value</label>
                      {condition.left_operand_type === "SCALAR" || condition.left_operand_type === "LOOKBACK" ? (
                        <input
                          placeholder={condition.left_operand_type === "LOOKBACK" ? "e.g., adx:-3" : ""}
                          value={condition.left_operand_value}
                          onChange={(e) =>
                            updateCondition("entry", idx, { left_operand_value: e.target.value })
                          }
                        />
                      ) : (
                        <select
                          value={condition.left_operand_value}
                          onChange={(e) =>
                            updateCondition("entry", idx, { left_operand_value: e.target.value })
                          }
                        >
                          {(condition.left_operand_type === "INDICATOR"
                            ? indicatorAliases
                            : sourceOptions
                          ).map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                    <div>
                      <label>Operator</label>
                      <select
                        value={condition.operator}
                        onChange={(e) =>
                          updateCondition("entry", idx, { operator: e.target.value as any })
                        }
                      >
                        {operatorOptions.map((op) => (
                          <option key={op} value={op}>
                            {op}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label>Right Type</label>
                      <select
                        value={condition.right_operand_type}
                        onChange={(e) =>
                          updateCondition("entry", idx, {
                            right_operand_type: e.target.value as any,
                          })
                        }
                      >
                        <option value="INDICATOR">INDICATOR</option>
                        <option value="OHLCV">OHLCV</option>
                        <option value="SCALAR">SCALAR</option>
                        <option value="LOOKBACK">LOOKBACK</option>
                      </select>
                    </div>
                    <div>
                      <label>Right Value</label>
                      {condition.right_operand_type === "SCALAR" || condition.right_operand_type === "LOOKBACK" ? (
                        <input
                          placeholder={condition.right_operand_type === "LOOKBACK" ? "e.g., close:-10" : ""}
                          value={condition.right_operand_value}
                          onChange={(e) =>
                            updateCondition("entry", idx, { right_operand_value: e.target.value })
                          }
                        />
                      ) : (
                        <select
                          value={condition.right_operand_value}
                          onChange={(e) =>
                            updateCondition("entry", idx, { right_operand_value: e.target.value })
                          }
                        >
                          {(condition.right_operand_type === "INDICATOR"
                            ? indicatorAliases
                            : sourceOptions
                          ).map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  </div>
                  <button className="btn secondary" onClick={() => removeCondition("entry", idx)}>
                    Remove
                  </button>
                </div>
              ))}
              <button className="btn" onClick={() => addCondition("entry")}>
                Add Entry Condition
              </button>
            </>
          ) : (
            <>
              {/* Advanced Mode - Named Groups + Expression */}
              <div className="notice" style={{ marginBottom: "16px" }}>
                <strong>Advanced Mode:</strong> Create named condition groups and combine them with boolean expressions.
                <br />
                Operators: <code>&&</code> (AND), <code>||</code> (OR), <code>!</code> (NOT), <code>()</code> (grouping)
              </div>

              {/* Named Groups */}
              {Object.keys(entryGroups).length === 0 && (
                <div className="notice">No groups yet. Add a group below to get started.</div>
              )}

              {Object.entries(entryGroups).map(([groupName, group]) => (
                <div key={groupName} className="card" style={{ marginTop: "16px", background: "#f9f9f9" }}>
                  <div className="row" style={{ alignItems: "center", marginBottom: "8px" }}>
                    <h3 style={{ margin: 0 }}>Group: {groupName}</h3>
                    <button
                      className="btn secondary"
                      style={{ marginLeft: "auto", padding: "4px 12px" }}
                      onClick={() => removeNamedGroup("entry", groupName)}
                    >
                      Remove Group
                    </button>
                  </div>

                  <div className="row" style={{ marginBottom: "8px" }}>
                    <div>
                      <label>Logic</label>
                      <select
                        value={group.logic}
                        onChange={(e) => updateGroupLogic("entry", groupName, e.target.value as "AND" | "OR")}
                      >
                        <option value="AND">AND</option>
                        <option value="OR">OR</option>
                      </select>
                    </div>
                  </div>

                  {group.conditions.map((condition, idx) => (
                    <div key={idx} className="card" style={{ marginTop: "8px" }}>
                      <div className="row">
                        <div>
                          <label>Left Type</label>
                          <select
                            value={condition.left_operand_type}
                            onChange={(e) =>
                              updateConditionInGroup("entry", groupName, idx, {
                                left_operand_type: e.target.value as any,
                              })
                            }
                          >
                            <option value="INDICATOR">INDICATOR</option>
                            <option value="OHLCV">OHLCV</option>
                            <option value="SCALAR">SCALAR</option>
                            <option value="LOOKBACK">LOOKBACK</option>
                          </select>
                        </div>
                        <div>
                          <label>Left Value</label>
                          {condition.left_operand_type === "SCALAR" || condition.left_operand_type === "LOOKBACK" ? (
                            <input
                              placeholder={condition.left_operand_type === "LOOKBACK" ? "e.g., adx:-3" : ""}
                              value={condition.left_operand_value}
                              onChange={(e) =>
                                updateConditionInGroup("entry", groupName, idx, { left_operand_value: e.target.value })
                              }
                            />
                          ) : (
                            <select
                              value={condition.left_operand_value}
                              onChange={(e) =>
                                updateConditionInGroup("entry", groupName, idx, { left_operand_value: e.target.value })
                              }
                            >
                              {(condition.left_operand_type === "INDICATOR"
                                ? indicatorAliases
                                : sourceOptions
                              ).map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                            </select>
                          )}
                        </div>
                        <div>
                          <label>Operator</label>
                          <select
                            value={condition.operator}
                            onChange={(e) =>
                              updateConditionInGroup("entry", groupName, idx, { operator: e.target.value as any })
                            }
                          >
                            {operatorOptions.map((op) => (
                              <option key={op} value={op}>
                                {op}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label>Right Type</label>
                          <select
                            value={condition.right_operand_type}
                            onChange={(e) =>
                              updateConditionInGroup("entry", groupName, idx, {
                                right_operand_type: e.target.value as any,
                              })
                            }
                          >
                            <option value="INDICATOR">INDICATOR</option>
                            <option value="OHLCV">OHLCV</option>
                            <option value="SCALAR">SCALAR</option>
                            <option value="LOOKBACK">LOOKBACK</option>
                          </select>
                        </div>
                        <div>
                          <label>Right Value</label>
                          {condition.right_operand_type === "SCALAR" || condition.right_operand_type === "LOOKBACK" ? (
                            <input
                              placeholder={condition.right_operand_type === "LOOKBACK" ? "e.g., close:-10" : ""}
                              value={condition.right_operand_value}
                              onChange={(e) =>
                                updateConditionInGroup("entry", groupName, idx, { right_operand_value: e.target.value })
                              }
                            />
                          ) : (
                            <select
                              value={condition.right_operand_value}
                              onChange={(e) =>
                                updateConditionInGroup("entry", groupName, idx, { right_operand_value: e.target.value })
                              }
                            >
                              {(condition.right_operand_type === "INDICATOR"
                                ? indicatorAliases
                                : sourceOptions
                              ).map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                            </select>
                          )}
                        </div>
                      </div>
                      <button className="btn secondary" onClick={() => removeConditionFromGroup("entry", groupName, idx)}>
                        Remove
                      </button>
                    </div>
                  ))}

                  <button className="btn" onClick={() => addConditionToGroup("entry", groupName)}>
                    Add Condition to {groupName}
                  </button>
                </div>
              ))}

              {/* Add New Group */}
              <div className="row" style={{ marginTop: "16px", gap: "8px" }}>
                <input
                  placeholder="Group name (e.g., oversold, trending)"
                  id="newEntryGroupName"
                  style={{ flex: 1 }}
                />
                <button
                  className="btn"
                  onClick={() => {
                    const input = document.getElementById("newEntryGroupName") as HTMLInputElement;
                    const groupName = input.value.trim();
                    if (groupName) {
                      addNamedGroup("entry", groupName);
                      input.value = "";
                    }
                  }}
                >
                  Add Group
                </button>
              </div>

              {/* Expression Editor */}
              <div style={{ marginTop: "16px" }}>
                <label>Entry Expression</label>
                <input
                  value={entryExpression}
                  onChange={(e) => setEntryExpression(e.target.value)}
                  placeholder='e.g., (oversold && trending) || bullish_cross'
                  style={{ fontFamily: "monospace" }}
                />
                <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: "4px" }}>
                  Combine groups using: <code>&&</code> (AND), <code>||</code> (OR), <code>!</code> (NOT), <code>()</code>
                  <br />
                  Available groups: {Object.keys(entryGroups).length > 0 ? Object.keys(entryGroups).join(", ") : "none"}
                </p>
              </div>
            </>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="card">
          <div className="row" style={{ alignItems: "center", marginBottom: "16px" }}>
            <h2 style={{ margin: 0 }}>Exit Rules</h2>
            <div style={{ marginLeft: "auto", display: "flex", gap: "8px", alignItems: "center" }}>
              <span style={{ fontSize: "0.9rem", color: "var(--muted)" }}>Mode:</span>
              <button
                className={`btn ${!useExpressions ? "" : "secondary"}`}
                style={{ padding: "4px 12px" }}
                onClick={() => setUseExpressions(false)}
              >
                Simple
              </button>
              <button
                className={`btn ${useExpressions ? "" : "secondary"}`}
                style={{ padding: "4px 12px" }}
                onClick={() => setUseExpressions(true)}
              >
                Advanced
              </button>
            </div>
          </div>

          {!useExpressions ? (
            <>
              {/* Simple Mode - Single Group */}
              <div className="row">
                <div>
                  <label>Logic</label>
                  <select
                    value={exit.logic}
                    onChange={(e) => setExit({ ...exit, logic: e.target.value as "AND" | "OR" })}
                  >
                    <option value="AND">AND</option>
                    <option value="OR">OR</option>
                  </select>
                </div>
              </div>
              {exit.conditions.map((condition, idx) => (
                <div key={idx} className="card" style={{ marginTop: "12px" }}>
                  <div className="row">
                    <div>
                      <label>Left Type</label>
                      <select
                        value={condition.left_operand_type}
                        onChange={(e) =>
                          updateCondition("exit", idx, {
                            left_operand_type: e.target.value as any,
                          })
                        }
                      >
                        <option value="INDICATOR">INDICATOR</option>
                        <option value="OHLCV">OHLCV</option>
                        <option value="SCALAR">SCALAR</option>
                        <option value="LOOKBACK">LOOKBACK</option>
                      </select>
                    </div>
                    <div>
                      <label>Left Value</label>
                      {condition.left_operand_type === "SCALAR" || condition.left_operand_type === "LOOKBACK" ? (
                        <input
                          placeholder={condition.left_operand_type === "LOOKBACK" ? "e.g., adx:-3" : ""}
                          value={condition.left_operand_value}
                          onChange={(e) =>
                            updateCondition("exit", idx, { left_operand_value: e.target.value })
                          }
                        />
                      ) : (
                        <select
                          value={condition.left_operand_value}
                          onChange={(e) =>
                            updateCondition("exit", idx, { left_operand_value: e.target.value })
                          }
                        >
                          {(condition.left_operand_type === "INDICATOR"
                            ? indicatorAliases
                            : sourceOptions
                          ).map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                    <div>
                      <label>Operator</label>
                      <select
                        value={condition.operator}
                        onChange={(e) =>
                          updateCondition("exit", idx, { operator: e.target.value as any })
                        }
                      >
                        {operatorOptions.map((op) => (
                          <option key={op} value={op}>
                            {op}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label>Right Type</label>
                      <select
                        value={condition.right_operand_type}
                        onChange={(e) =>
                          updateCondition("exit", idx, {
                            right_operand_type: e.target.value as any,
                          })
                        }
                      >
                        <option value="INDICATOR">INDICATOR</option>
                        <option value="OHLCV">OHLCV</option>
                        <option value="SCALAR">SCALAR</option>
                        <option value="LOOKBACK">LOOKBACK</option>
                      </select>
                    </div>
                    <div>
                      <label>Right Value</label>
                      {condition.right_operand_type === "SCALAR" || condition.right_operand_type === "LOOKBACK" ? (
                        <input
                          placeholder={condition.right_operand_type === "LOOKBACK" ? "e.g., close:-10" : ""}
                          value={condition.right_operand_value}
                          onChange={(e) =>
                            updateCondition("exit", idx, { right_operand_value: e.target.value })
                          }
                        />
                      ) : (
                        <select
                          value={condition.right_operand_value}
                          onChange={(e) =>
                            updateCondition("exit", idx, { right_operand_value: e.target.value })
                          }
                        >
                          {(condition.right_operand_type === "INDICATOR"
                            ? indicatorAliases
                            : sourceOptions
                          ).map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  </div>
                  <button className="btn secondary" onClick={() => removeCondition("exit", idx)}>
                    Remove
                  </button>
                </div>
              ))}
              <button className="btn" onClick={() => addCondition("exit")}>
                Add Exit Condition
              </button>
            </>
          ) : (
            <>
              {/* Advanced Mode - Named Groups + Expression */}
              <div className="notice" style={{ marginBottom: "16px" }}>
                <strong>Advanced Mode:</strong> Create named condition groups and combine them with boolean expressions.
                <br />
                Operators: <code>&&</code> (AND), <code>||</code> (OR), <code>!</code> (NOT), <code>()</code> (grouping)
              </div>

              {/* Named Groups */}
              {Object.keys(exitGroups).length === 0 && (
                <div className="notice">No groups yet. Add a group below to get started.</div>
              )}

              {Object.entries(exitGroups).map(([groupName, group]) => (
                <div key={groupName} className="card" style={{ marginTop: "16px", background: "#f9f9f9" }}>
                  <div className="row" style={{ alignItems: "center", marginBottom: "8px" }}>
                    <h3 style={{ margin: 0 }}>Group: {groupName}</h3>
                    <button
                      className="btn secondary"
                      style={{ marginLeft: "auto", padding: "4px 12px" }}
                      onClick={() => removeNamedGroup("exit", groupName)}
                    >
                      Remove Group
                    </button>
                  </div>

                  <div className="row" style={{ marginBottom: "8px" }}>
                    <div>
                      <label>Logic</label>
                      <select
                        value={group.logic}
                        onChange={(e) => updateGroupLogic("exit", groupName, e.target.value as "AND" | "OR")}
                      >
                        <option value="AND">AND</option>
                        <option value="OR">OR</option>
                      </select>
                    </div>
                  </div>

                  {group.conditions.map((condition, idx) => (
                    <div key={idx} className="card" style={{ marginTop: "8px" }}>
                      <div className="row">
                        <div>
                          <label>Left Type</label>
                          <select
                            value={condition.left_operand_type}
                            onChange={(e) =>
                              updateConditionInGroup("exit", groupName, idx, {
                                left_operand_type: e.target.value as any,
                              })
                            }
                          >
                            <option value="INDICATOR">INDICATOR</option>
                            <option value="OHLCV">OHLCV</option>
                            <option value="SCALAR">SCALAR</option>
                            <option value="LOOKBACK">LOOKBACK</option>
                          </select>
                        </div>
                        <div>
                          <label>Left Value</label>
                          {condition.left_operand_type === "SCALAR" || condition.left_operand_type === "LOOKBACK" ? (
                            <input
                              placeholder={condition.left_operand_type === "LOOKBACK" ? "e.g., adx:-3" : ""}
                              value={condition.left_operand_value}
                              onChange={(e) =>
                                updateConditionInGroup("exit", groupName, idx, { left_operand_value: e.target.value })
                              }
                            />
                          ) : (
                            <select
                              value={condition.left_operand_value}
                              onChange={(e) =>
                                updateConditionInGroup("exit", groupName, idx, { left_operand_value: e.target.value })
                              }
                            >
                              {(condition.left_operand_type === "INDICATOR"
                                ? indicatorAliases
                                : sourceOptions
                              ).map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                            </select>
                          )}
                        </div>
                        <div>
                          <label>Operator</label>
                          <select
                            value={condition.operator}
                            onChange={(e) =>
                              updateConditionInGroup("exit", groupName, idx, { operator: e.target.value as any })
                            }
                          >
                            {operatorOptions.map((op) => (
                              <option key={op} value={op}>
                                {op}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label>Right Type</label>
                          <select
                            value={condition.right_operand_type}
                            onChange={(e) =>
                              updateConditionInGroup("exit", groupName, idx, {
                                right_operand_type: e.target.value as any,
                              })
                            }
                          >
                            <option value="INDICATOR">INDICATOR</option>
                            <option value="OHLCV">OHLCV</option>
                            <option value="SCALAR">SCALAR</option>
                            <option value="LOOKBACK">LOOKBACK</option>
                          </select>
                        </div>
                        <div>
                          <label>Right Value</label>
                          {condition.right_operand_type === "SCALAR" || condition.right_operand_type === "LOOKBACK" ? (
                            <input
                              placeholder={condition.right_operand_type === "LOOKBACK" ? "e.g., close:-10" : ""}
                              value={condition.right_operand_value}
                              onChange={(e) =>
                                updateConditionInGroup("exit", groupName, idx, { right_operand_value: e.target.value })
                              }
                            />
                          ) : (
                            <select
                              value={condition.right_operand_value}
                              onChange={(e) =>
                                updateConditionInGroup("exit", groupName, idx, { right_operand_value: e.target.value })
                              }
                            >
                              {(condition.right_operand_type === "INDICATOR"
                                ? indicatorAliases
                                : sourceOptions
                              ).map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                            </select>
                          )}
                        </div>
                      </div>
                      <button className="btn secondary" onClick={() => removeConditionFromGroup("exit", groupName, idx)}>
                        Remove
                      </button>
                    </div>
                  ))}

                  <button className="btn" onClick={() => addConditionToGroup("exit", groupName)}>
                    Add Condition to {groupName}
                  </button>
                </div>
              ))}

              {/* Add New Group */}
              <div className="row" style={{ marginTop: "16px", gap: "8px" }}>
                <input
                  placeholder="Group name (e.g., overbought, weak_trend)"
                  id="newExitGroupName"
                  style={{ flex: 1 }}
                />
                <button
                  className="btn"
                  onClick={() => {
                    const input = document.getElementById("newExitGroupName") as HTMLInputElement;
                    const groupName = input.value.trim();
                    if (groupName) {
                      addNamedGroup("exit", groupName);
                      input.value = "";
                    }
                  }}
                >
                  Add Group
                </button>
              </div>

              {/* Expression Editor */}
              <div style={{ marginTop: "16px" }}>
                <label>Exit Expression</label>
                <input
                  value={exitExpression}
                  onChange={(e) => setExitExpression(e.target.value)}
                  placeholder='e.g., overbought || (weak_trend && profit_target)'
                  style={{ fontFamily: "monospace" }}
                />
                <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: "4px" }}>
                  Combine groups using: <code>&&</code> (AND), <code>||</code> (OR), <code>!</code> (NOT), <code>()</code>
                  <br />
                  Available groups: {Object.keys(exitGroups).length > 0 ? Object.keys(exitGroups).join(", ") : "none"}
                </p>
              </div>
            </>
          )}
        </div>
      )}

      {step === 3 && (
        <div className="card">
          <h2>Backtest Config</h2>
          <div className="row">
            <div>
              <label>Ticker</label>
              <input value={ticker} onChange={(e) => setTicker(e.target.value)} />
            </div>
            <div>
              <label>Asset Class</label>
              <select
                value={assetClass}
                onChange={(e) => setAssetClass(e.target.value as "STOCK" | "CRYPTO")}
              >
                <option value="STOCK">STOCK</option>
                <option value="CRYPTO">CRYPTO</option>
              </select>
            </div>
            <div>
              <label>Initial Capital</label>
              <input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(e.target.value)}
              />
            </div>
          </div>
          <div className="row" style={{ marginTop: "12px" }}>
            <div>
              <label>Start Date</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div>
              <label>End Date</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
            <div>
              <label>Resolution</label>
              <select value={resolution} onChange={(e) => setResolution(e.target.value)}>
                {resolutionOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="card" style={{ marginTop: "16px" }}>
            <h4>Position Sizing & Risk Management</h4>
            <div className="row">
              <div>
                <label>Position Sizing Type</label>
                <select
                  value={positionSizeType}
                  onChange={(e) => setPositionSizeType(e.target.value as any)}
                >
                  <option value="full_capital">Full Capital</option>
                  <option value="percent_capital">Percent of Capital</option>
                  <option value="fixed_amount">Fixed Amount</option>
                  <option value="risk_based">Risk-Based</option>
                </select>
              </div>
              {positionSizeType !== "full_capital" && (
                <div>
                  <label>
                    {positionSizeType === "percent_capital" ? "Percentage (%)" : positionSizeType === "fixed_amount" ? "Fixed Amount ($)" : "Risk Percentage (%)"}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={positionSizeValue}
                    onChange={(e) => setPositionSizeValue(e.target.value)}
                    placeholder={positionSizeType === "percent_capital" ? "e.g., 50" : positionSizeType === "fixed_amount" ? "e.g., 10000" : "e.g., 1.0"}
                  />
                </div>
              )}
            </div>
            <div className="row" style={{ marginTop: "12px" }}>
              <div>
                <label>Stop Loss (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={stopLossPct}
                  onChange={(e) => setStopLossPct(e.target.value)}
                  placeholder="Optional, e.g., 5"
                />
              </div>
              <div>
                <label>Take Profit (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={takeProfitPct}
                  onChange={(e) => setTakeProfitPct(e.target.value)}
                  placeholder="Optional, e.g., 15"
                />
              </div>
              <div>
                <label>Dynamic Stop (Indicator-based)</label>
                <select
                  value={dynamicStopColumn}
                  onChange={(e) => setDynamicStopColumn(e.target.value)}
                >
                  <option value="">None</option>
                  {indicatorAliases.map((alias) => (
                    <option key={alias} value={alias}>
                      {alias}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="notice" style={{ marginTop: "12px", fontSize: "0.85rem" }}>
              <strong>Dynamic Stop:</strong> Select an indicator column to use as a trailing stop.
              Exit when price crosses below the indicator value (e.g., ATR-based stop, Kijun-sen).
              Takes priority over fixed percentage stops.
            </div>
          </div>

          <div className="card" style={{ marginTop: "16px" }}>
            <h4>Transaction Costs</h4>
            <div className="row">
              <div>
                <label>Commission per Trade ($)</label>
                <input
                  type="number"
                  step="0.01"
                  value={commissionPerTrade}
                  onChange={(e) => setCommissionPerTrade(e.target.value)}
                />
              </div>
              <div>
                <label>Commission (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={commissionPct}
                  onChange={(e) => setCommissionPct(e.target.value)}
                />
              </div>
              <div>
                <label>Slippage (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={slippagePct}
                  onChange={(e) => setSlippagePct(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="row" style={{ marginTop: "12px" }}>
            <button className="btn secondary" onClick={handleValidateTicker}>
              Validate Ticker
            </button>
            {tickerValid !== null && (
              <span className="tag">{tickerValid ? "Valid" : "Invalid"}</span>
            )}
          </div>
          <div className="card" style={{ marginTop: "16px" }}>
            <h4>Periodic Contribution</h4>
            <div className="row">
              <div>
                <label>Enable</label>
                <select
                  value={contributionEnabled ? "yes" : "no"}
                  onChange={(e) => setContributionEnabled(e.target.value === "yes")}
                >
                  <option value="no">No</option>
                  <option value="yes">Yes</option>
                </select>
              </div>
              <div>
                <label>Amount</label>
                <input
                  type="number"
                  value={contributionAmount}
                  onChange={(e) => setContributionAmount(e.target.value)}
                  disabled={!contributionEnabled}
                />
              </div>
              <div>
                <label>Frequency</label>
                <select
                  value={contributionFrequency}
                  onChange={(e) =>
                    setContributionFrequency(
                      e.target.value as "daily" | "weekly" | "monthly" | "interval_days"
                    )
                  }
                  disabled={!contributionEnabled}
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="interval_days">Every N Days</option>
                </select>
              </div>
            </div>
            {contributionFrequency === "interval_days" && (
              <div className="row" style={{ marginTop: "12px" }}>
                <div>
                  <label>Interval Days</label>
                  <input
                    type="number"
                    value={intervalDays}
                    onChange={(e) => setIntervalDays(e.target.value)}
                    disabled={!contributionEnabled}
                  />
                </div>
              </div>
            )}
            <div className="row" style={{ marginTop: "12px" }}>
              <div>
                <label>Include Start Period</label>
                <select
                  value={includeStart ? "yes" : "no"}
                  onChange={(e) => setIncludeStart(e.target.value === "yes")}
                  disabled={!contributionEnabled}
                >
                  <option value="no">No</option>
                  <option value="yes">Yes</option>
                </select>
              </div>
            </div>
          </div>
          {assetClass === "STOCK" && isIntraday && rangeDays > 60 && (
            <p className="notice" style={{ marginTop: "12px" }}>
              Yahoo intraday data is limited to the most recent 60 days. Reduce the date range.
            </p>
          )}
        </div>
      )}

      {step === 4 && (
        <div className="card">
          <h2>Review & Submit</h2>
          <div className="grid grid-2">
            <div>
              <h3>Strategy</h3>
              <p><strong>{name || "Untitled"}</strong></p>
              <p>{description || "No description"}</p>
              <p>Indicators: {indicators.length}</p>

              {!useExpressions ? (
                <>
                  <p>Mode: Simple (AND/OR)</p>
                  <p>Entry conditions: {entry.conditions.length}</p>
                  <p>Exit conditions: {exit.conditions.length}</p>
                </>
              ) : (
                <>
                  <p>Mode: Advanced (Expressions)</p>
                  <p>Entry groups: {Object.keys(entryGroups).length}</p>
                  <p>Entry expression: {entryExpression || "(none)"}</p>
                  <p>Exit groups: {Object.keys(exitGroups).length}</p>
                  <p>Exit expression: {exitExpression || "(none)"}</p>
                </>
              )}
            </div>
            <div>
              <h3>Backtest</h3>
              <p>{ticker} ({assetClass})</p>
              <p>{startDate} → {endDate}</p>
              <p>Initial: ${initialCapital}</p>
            </div>
          </div>
          <button className="btn" onClick={handleSubmit} disabled={loading}>
            {loading ? "Submitting..." : "Submit Backtest"}
          </button>
        </div>
      )}

      <div className="row">
        <button className="btn secondary" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
          Back
        </button>
        <button className="btn" disabled={step === steps.length - 1} onClick={() => setStep((s) => s + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}
