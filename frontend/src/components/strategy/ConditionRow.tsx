import { useState, useRef, useEffect } from "react";
import type { ConditionInput, OperandType, OperatorType } from "../../types";
import {
  operatorOptions,
  sourceOptions,
  operatorToEnglish,
  validateLookbackFormat,
  isUnaryOperator,
} from "./strategyUtils";

interface ConditionRowProps {
  condition: ConditionInput;
  indicatorAliases: string[];
  logic: "AND" | "OR";
  isFirst: boolean;
  onChange: (patch: Partial<ConditionInput>) => void;
  onRemove: () => void;
  onLogicChange?: (logic: "AND" | "OR") => void;
}

export default function ConditionRow({
  condition,
  indicatorAliases,
  logic,
  isFirst,
  onChange,
  onRemove,
  onLogicChange,
}: ConditionRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const rowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (rowRef.current && !rowRef.current.contains(event.target as Node)) {
        setIsEditing(false);
      }
    }
    if (isEditing) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isEditing]);

  const displayText = () => {
    const left = condition.left_operand_value;
    const op = operatorToEnglish(condition.operator);

    if (isUnaryOperator(condition.operator)) {
      return `${left} ${op}`;
    }

    const right = condition.right_operand_value;
    return `${left} ${op} ${right}`;
  };

  const allOptions = [...indicatorAliases, ...sourceOptions];

  const renderOperandSelect = (
    type: OperandType,
    value: string,
    onTypeChange: (t: OperandType) => void,
    onValueChange: (v: string) => void,
    _isRight = false
  ) => {
    return (
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <select
          value={type}
          onChange={(e) => onTypeChange(e.target.value as OperandType)}
          style={{ width: "120px" }}
        >
          <option value="INDICATOR">Indicator</option>
          <option value="OHLCV">OHLCV</option>
          <option value="SCALAR">Number</option>
          <option value="LOOKBACK">Lookback</option>
        </select>

        {type === "SCALAR" || type === "LOOKBACK" ? (
          <input
            placeholder={type === "LOOKBACK" ? "e.g., close:-10" : "e.g., 30"}
            value={value}
            onChange={(e) => onValueChange(e.target.value)}
            style={{
              width: "140px",
              ...(type === "LOOKBACK" && !validateLookbackFormat(value)
                ? { borderColor: "var(--danger)" }
                : {}),
            }}
          />
        ) : (
          <select
            value={value}
            onChange={(e) => onValueChange(e.target.value)}
            style={{ width: "140px" }}
          >
            {(type === "INDICATOR" ? allOptions : sourceOptions).map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        )}
      </div>
    );
  };

  if (!isEditing) {
    return (
      <div
        ref={rowRef}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "10px 14px",
          background: "#faf8f5",
          borderRadius: "10px",
          cursor: "pointer",
          border: "1px solid var(--line)",
        }}
        onClick={() => setIsEditing(true)}
      >
        {!isFirst && onLogicChange && (
          <button
            className="btn secondary"
            style={{
              padding: "4px 10px",
              fontSize: "0.75rem",
              minWidth: "50px",
            }}
            onClick={(e) => {
              e.stopPropagation();
              onLogicChange(logic === "AND" ? "OR" : "AND");
            }}
          >
            {logic}
          </button>
        )}

        <span style={{ flex: 1, fontFamily: "monospace", fontSize: "0.9rem" }}>
          {displayText()}
        </span>

        <button
          className="btn secondary"
          style={{ padding: "4px 10px", fontSize: "0.8rem" }}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
        >
          Remove
        </button>
      </div>
    );
  }

  return (
    <div
      ref={rowRef}
      style={{
        padding: "14px",
        background: "#fff",
        borderRadius: "10px",
        border: "2px solid var(--accent)",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
        {renderOperandSelect(
          condition.left_operand_type,
          condition.left_operand_value,
          (t) => onChange({ left_operand_type: t }),
          (v) => onChange({ left_operand_value: v })
        )}

        <select
          value={condition.operator}
          onChange={(e) => onChange({ operator: e.target.value as OperatorType })}
          style={{ width: "150px" }}
        >
          {operatorOptions.map((op) => (
            <option key={op} value={op}>
              {op.replace(/_/g, " ")}
            </option>
          ))}
        </select>

        {!isUnaryOperator(condition.operator) &&
          renderOperandSelect(
            condition.right_operand_type,
            condition.right_operand_value,
            (t) => onChange({ right_operand_type: t }),
            (v) => onChange({ right_operand_value: v }),
            true
          )}
      </div>

      <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
        <button
          className="btn secondary"
          style={{ padding: "6px 12px" }}
          onClick={onRemove}
        >
          Remove
        </button>
        <button
          className="btn"
          style={{ padding: "6px 12px" }}
          onClick={() => setIsEditing(false)}
        >
          Done
        </button>
      </div>
    </div>
  );
}
