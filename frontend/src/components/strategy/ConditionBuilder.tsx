import { useStrategyBuilderStore } from "../../store/strategyBuilderStore";
import { ConditionRow } from "./ConditionRow";

export function ConditionBuilder() {
  const entry = useStrategyBuilderStore((s) => s.entry);
  const exit = useStrategyBuilderStore((s) => s.exit);
  const setEntryLogic = useStrategyBuilderStore((s) => s.setEntryLogic);
  const setExitLogic = useStrategyBuilderStore((s) => s.setExitLogic);
  const addCondition = useStrategyBuilderStore((s) => s.addCondition);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Entry Conditions */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Entry Conditions</h3>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <label style={{ fontSize: "0.85rem", margin: 0 }}>Logic:</label>
            <select
              value={entry.logic}
              onChange={(e) => setEntryLogic(e.target.value as "AND" | "OR")}
              style={{ width: "auto", minWidth: 80 }}
            >
              <option value="AND">AND</option>
              <option value="OR">OR</option>
            </select>
          </div>
        </div>

        {entry.conditions.length === 0 && (
          <div className="notice" style={{ marginBottom: 12 }}>
            No entry conditions. Add conditions to define when to enter a trade.
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {entry.conditions.map((condition, idx) => (
            <ConditionRow key={idx} condition={condition} index={idx} target="entry" />
          ))}
        </div>

        <button className="btn" style={{ marginTop: 12 }} onClick={() => addCondition("entry")}>
          Add Entry Condition
        </button>
      </div>

      {/* Exit Conditions */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Exit Conditions</h3>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <label style={{ fontSize: "0.85rem", margin: 0 }}>Logic:</label>
            <select
              value={exit.logic}
              onChange={(e) => setExitLogic(e.target.value as "AND" | "OR")}
              style={{ width: "auto", minWidth: 80 }}
            >
              <option value="AND">AND</option>
              <option value="OR">OR</option>
            </select>
          </div>
        </div>

        {exit.conditions.length === 0 && (
          <div className="notice" style={{ marginBottom: 12 }}>
            No exit conditions. Add conditions to define when to exit a trade.
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {exit.conditions.map((condition, idx) => (
            <ConditionRow key={idx} condition={condition} index={idx} target="exit" />
          ))}
        </div>

        <button className="btn" style={{ marginTop: 12 }} onClick={() => addCondition("exit")}>
          Add Exit Condition
        </button>
      </div>
    </div>
  );
}
