import type {
  IndicatorInput,
  ConditionGroupInput,

} from "../../types";
import {
  conditionToEnglish,
} from "./strategyUtils";

interface StrategyPreviewProps {
  name: string;
  description: string;
  indicators: IndicatorInput[];
  entry: ConditionGroupInput;
  exit: ConditionGroupInput;
  useExpressions: boolean;
  entryGroups: Record<string, ConditionGroupInput>;
  exitGroups: Record<string, ConditionGroupInput>;
  entryExpression: string;
  exitExpression: string;
}

export default function StrategyPreview({
  name,
  description,
  indicators,
  entry,
  exit,
  useExpressions,
  entryGroups,
  exitGroups,
  entryExpression,
  exitExpression,
}: StrategyPreviewProps) {
  const hasName = name.trim().length > 0;
  const hasIndicators = indicators.length > 0;
  const hasEntryRules = useExpressions
    ? Object.keys(entryGroups).length > 0 && entryExpression.trim().length > 0
    : entry.conditions.length > 0;
  const hasExitRules = useExpressions
    ? Object.keys(exitGroups).length > 0 && exitExpression.trim().length > 0
    : exit.conditions.length > 0;

  const ValidationBadge = ({
    valid,
    label,
  }: {
    valid: boolean;
    label: string;
  }) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        fontSize: "0.85rem",
      }}
    >
      <span
        style={{
          width: "18px",
          height: "18px",
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: valid ? "#d4edda" : "#fff6e8",
          color: valid ? "#155724" : "#856404",
          fontSize: "0.75rem",
          fontWeight: 600,
        }}
      >
        {valid ? "Y" : "!"}
      </span>
      <span style={{ color: valid ? "var(--ink)" : "var(--muted)" }}>
        {label}
      </span>
    </div>
  );

  const renderConditionGroup = (
    group: ConditionGroupInput,
    label: string
  ) => {
    if (group.conditions.length === 0) {
      return (
        <div style={{ color: "var(--muted)", fontStyle: "italic" }}>
          No {label.toLowerCase()} rules defined
        </div>
      );
    }

    return (
      <div style={{ fontSize: "0.9rem" }}>
        {group.conditions.map((c, i) => (
          <div key={i} style={{ marginBottom: "4px" }}>
            {i > 0 && (
              <span
                style={{
                  color: "var(--accent)",
                  fontWeight: 600,
                  marginRight: "8px",
                }}
              >
                {group.logic}
              </span>
            )}
            <code style={{ background: "#f0ede8", padding: "2px 6px", borderRadius: "4px" }}>
              {conditionToEnglish(c)}
            </code>
          </div>
        ))}
      </div>
    );
  };

  const renderNamedGroups = (
    groups: Record<string, ConditionGroupInput>,
    expression: string
  ) => {
    if (Object.keys(groups).length === 0) {
      return (
        <div style={{ color: "var(--muted)", fontStyle: "italic" }}>
          No groups defined
        </div>
      );
    }

    return (
      <div style={{ fontSize: "0.9rem" }}>
        {Object.entries(groups).map(([groupName, group]) => (
          <div
            key={groupName}
            style={{
              marginBottom: "8px",
              padding: "8px",
              background: "#faf8f5",
              borderRadius: "6px",
            }}
          >
            <div
              style={{
                fontWeight: 600,
                color: "var(--accent)",
                marginBottom: "4px",
              }}
            >
              {groupName}:
            </div>
            {group.conditions.map((c, i) => (
              <div key={i} style={{ marginLeft: "12px" }}>
                {i > 0 && (
                  <span style={{ color: "var(--muted)", marginRight: "4px" }}>
                    {group.logic}
                  </span>
                )}
                <code
                  style={{
                    background: "#f0ede8",
                    padding: "2px 6px",
                    borderRadius: "4px",
                  }}
                >
                  {conditionToEnglish(c)}
                </code>
              </div>
            ))}
          </div>
        ))}
        {expression && (
          <div style={{ marginTop: "8px", fontFamily: "monospace" }}>
            <span style={{ color: "var(--muted)" }}>Expression: </span>
            <code
              style={{
                background: "#e8f4f0",
                padding: "2px 8px",
                borderRadius: "4px",
              }}
            >
              {expression}
            </code>
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      style={{
        position: "sticky",
        top: "24px",
        height: "fit-content",
        maxHeight: "calc(100vh - 180px)",
        overflow: "auto",
      }}
    >
      <div
        className="card"
        style={{
          background: "linear-gradient(135deg, #faf8f5 0%, #f0ede8 100%)",
        }}
      >
        <h3 style={{ margin: "0 0 16px 0" }}>Strategy Preview</h3>

        {/* Validation Status */}
        <div
          style={{
            display: "flex",
            gap: "16px",
            flexWrap: "wrap",
            marginBottom: "20px",
            padding: "12px",
            background: "#fff",
            borderRadius: "10px",
          }}
        >
          <ValidationBadge valid={hasName} label="Name" />
          <ValidationBadge valid={hasIndicators} label="Indicators" />
          <ValidationBadge valid={hasEntryRules} label="Entry Rules" />
          <ValidationBadge valid={hasExitRules} label="Exit Rules" />
        </div>

        {/* Strategy Name */}
        <div style={{ marginBottom: "16px" }}>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--muted)",
              marginBottom: "4px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Strategy Name
          </div>
          <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>
            {name || (
              <span style={{ color: "var(--muted)", fontStyle: "italic" }}>
                Untitled Strategy
              </span>
            )}
          </div>
          {description && (
            <div
              style={{
                fontSize: "0.9rem",
                color: "var(--muted)",
                marginTop: "4px",
              }}
            >
              {description}
            </div>
          )}
        </div>

        {/* Indicators */}
        <div style={{ marginBottom: "16px" }}>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--muted)",
              marginBottom: "8px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Indicators ({indicators.length})
          </div>
          {indicators.length === 0 ? (
            <div style={{ color: "var(--muted)", fontStyle: "italic" }}>
              No indicators added
            </div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              {indicators.map((ind, i) => (
                <span
                  key={i}
                  className="tag"
                  style={{ background: "#e8f4f0", color: "var(--accent)" }}
                  title={`${ind.indicator_type}: ${Object.entries(ind.params)
                    .map(([k, v]) => `${k}=${v}`)
                    .join(", ")}`}
                >
                  {ind.alias}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Entry Rules */}
        <div style={{ marginBottom: "16px" }}>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--muted)",
              marginBottom: "8px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Entry Rules
          </div>
          {useExpressions
            ? renderNamedGroups(entryGroups, entryExpression)
            : renderConditionGroup(entry, "entry")}
        </div>

        {/* Exit Rules */}
        <div>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--muted)",
              marginBottom: "8px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Exit Rules
          </div>
          {useExpressions
            ? renderNamedGroups(exitGroups, exitExpression)
            : renderConditionGroup(exit, "exit")}
        </div>
      </div>
    </div>
  );
}
