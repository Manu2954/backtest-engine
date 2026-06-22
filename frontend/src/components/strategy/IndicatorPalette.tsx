import { useState, useMemo } from "react";
import { getIndicatorConfigsArray } from "../../lib/constants";
import { useStrategyBuilderStore } from "../../store/strategyBuilderStore";

export function IndicatorPalette() {
  const [search, setSearch] = useState("");
  const addIndicator = useStrategyBuilderStore((s) => s.addIndicator);

  const allConfigs = getIndicatorConfigsArray();

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return allConfigs;
    return allConfigs.filter(
      (c) =>
        c.type.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q)
    );
  }, [search, allConfigs]);

  const handleAdd = (type: string) => {
    addIndicator(type);
  };

  return (
    <div className="card">
      <h3>Indicator Palette</h3>
      <input
        type="text"
        placeholder="Search indicators..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ marginBottom: 12 }}
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 400, overflowY: "auto" }}>
        {filtered.length === 0 && (
          <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>No indicators found</p>
        )}
        {filtered.map((config) => (
          <div
            key={config.type}
            className="card"
            style={{
              padding: 12,
              cursor: "pointer",
              transition: "background 0.2s",
            }}
            onClick={() => handleAdd(config.type)}
            onMouseOver={(e) => (e.currentTarget.style.background = "var(--bg-2)")}
            onMouseOut={(e) => (e.currentTarget.style.background = "var(--card)")}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600 }}>{config.name}</span>
              <span className="tag">{config.type}</span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--muted)", margin: "6px 0 0 0" }}>
              {config.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
