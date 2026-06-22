import { OPERATORS, OPERAND_TYPES, OHLCV_COLUMNS, isUnaryOperator } from "../../lib/constants";
import { useStrategyBuilderStore } from "../../store/strategyBuilderStore";
import type { ConditionInput, OperandType, OperatorType } from "../../types";

interface ConditionRowProps {
  condition: ConditionInput;
  index: number;
  target: "entry" | "exit";
}

export function ConditionRow({ condition, index, target }: ConditionRowProps) {
  const updateCondition = useStrategyBuilderStore((s) => s.updateCondition);
  const removeCondition = useStrategyBuilderStore((s) => s.removeCondition);
  const indicatorAliases = useStrategyBuilderStore((s) => s.getIndicatorAliases());

  const isUnary = isUnaryOperator(condition.operator);

  const handleChange = (patch: Partial<ConditionInput>) => {
    updateCondition(target, index, patch);
  };

  const getValueOptions = (type: OperandType): string[] => {
    if (type === "INDICATOR") return indicatorAliases;
    if (type === "OHLCV") return [...OHLCV_COLUMNS];
    return [];
  };

  const renderOperandValue = (
    side: "left" | "right",
    type: OperandType,
    value: string
  ) => {
    const options = getValueOptions(type);
    const isInput = type === "SCALAR" || type === "LOOKBACK";

    if (isInput) {
      return (
        <input
          value={value}
          placeholder={type === "LOOKBACK" ? "column:-offset (e.g., close:-10)" : "Enter value"}
          onChange={(e) =>
            handleChange({
              [`${side}_operand_value`]: e.target.value,
            })
          }
          style={{ minWidth: 120 }}
        />
      );
    }

    return (
      <select
        value={value || options[0] || ""}
        onChange={(e) =>
          handleChange({
            [`${side}_operand_value`]: e.target.value,
          })
        }
        style={{ minWidth: 120 }}
      >
        {options.length === 0 && <option value="">-- No options --</option>}
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  };

  return (
    <div
      className="card"
      style={{
        padding: 12,
        display: "flex",
        alignItems: "flex-end",
        gap: 8,
        flexWrap: "wrap",
      }}
    >
      {/* Left operand type */}
      <div style={{ flex: "0 0 auto" }}>
        <label style={{ fontSize: "0.8rem" }}>Left Type</label>
        <select
          value={condition.left_operand_type}
          onChange={(e) => handleChange({ left_operand_type: e.target.value as OperandType })}
        >
          {OPERAND_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {/* Left operand value */}
      <div style={{ flex: 1, minWidth: 100 }}>
        <label style={{ fontSize: "0.8rem" }}>Left Value</label>
        {renderOperandValue("left", condition.left_operand_type, condition.left_operand_value)}
      </div>

      {/* Operator */}
      <div style={{ flex: "0 0 auto" }}>
        <label style={{ fontSize: "0.8rem" }}>Operator</label>
        <select
          value={condition.operator}
          onChange={(e) => handleChange({ operator: e.target.value as OperatorType })}
        >
          {OPERATORS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* Right operand (hidden for unary operators) */}
      {!isUnary && (
        <>
          <div style={{ flex: "0 0 auto" }}>
            <label style={{ fontSize: "0.8rem" }}>Right Type</label>
            <select
              value={condition.right_operand_type}
              onChange={(e) => handleChange({ right_operand_type: e.target.value as OperandType })}
            >
              {OPERAND_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ flex: 1, minWidth: 100 }}>
            <label style={{ fontSize: "0.8rem" }}>Right Value</label>
            {renderOperandValue("right", condition.right_operand_type, condition.right_operand_value)}
          </div>
        </>
      )}

      {/* Delete button */}
      <button
        className="btn secondary"
        style={{ padding: "8px 12px", color: "var(--danger)", alignSelf: "flex-end" }}
        onClick={() => removeCondition(target, index)}
      >
        Delete
      </button>
    </div>
  );
}
