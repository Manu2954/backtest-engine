import { create } from "zustand";
import type {
  IndicatorInput,
  ConditionGroupInput,
  ConditionInput,
} from "../types";
import { getDefaultParams } from "../lib/constants";

export interface StrategyState {
  // Strategy metadata
  name: string;
  description: string;

  // Indicators
  indicators: IndicatorInput[];

  // Condition groups (simple mode)
  entry: ConditionGroupInput;
  exit: ConditionGroupInput;

  // History for undo/redo
  history: StrategySnapshot[];
  historyIndex: number;

  // UI state
  selectedIndicatorIndex: number | null;
  isDirty: boolean;
}

interface StrategySnapshot {
  name: string;
  description: string;
  indicators: IndicatorInput[];
  entry: ConditionGroupInput;
  exit: ConditionGroupInput;
}

interface StrategyActions {
  // Metadata
  setName: (name: string) => void;
  setDescription: (description: string) => void;

  // Indicator actions
  addIndicator: (type: string) => void;
  removeIndicator: (index: number) => void;
  updateIndicator: (index: number, patch: Partial<IndicatorInput>) => void;
  selectIndicator: (index: number | null) => void;

  // Condition group actions
  setEntryLogic: (logic: "AND" | "OR") => void;
  setExitLogic: (logic: "AND" | "OR") => void;

  // Condition actions
  addCondition: (target: "entry" | "exit") => void;
  removeCondition: (target: "entry" | "exit", index: number) => void;
  updateCondition: (target: "entry" | "exit", index: number, patch: Partial<ConditionInput>) => void;

  // History actions
  undo: () => void;
  redo: () => void;
  saveToHistory: () => void;

  // Load/reset
  loadStrategy: (data: {
    name: string;
    description: string;
    indicators: IndicatorInput[];
    entry: ConditionGroupInput;
    exit: ConditionGroupInput;
  }) => void;
  reset: () => void;

  // Computed helpers
  getIndicatorAliases: () => string[];
}

const emptyConditionGroup = (): ConditionGroupInput => ({
  logic: "AND",
  conditions: [],
});

const createEmptyCondition = (): ConditionInput => ({
  left_operand_type: "INDICATOR",
  left_operand_value: "",
  operator: "GT",
  right_operand_type: "SCALAR",
  right_operand_value: "0",
  display_order: 0,
});

const initialState: StrategyState = {
  name: "",
  description: "",
  indicators: [],
  entry: emptyConditionGroup(),
  exit: emptyConditionGroup(),
  history: [],
  historyIndex: -1,
  selectedIndicatorIndex: null,
  isDirty: false,
};

