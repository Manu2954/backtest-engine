import type { CSSProperties } from "react";

export type ViewMode = "card" | "table";

interface ViewToggleProps {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
}

const buttonStyle: CSSProperties = {
  border: "none",
  background: "transparent",
  padding: "8px 12px",
  borderRadius: "8px",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  transition: "background 0.2s",
};

const activeStyle: CSSProperties = {
  background: "var(--accent)",
  color: "white",
};

const inactiveStyle: CSSProperties = {
  background: "#f0ede8",
  color: "var(--muted)",
};

export default function ViewToggle({ value, onChange }: ViewToggleProps) {
  return (
    <div
      style={{
        display: "flex",
        gap: "4px",
        padding: "4px",
        borderRadius: "12px",
        background: "#f0ede8",
      }}
    >
      <button
        style={{ ...buttonStyle, ...(value === "card" ? activeStyle : inactiveStyle) }}
        onClick={() => onChange("card")}
        title="Card View"
        type="button"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
      </button>
      <button
        style={{ ...buttonStyle, ...(value === "table" ? activeStyle : inactiveStyle) }}
        onClick={() => onChange("table")}
        title="Table View"
        type="button"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
    </div>
  );
}
