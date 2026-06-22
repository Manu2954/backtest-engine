import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  createStrategy,
  getStrategy,
  updateStrategy,
} from "../api/client";
import type {
  ConditionGroupInput,
  ConditionInput,
  IndicatorInput,
  IndicatorType,
  StrategyCreate,
} from "../types";
import IndicatorSection from "../components/strategy/IndicatorSection";
import StrategyPreview from "../components/strategy/StrategyPreview";
import ConditionRow from "../components/strategy/ConditionRow";
import { getIndicatorColumns } from "../components/strategy/strategyUtils";

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

export default function StrategyEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Strategy state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [indicators, setIndicators] = useState<IndicatorInput[]>([]);
  const [entry, setEntry] = useState<ConditionGroupInput>(emptyGroup());
  const [exit, setExit] = useState<ConditionGroupInput>(emptyGroup());

  // Expression mode
  const [useExpressions, setUseExpressions] = useState(false);
  const [entryGroups, setEntryGroups] = useState<Record<string, ConditionGroupInput>>({});
  const [exitGroups, setExitGroups] = useState<Record<string, ConditionGroupInput>>({});
  const [entryExpression, setEntryExpression] = useState("");
  const [exitExpression, setExitExpression] = useState("");

  // Collapsible sections
  const [indicatorsCollapsed, setIndicatorsCollapsed] = useState(false);
  const [entryCollapsed, setEntryCollapsed] = useState(false);
  const [exitCollapsed, setExitCollapsed] = useState(false);

  // Preview visibility on mobile
  const [showMobilePreview, setShowMobilePreview] = useState(false);

  // Generate all indicator column names
  const indicatorAliases = useMemo(() => {
    const aliases: string[] = [];
    indicators.forEach((ind) => {
      aliases.push(...getIndicatorColumns(ind.indicator_type, ind.alias));
    });
    return aliases;
  }, [indicators]);

  // Load strategy if editing
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

        const hasExpressions = !!(
          strategy.entry_expression || strategy.exit_expression
        );

        if (hasExpressions) {
          setUseExpressions(true);

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
          setUseExpressions(false);

          const entryGroup = strategy.condition_groups.find(
            (g) => g.group_type === "ENTRY"
          );
          const exitGroup = strategy.condition_groups.find(
            (g) => g.group_type === "EXIT"
          );

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
      })
      .catch((err) => setError(err.message || "Failed to load strategy"))
      .finally(() => setLoading(false));
  }, [id]);

  // Indicator handlers
  const addIndicator = (indicator: IndicatorInput) => {
    setIndicators((prev) => [...prev, indicator]);
  };

  const updateIndicator = (idx: number, patch: Partial<IndicatorInput>) => {
    setIndicators((prev) =>
      prev.map((ind, index) => (index === idx ? { ...ind, ...patch } : ind))
    );
  };

  const removeIndicator = (idx: number) => {
    setIndicators((prev) => prev.filter((_, index) => index !== idx));
  };

  // Condition handlers for simple mode
  const addCondition = (target: "entry" | "exit") => {
    const group = target === "entry" ? entry : exit;
    const updated = {
      ...group,
      conditions: [
        ...group.conditions,
        {
          ...emptyCondition(indicatorAliases),
          display_order: group.conditions.length,
        },
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

  // Named group handlers for expression mode
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
          {
            ...emptyCondition(indicatorAliases),
            display_order: group.conditions.length,
          },
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

  const removeConditionFromGroup = (
    target: "entry" | "exit",
    groupName: string,
    idx: number
  ) => {
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

  const updateGroupLogic = (
    target: "entry" | "exit",
    groupName: string,
    logic: "AND" | "OR"
  ) => {
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

  // Save handler
  const handleSave = async (isDraft = false) => {
    if (!name.trim()) {
      setError("Strategy name is required");
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      if (useExpressions) {
        if (
          Object.keys(entryGroups).length === 0 &&
          Object.keys(exitGroups).length === 0
        ) {
          setError("Advanced mode requires at least one entry or exit group");
          setIsSaving(false);
          return;
        }
        if (Object.keys(entryGroups).length > 0 && !entryExpression.trim()) {
          setError("Entry expression is required when entry groups are defined");
          setIsSaving(false);
          return;
        }
        if (Object.keys(exitGroups).length > 0 && !exitExpression.trim()) {
          setError("Exit expression is required when exit groups are defined");
          setIsSaving(false);
          return;
        }
      }

      const payload: StrategyCreate = {
        name,
        description,
        indicators,
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

      const strategy = id
        ? await updateStrategy(id, payload)
        : await createStrategy(payload);

      if (!isDraft) {
        navigate(`/strategies/${strategy.id}`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to save strategy");
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="container fade-in">
        <div className="card" style={{ textAlign: "center", padding: "48px" }}>
          <div className="spinner" style={{ margin: "0 auto" }} />
          <p style={{ marginTop: "16px", color: "var(--muted)" }}>
            Loading strategy...
          </p>
        </div>
      </div>
    );
  }

  const renderConditionsSection = (
    target: "entry" | "exit",
    collapsed: boolean,
    setCollapsed: (v: boolean) => void
  ) => {
    const group = target === "entry" ? entry : exit;
    const groups = target === "entry" ? entryGroups : exitGroups;
    const expression = target === "entry" ? entryExpression : exitExpression;
    const setExpression =
      target === "entry" ? setEntryExpression : setExitExpression;
    const label = target === "entry" ? "Entry Rules" : "Exit Rules";
    const conditionCount = useExpressions
      ? Object.values(groups).reduce((acc, g) => acc + g.conditions.length, 0)
      : group.conditions.length;

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
          onClick={() => setCollapsed(!collapsed)}
        >
          <h2 style={{ margin: 0 }}>
            {label}
            <span
              style={{
                marginLeft: "12px",
                fontSize: "0.85rem",
                color: "var(--muted)",
                fontWeight: 400,
              }}
            >
              ({conditionCount} conditions)
            </span>
          </h2>
          <span style={{ fontSize: "1.2rem", color: "var(--muted)" }}>
            {collapsed ? "+" : "-"}
          </span>
        </div>

        {!collapsed && (
          <>
            {/* Mode Toggle */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "16px",
              }}
            >
              <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                Mode:
              </span>
              <button
                className={`btn ${!useExpressions ? "" : "secondary"}`}
                style={{ padding: "4px 12px", fontSize: "0.85rem" }}
                onClick={() => setUseExpressions(false)}
              >
                Simple
              </button>
              <button
                className={`btn ${useExpressions ? "" : "secondary"}`}
                style={{ padding: "4px 12px", fontSize: "0.85rem" }}
                onClick={() => setUseExpressions(true)}
              >
                Advanced
              </button>
            </div>

            {!useExpressions ? (
              <>
                {/* Simple Mode */}
                {group.conditions.length === 0 ? (
                  <div
                    className="notice"
                    style={{ marginBottom: "16px", textAlign: "center" }}
                  >
                    No {target} conditions yet. Add a condition to define when
                    to {target === "entry" ? "enter" : "exit"} a trade.
                  </div>
                ) : (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                      marginBottom: "16px",
                    }}
                  >
                    {group.conditions.map((condition, idx) => (
                      <ConditionRow
                        key={idx}
                        condition={condition}
                        indicatorAliases={indicatorAliases}
                        logic={group.logic}
                        isFirst={idx === 0}
                        onChange={(patch) =>
                          updateCondition(target, idx, patch)
                        }
                        onRemove={() => removeCondition(target, idx)}
                        onLogicChange={(logic) => {
                          const setter =
                            target === "entry" ? setEntry : setExit;
                          setter({ ...group, logic });
                        }}
                      />
                    ))}
                  </div>
                )}
                <button className="btn" onClick={() => addCondition(target)}>
                  + Add Condition
                </button>
              </>
            ) : (
              <>
                {/* Advanced Mode */}
                <div className="notice" style={{ marginBottom: "16px" }}>
                  Create named condition groups and combine them with boolean
                  expressions.
                  <br />
                  <code>&&</code> (AND), <code>||</code> (OR), <code>!</code>{" "}
                  (NOT), <code>()</code> (grouping)
                </div>

                {Object.keys(groups).length === 0 && (
                  <div
                    className="notice"
                    style={{ marginBottom: "16px", textAlign: "center" }}
                  >
                    No groups yet. Add a group below to get started.
                  </div>
                )}

                {Object.entries(groups).map(([groupName, grp]) => (
                  <div
                    key={groupName}
                    style={{
                      marginBottom: "16px",
                      padding: "16px",
                      background: "#faf8f5",
                      borderRadius: "12px",
                      border: "1px solid var(--line)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "12px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <h4 style={{ margin: 0 }}>{groupName}</h4>
                        <select
                          value={grp.logic}
                          onChange={(e) =>
                            updateGroupLogic(
                              target,
                              groupName,
                              e.target.value as "AND" | "OR"
                            )
                          }
                          style={{ width: "80px" }}
                        >
                          <option value="AND">AND</option>
                          <option value="OR">OR</option>
                        </select>
                      </div>
                      <button
                        className="btn secondary"
                        style={{ padding: "4px 10px", fontSize: "0.8rem" }}
                        onClick={() => removeNamedGroup(target, groupName)}
                      >
                        Remove Group
                      </button>
                    </div>

                    {grp.conditions.length === 0 ? (
                      <div
                        style={{
                          color: "var(--muted)",
                          fontStyle: "italic",
                          marginBottom: "12px",
                        }}
                      >
                        No conditions in this group
                      </div>
                    ) : (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "8px",
                          marginBottom: "12px",
                        }}
                      >
                        {grp.conditions.map((condition, idx) => (
                          <ConditionRow
                            key={idx}
                            condition={condition}
                            indicatorAliases={indicatorAliases}
                            logic={grp.logic}
                            isFirst={idx === 0}
                            onChange={(patch) =>
                              updateConditionInGroup(target, groupName, idx, patch)
                            }
                            onRemove={() =>
                              removeConditionFromGroup(target, groupName, idx)
                            }
                            onLogicChange={(logic) =>
                              updateGroupLogic(target, groupName, logic)
                            }
                          />
                        ))}
                      </div>
                    )}

                    <button
                      className="btn secondary"
                      style={{ fontSize: "0.85rem" }}
                      onClick={() => addConditionToGroup(target, groupName)}
                    >
                      + Add Condition
                    </button>
                  </div>
                ))}

                {/* Add new group */}
                <div
                  style={{
                    display: "flex",
                    gap: "8px",
                    marginBottom: "16px",
                  }}
                >
                  <input
                    placeholder="Group name (e.g., oversold, trending)"
                    id={`new${target}GroupName`}
                    style={{ flex: 1 }}
                  />
                  <button
                    className="btn"
                    onClick={() => {
                      const input = document.getElementById(
                        `new${target}GroupName`
                      ) as HTMLInputElement;
                      const groupName = input.value.trim();
                      if (groupName) {
                        addNamedGroup(target, groupName);
                        input.value = "";
                      }
                    }}
                  >
                    Add Group
                  </button>
                </div>

                {/* Expression editor */}
                <div>
                  <label>
                    {target === "entry" ? "Entry" : "Exit"} Expression
                  </label>
                  <input
                    value={expression}
                    onChange={(e) => setExpression(e.target.value)}
                    placeholder={`e.g., (${Object.keys(groups)[0] || "group1"} && ${Object.keys(groups)[1] || "group2"}) || ${Object.keys(groups)[2] || "group3"}`}
                    style={{ fontFamily: "monospace" }}
                  />
                  <p
                    style={{
                      fontSize: "0.85rem",
                      color: "var(--muted)",
                      marginTop: "4px",
                    }}
                  >
                    Available groups:{" "}
                    {Object.keys(groups).length > 0
                      ? Object.keys(groups).join(", ")
                      : "none"}
                  </p>
                </div>
              </>
            )}
          </>
        )}
      </div>
    );
  };

  return (
    <div className="container fade-in">
      {/* Sticky Header */}
      <div
        className="card"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ flex: 1, minWidth: "200px" }}>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Strategy Name"
            style={{
              fontSize: "1.2rem",
              fontWeight: 600,
              border: "none",
              background: "transparent",
              width: "100%",
              padding: "4px 0",
            }}
          />
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optional)"
            style={{
              fontSize: "0.9rem",
              color: "var(--muted)",
              border: "none",
              background: "transparent",
              width: "100%",
              padding: "2px 0",
            }}
          />
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            className="btn secondary"
            onClick={() => navigate("/strategies")}
          >
            Cancel
          </button>
          <button
            className="btn secondary"
            onClick={() => handleSave(true)}
            disabled={isSaving}
          >
            Save Draft
          </button>
          <button
            className="btn"
            onClick={() => handleSave(false)}
            disabled={isSaving}
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      {error && <div className="notice">{error}</div>}

      {/* Mobile Preview Toggle */}
      <div className="mobile-preview-toggle">
        <button
          className="btn secondary"
          onClick={() => setShowMobilePreview(!showMobilePreview)}
          style={{ width: "100%" }}
        >
          {showMobilePreview ? "Hide Preview" : "Show Preview"}
        </button>
      </div>

      {/* Two Column Layout */}
      <div className="strategy-editor-layout">
        {/* Left Column - Editor */}
        <div className="strategy-editor-main">
          <IndicatorSection
            indicators={indicators}
            onAdd={addIndicator}
            onUpdate={updateIndicator}
            onRemove={removeIndicator}
            collapsed={indicatorsCollapsed}
            onToggleCollapse={() => setIndicatorsCollapsed(!indicatorsCollapsed)}
          />

          {renderConditionsSection("entry", entryCollapsed, setEntryCollapsed)}
          {renderConditionsSection("exit", exitCollapsed, setExitCollapsed)}
        </div>

        {/* Right Column - Preview */}
        <div
          className={`strategy-editor-preview ${showMobilePreview ? "show" : ""}`}
        >
          <StrategyPreview
            name={name}
            description={description}
            indicators={indicators}
            entry={entry}
            exit={exit}
            useExpressions={useExpressions}
            entryGroups={entryGroups}
            exitGroups={exitGroups}
            entryExpression={entryExpression}
            exitExpression={exitExpression}
          />
        </div>
      </div>

      {/* Footer */}
      <div
        className="card"
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "12px",
          marginTop: "auto",
        }}
      >
        <button
          className="btn secondary"
          onClick={() => navigate("/strategies")}
        >
          Cancel
        </button>
        <button
          className="btn secondary"
          onClick={() => handleSave(true)}
          disabled={isSaving}
        >
          Save Draft
        </button>
        <button
          className="btn"
          onClick={() => handleSave(false)}
          disabled={isSaving}
        >
          {isSaving ? "Saving..." : "Save Strategy"}
        </button>
      </div>
    </div>
  );
}