export const useStrategyBuilderStore = create<StrategyState & StrategyActions>((set, get) => ({
  ...initialState,

  setName: (name) => {
    set({ name, isDirty: true });
  },

  setDescription: (description) => {
    set({ description, isDirty: true });
  },

  addIndicator: (type) => {
    const state = get();
    const nextIndex = state.indicators.length + 1;
    const alias = `${type.toLowerCase()}_${nextIndex}`;
    const newIndicator: IndicatorInput = {
      indicator_type: type,
      alias,
      params: getDefaultParams(type),
      display_order: state.indicators.length,
    };
    get().saveToHistory();
    set({
      indicators: [...state.indicators, newIndicator],
      selectedIndicatorIndex: state.indicators.length,
      isDirty: true,
    });
  },

  removeIndicator: (index) => {
    const state = get();
    get().saveToHistory();
    set({
      indicators: state.indicators.filter((_, i) => i !== index),
      selectedIndicatorIndex: null,
      isDirty: true,
    });
  },

  updateIndicator: (index, patch) => {
    const state = get();
    get().saveToHistory();
    set({
      indicators: state.indicators.map((ind, i) => (i === index ? { ...ind, ...patch } : ind)),
      isDirty: true,
    });
  },

  selectIndicator: (index) => {
    set({ selectedIndicatorIndex: index });
  },

  setEntryLogic: (logic) => {
    get().saveToHistory();
    set((state) => ({ entry: { ...state.entry, logic }, isDirty: true }));
  },

  setExitLogic: (logic) => {
    get().saveToHistory();
    set((state) => ({ exit: { ...state.exit, logic }, isDirty: true }));
  },

  addCondition: (target) => {
    const state = get();
    get().saveToHistory();
    const group = target === "entry" ? state.entry : state.exit;
    const newCondition: ConditionInput = {
      ...createEmptyCondition(),
      display_order: group.conditions.length,
    };
    const updated = {
      ...group,
      conditions: [...group.conditions, newCondition],
    };
    set({
      [target]: updated,
      isDirty: true,
    });
  },

  removeCondition: (target, index) => {
    const state = get();
    get().saveToHistory();
    const group = target === "entry" ? state.entry : state.exit;
    const updated = {
      ...group,
      conditions: group.conditions.filter((_, i) => i !== index),
    };
    set({
      [target]: updated,
      isDirty: true,
    });
  },

  updateCondition: (target, index, patch) => {
    const state = get();
    const group = target === "entry" ? state.entry : state.exit;
    const updated = {
      ...group,
      conditions: group.conditions.map((c, i) => (i === index ? { ...c, ...patch } : c)),
    };
    set({
      [target]: updated,
      isDirty: true,
    });
  },

  saveToHistory: () => {
    const state = get();
    const snapshot: StrategySnapshot = {
      name: state.name,
      description: state.description,
      indicators: JSON.parse(JSON.stringify(state.indicators)),
      entry: JSON.parse(JSON.stringify(state.entry)),
      exit: JSON.parse(JSON.stringify(state.exit)),
    };
    // Truncate future history if we're not at the end
    const newHistory = state.history.slice(0, state.historyIndex + 1);
    newHistory.push(snapshot);
    // Keep max 50 history items
    if (newHistory.length > 50) newHistory.shift();
    set({
      history: newHistory,
      historyIndex: newHistory.length - 1,
    });
  },

  undo: () => {
    const state = get();
    if (state.historyIndex < 0) return;
    const snapshot = state.history[state.historyIndex];
    if (!snapshot) return;
    set({
      name: snapshot.name,
      description: snapshot.description,
      indicators: JSON.parse(JSON.stringify(snapshot.indicators)),
      entry: JSON.parse(JSON.stringify(snapshot.entry)),
      exit: JSON.parse(JSON.stringify(snapshot.exit)),
      historyIndex: state.historyIndex - 1,
    });
  },

  redo: () => {
    const state = get();
    if (state.historyIndex >= state.history.length - 1) return;
    const snapshot = state.history[state.historyIndex + 1];
    if (!snapshot) return;
    set({
      name: snapshot.name,
      description: snapshot.description,
      indicators: JSON.parse(JSON.stringify(snapshot.indicators)),
      entry: JSON.parse(JSON.stringify(snapshot.entry)),
      exit: JSON.parse(JSON.stringify(snapshot.exit)),
      historyIndex: state.historyIndex + 1,
    });
  },

  loadStrategy: (data) => {
    set({
      name: data.name,
      description: data.description,
      indicators: JSON.parse(JSON.stringify(data.indicators)),
      entry: JSON.parse(JSON.stringify(data.entry)),
      exit: JSON.parse(JSON.stringify(data.exit)),
      history: [],
      historyIndex: -1,
      selectedIndicatorIndex: null,
      isDirty: false,
    });
  },

  reset: () => {
    set({
      ...initialState,
      history: [],
      historyIndex: -1,
    });
  },

  getIndicatorAliases: () => {
    const state = get();
    const aliases: string[] = [];
    state.indicators.forEach((ind) => {
      const type = ind.indicator_type;
      const alias = ind.alias;
      aliases.push(alias);
      // Add sub-columns for multi-output indicators
      if (type === "MACD") {
        aliases.push(`${alias}_macd`, `${alias}_signal`, `${alias}_hist`);
      } else if (type === "BB") {
        aliases.push(`${alias}_upper`, `${alias}_mid`, `${alias}_lower`);
      } else if (type === "STOCH") {
        aliases.push(`${alias}_k`, `${alias}_d`);
      } else if (type === "ADX") {
        aliases.push(`${alias}_adx`, `${alias}_dmp`, `${alias}_dmn`);
      } else if (type === "ICHIMOKU") {
        aliases.push(`${alias}_tenkan`, `${alias}_kijun`, `${alias}_span_a`, `${alias}_span_b`, `${alias}_chikou`);
      }
    });
    return aliases;
  },
}));
