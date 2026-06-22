import { useState } from "react";
import { getIndicatorConfig, getIndicatorOutputs, getIndicatorConfigsArray } from "../../lib/constants";
import { useStrategyBuilderStore } from "../../store/strategyBuilderStore";
import type { IndicatorInput } from "../../types";

interface IndicatorCardProps {
  indicator: IndicatorInput;
  index: number;
}

export function IndicatorCard({ indicator, index }: IndicatorCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const updateIndicator = useStrategyBuilderStore((s) => s.updateIndicator);
  const removeIndicator = useStrategyBuilderStore((s) => s.removeIndicator);
  const selectIndicator = useStrategyBuilderStore((s) => s.selectIndicator);
  const selectedIndex = useStrategyBuilderStore((s) => s.selectedIndicatorIndex);

  const config = getIndicatorConfig(indicator.indicator_type);
  const outputs = getIndicatorOutputs(indicator.indicator_type, indicator.alias);
  const isSelected = selectedIndex === index;

  const handleParamChange = (key: string, value: string | number) => {
    updateIndicator(index, {
      params: { ...indicator.params, [key]: value },
    });
  };

  const handleAliasChange = (alias: string) => {
    updateIndicator(index, { alias });
  };

  const handleTypeChange = (type: string) => {
    const newConfig = getIndicatorConfig(type);
    const newParams: Record<string, number | string> = {};
    newConfig?.params.forEach((p: { key: string; default: number | string }) => {
      newParams[p.key] = p.default;
    });
    updateIndicator(index, {
      indicator_type: type,
      params: newParams,
      alias: `${type.toLowerCase()}_${index + 1}`,
    });
  };

  return (
    <div
      className="card"
      style={{
        padding: 16,
        border: isSelected ? "2px solid var(--accent)" : "1px solid var(--line)",
        cursor: "pointer",
      }}
      onClick={() => selectIndicator(isSelected ? null : index)}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div>
          <span style={{ fontWeight: 600, fontSize: "1rem" }}>{indicator.alias}</span>
          <span className="tag" style={{ marginLeft: 8 }}>
            {indicator.indicator_type}
          </span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn secondary"
            style={{ padding: "4px 10px", fontSize: "0.85rem" }}
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
          >
            {isEditing ? "Done" : "Edit"}
          </button>
          <button
            className="btn secondary"
            style={{ padding: "4px 10px", fontSize: "0.85rem", color: "var(--danger)" }}
            onClick={(e) => {
              e.stopPropagation();
              removeIndicator(index);
            }}
          >
            Remove
          </button>
        </div>
      </div>

      {/* Output columns info */}
      <p style={{ fontSize: "0.8rem", color: "var(--muted)", margin: "4px 0" }}>
        Outputs: {outputs.join(", ")}
      </p>

      {/* Editing panel */}
      {isEditing && config && (
        <div
          style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--line)" }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="row" style={{ marginBottom: 12 }}>
            <div>
              <label>Type</label>
              <select
                value={indicator.indicator_type}
                onChange={(e) => handleTypeChange(e.target.value)}
              >
                {getIndicatorConfigsArray().map((cfg) => (
                  <option key={cfg.type} value={cfg.type}>
                    {cfg.type}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Alias</label>
              <input value={indicator.alias} onChange={(e) => handleAliasChange(e.target.value)} />
            </div>
          </div>

          {config && config.params.length > 0 && (
            <div className="row">
              {[...config.params].map((param) => (
                <div key={param.key}>
                  <label>{param.label}</label>
                  {param.type === "select" ? (
                    <select
                      value={(indicator.params[param.key] as string) || String(param.default)}
                      onChange={(e) => handleParamChange(param.key, e.target.value)}
                    >
                      {param.options?.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="number"
                      value={Number(indicator.params[param.key] ?? param.default)}
                      onChange={(e) => handleParamChange(param.key, Number(e.target.value))}
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          {(!config || config.params.length === 0) && (
            <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>No configurable parameters</p>
          )}
        </div>
      )}
    </div>
  );
}
