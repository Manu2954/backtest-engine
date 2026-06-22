import { useState } from "react";
import type { IndicatorInput, IndicatorType } from "../../types";
import {
  indicatorParamConfig,
  indicatorDefaults,
  indicatorPresets,
  generateAlias,
  sourceOptions,
} from "./strategyUtils";

interface IndicatorSectionProps {
  indicators: IndicatorInput[];
  onAdd: (indicator: IndicatorInput) => void;
  onUpdate: (idx: number, patch: Partial<IndicatorInput>) => void;
  onRemove: (idx: number) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export default function IndicatorSection({
  indicators,
  onAdd,
  onUpdate,
  onRemove,
  collapsed = false,
  onToggleCollapse,
}: IndicatorSectionProps) {
  const [editingIdx, setEditingIdx] = useState<number | null>(null);

  const handleAddIndicator = () => {
    const type: IndicatorType = "RSI";
    const params = { ...indicatorDefaults[type] };
    const alias = generateAlias(type, params);
    const uniqueAlias = makeUniqueAlias(alias);
    onAdd({
      indicator_type: type,
      alias: uniqueAlias,
      params,
      display_order: indicators.length,
    });
    setEditingIdx(indicators.length);
  };

  const handleAddPreset = (preset: (typeof indicatorPresets)[number]) => {
    const alias = generateAlias(preset.type, preset.params);
    const uniqueAlias = makeUniqueAlias(alias);
    onAdd({
      indicator_type: preset.type,
      alias: uniqueAlias,
      params: { ...preset.params },
      display_order: indicators.length,
    });
  };

  const makeUniqueAlias = (base: string): string => {
    const existing = indicators.map((i) => i.alias);
    if (!existing.includes(base)) return base;
    let i = 2;
    while (existing.includes(`${base}_${i}`)) i++;
    return `${base}_${i}`;
  };

  const handleTypeChange = (idx: number, type: IndicatorType) => {
    const params = { ...indicatorDefaults[type] };
    const alias = generateAlias(type, params);
    const uniqueAlias = makeUniqueAlias(alias);
    onUpdate(idx, {
      indicator_type: type,
      params,
      alias: uniqueAlias,
    });
  };

  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          marginBottom: collapsed ? 0 : "16px",
        }}
        onClick={onToggleCollapse}
      >
        <h2 style={{ margin: 0 }}>
          Indicators
          <span
            style={{
              marginLeft: "12px",
              fontSize: "0.85rem",
              color: "var(--muted)",
              fontWeight: 400,
            }}
          >
            ({indicators.length})
          </span>
        </h2>
        <span style={{ fontSize: "1.2rem", color: "var(--muted)" }}>
          {collapsed ? "+" : "-"}
        </span>
      </div>

      {!collapsed && (
        <>
          {indicators.length === 0 ? (
            <div
              className="notice"
              style={{ marginBottom: "16px", textAlign: "center" }}
            >
              No indicators added yet. Add common presets or create a custom
              indicator.
            </div>
          ) : (
            <table className="table" style={{ marginBottom: "16px" }}>
              <thead>
                <tr>
                  <th style={{ width: "100px" }}>Type</th>
                  <th>Alias</th>
                  <th>Parameters</th>
                  <th style={{ width: "100px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {indicators.map((indicator, idx) => (
                  <tr
                    key={`${indicator.alias}-${idx}`}
                    style={{
                      background:
                        editingIdx === idx ? "var(--bg-2)" : "transparent",
                    }}
                  >
                    <td>
                      {editingIdx === idx ? (
                        <select
                          value={indicator.indicator_type}
                          onChange={(e) =>
                            handleTypeChange(idx, e.target.value as IndicatorType)
                          }
                          style={{ width: "90px" }}
                        >
                          {Object.keys(indicatorDefaults).map((type) => (
                            <option key={type} value={type}>
                              {type}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span
                          className="tag"
                          style={{ background: "var(--accent)", color: "white" }}
                        >
                          {indicator.indicator_type}
                        </span>
                      )}
                    </td>
                    <td>
                      {editingIdx === idx ? (
                        <input
                          value={indicator.alias}
                          onChange={(e) =>
                            onUpdate(idx, { alias: e.target.value })
                          }
                          style={{ width: "120px" }}
                        />
                      ) : (
                        <code>{indicator.alias}</code>
                      )}
                    </td>
                    <td>
                      {editingIdx === idx ? (
                        <div
                          style={{
                            display: "flex",
                            gap: "8px",
                            flexWrap: "wrap",
                          }}
                        >
                          {indicatorParamConfig[indicator.indicator_type].map(
                            (field) => (
                              <div
                                key={field.key}
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "4px",
                                }}
                              >
                                <label
                                  style={{
                                    fontSize: "0.8rem",
                                    margin: 0,
                                    color: "var(--muted)",
                                  }}
                                >
                                  {field.label}:
                                </label>
                                {field.type === "select" ? (
                                  <select
                                    value={
                                      (indicator.params[field.key] as string) ||
                                      "close"
                                    }
                                    onChange={(e) =>
                                      onUpdate(idx, {
                                        params: {
                                          ...indicator.params,
                                          [field.key]: e.target.value,
                                        },
                                      })
                                    }
                                    style={{ width: "80px" }}
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
                                    value={Number(
                                      indicator.params[field.key] ?? 0
                                    )}
                                    onChange={(e) =>
                                      onUpdate(idx, {
                                        params: {
                                          ...indicator.params,
                                          [field.key]: Number(e.target.value),
                                        },
                                      })
                                    }
                                    style={{ width: "60px" }}
                                  />
                                )}
                              </div>
                            )
                          )}
                        </div>
                      ) : (
                        <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                          {Object.entries(indicator.params)
                            .map(([k, v]) => `${k}=${v}`)
                            .join(", ")}
                        </span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "4px" }}>
                        {editingIdx === idx ? (
                          <button
                            className="btn"
                            style={{ padding: "4px 10px", fontSize: "0.8rem" }}
                            onClick={() => setEditingIdx(null)}
                          >
                            Done
                          </button>
                        ) : (
                          <button
                            className="btn secondary"
                            style={{ padding: "4px 10px", fontSize: "0.8rem" }}
                            onClick={() => setEditingIdx(idx)}
                          >
                            Edit
                          </button>
                        )}
                        <button
                          className="btn secondary"
                          style={{
                            padding: "4px 10px",
                            fontSize: "0.8rem",
                            color: "var(--danger)",
                          }}
                          onClick={() => {
                            onRemove(idx);
                            if (editingIdx === idx) setEditingIdx(null);
                          }}
                        >
                          X
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button className="btn" onClick={handleAddIndicator}>
              + Add Indicator
            </button>
            <div
              style={{
                display: "flex",
                gap: "6px",
                flexWrap: "wrap",
                marginLeft: "8px",
              }}
            >
              <span
                style={{
                  fontSize: "0.85rem",
                  color: "var(--muted)",
                  alignSelf: "center",
                }}
              >
                Presets:
              </span>
              {indicatorPresets.map((preset) => (
                <button
                  key={preset.label}
                  className="btn secondary"
                  style={{ padding: "4px 10px", fontSize: "0.8rem" }}
                  onClick={() => handleAddPreset(preset)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
