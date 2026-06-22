import { create } from "zustand";
import type {
  IndicatorInput,
  ConditionGroupInput,
  ConditionInput,
} from "../types";
import { getDefaultParams, getIndicatorOutputs } from "../lib/constants";

// Generate unique IDs
let idCounter = 0;
const generateId = () => `block_${Date.now()}_${++idCounter}`;

export type BlockType = 'indicator' | 'condition' | 'group' | null;

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

  // UI state - Visual Builder
  selectedBlockId: string | null;
  selectedBlockType: BlockType;
  selectedIndicatorIndex: number | null; // Legacy support
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
  addIndicatorWithId: (type: string) => string; // Returns the new ID
  removeIndicator: (index: number) => void;
  removeIndicatorById: (id: string) => void;
  updateIndicator: (index: number, patch: Partial<IndicatorInput>) => void;
  updateIndicatorById: (id: string, patch: Partial<IndicatorInput>) => void;
  selectIndicator: (index: number | null) => void;

  // Block selection (Visual Builder)
  selectBlock: (id: string | null, type: BlockType) => void;
  getSelectedIndicator: () => IndicatorInput | null;
  getSelectedCondition: () => { condition: ConditionInput; target: 'entry' | 'exit'; index: number } | null;

  // Condition group actions
  setEntryLogic: (logic: "AND" | "OR") => void;
  setExitLogic: (logic: "AND" | "OR") => void;

  // Condition actions
  addCondition: (target: "entry" | "exit") => void;
  addConditionWithId: (target: "entry" | "exit") => string; // Returns the new ID
  removeCondition: (target: "entry" | "exit", index: number) => void;
  removeConditionById: (id: string) => void;
  updateCondition: (target: "entry" | "exit", index: number, patch: Partial<ConditionInput>) => void;
  updateConditionById: (id: string, patch: Partial<ConditionInput>) => void;

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
  findIndicatorById: (id: string) => { indicator: IndicatorInput; index: number } | null;
  findConditionById: (id: string) => { condition: ConditionInput; target: 'entry' | 'exit'; index: number } | null;
}

const emptyConditionGroup = (): ConditionGroupInput => ({
  logic: "AND",
  conditions: [],
});

const createEmptyCondition = (): ConditionInput => ({
  id: generateId(),
  left_operand_type: "OHLCV",
  left_operand_value: "close",
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
  selectedBlockId: null,
  selectedBlockType: null,
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
    const id = generateId();
    const newIndicator: IndicatorInput = {
      id,
      indicator_type: type,
      alias,
      params: getDefaultParams(type),
      display_order: state.indicators.length,
    };
    get().saveToHistory();
    set({
      indicators: [...state.indicators, newIndicator],
      selectedIndicatorIndex: state.indicators.length,
      selectedBlockId: id,
      selectedBlockType: 'indicator',
      isDirty: true,
    });
  },

  addIndicatorWithId: (type) => {
    const state = get();
    const nextIndex = state.indicators.length + 1;
    const alias = `${type.toLowerCase()}_${nextIndex}`;
    const id = generateId();
    const newIndicator: IndicatorInput = {
      id,
      indicator_type: type,
      alias,
      params: getDefaultParams(type),
      display_order: state.indicators.length,
    };
    get().saveToHistory();
    set({
      indicators: [...state.indicators, newIndicator],
      selectedIndicatorIndex: state.indicators.length,
      selectedBlockId: id,
      selectedBlockType: 'indicator',
      isDirty: true,
    });
    return id;
  },

  removeIndicator: (index) => {
    const state = get();
    get().saveToHistory();
    set({
      indicators: state.indicators.filter((_, i) => i !== index),
      selectedIndicatorIndex: null,
      selectedBlockId: null,
      selectedBlockType: null,
      isDirty: true,
    });
  },

  removeIndicatorById: (id) => {
    const state = get();
    get().saveToHistory();
    set({
      indicators: state.indicators.filter((ind) => ind.id !== id),
      selectedIndicatorIndex: null,
      selectedBlockId: state.selectedBlockId === id ? null : state.selectedBlockId,
      selectedBlockType: state.selectedBlockId === id ? null : state.selectedBlockType,
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

  updateIndicatorById: (id, patch) => {
    const state = get();
    get().saveToHistory();
    set({
      indicators: state.indicators.map((ind) => (ind.id === id ? { ...ind, ...patch } : ind)),
      isDirty: true,
    });
  },

  selectIndicator: (index) => {
    const state = get();
    const indicator = index !== null ? state.indicators[index] : null;
    set({
      selectedIndicatorIndex: index,
      selectedBlockId: indicator?.id || null,
      selectedBlockType: indicator ? 'indicator' : null,
    });
  },

  selectBlock: (id, type) => {
    set({
      selectedBlockId: id,
      selectedBlockType: type,
      selectedIndicatorIndex: null, // Clear legacy selection
    });
  },

  getSelectedIndicator: () => {
    const state = get();
    if (state.selectedBlockType !== 'indicator' || !state.selectedBlockId) return null;
    return state.indicators.find((ind) => ind.id === state.selectedBlockId) || null;
  },

  getSelectedCondition: () => {
    const state = get();
    if (state.selectedBlockType !== 'condition' || !state.selectedBlockId) return null;

    // Search in entry conditions
    const entryIdx = state.entry.conditions.findIndex((c) => c.id === state.selectedBlockId);
    if (entryIdx !== -1) {
      return { condition: state.entry.conditions[entryIdx], target: 'entry' as const, index: entryIdx };
    }

    // Search in exit conditions
    const exitIdx = state.exit.conditions.findIndex((c) => c.id === state.selectedBlockId);
    if (exitIdx !== -1) {
      return { condition: state.exit.conditions[exitIdx], target: 'exit' as const, index: exitIdx };
    }

    return null;
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

  addConditionWithId: (target) => {
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
      selectedBlockId: newCondition.id,
      selectedBlockType: 'condition',
      isDirty: true,
    });
    return newCondition.id!;
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

  removeConditionById: (id) => {
    const state = get();
    get().saveToHistory();

    // Check entry conditions
    if (state.entry.conditions.some((c) => c.id === id)) {
      set({
        entry: {
          ...state.entry,
          conditions: state.entry.conditions.filter((c) => c.id !== id),
        },
        selectedBlockId: state.selectedBlockId === id ? null : state.selectedBlockId,
        selectedBlockType: state.selectedBlockId === id ? null : state.selectedBlockType,
        isDirty: true,
      });
      return;
    }

    // Check exit conditions
    if (state.exit.conditions.some((c) => c.id === id)) {
      set({
        exit: {
          ...state.exit,
          conditions: state.exit.conditions.filter((c) => c.id !== id),
        },
        selectedBlockId: state.selectedBlockId === id ? null : state.selectedBlockId,
        selectedBlockType: state.selectedBlockId === id ? null : state.selectedBlockType,
        isDirty: true,
      });
    }
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

  updateConditionById: (id, patch) => {
    const state = get();

    // Check entry conditions
    const entryIdx = state.entry.conditions.findIndex((c) => c.id === id);
    if (entryIdx !== -1) {
      set({
        entry: {
          ...state.entry,
          conditions: state.entry.conditions.map((c, i) =>
            i === entryIdx ? { ...c, ...patch } : c
          ),
        },
        isDirty: true,
      });
      return;
    }

    // Check exit conditions
    const exitIdx = state.exit.conditions.findIndex((c) => c.id === id);
    if (exitIdx !== -1) {
      set({
        exit: {
          ...state.exit,
          conditions: state.exit.conditions.map((c, i) =>
            i === exitIdx ? { ...c, ...patch } : c
          ),
        },
        isDirty: true,
      });
    }
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
    return state.indicators.flatMap((ind) =>
      getIndicatorOutputs(ind.indicator_type, ind.alias)
    );
  },

  findIndicatorById: (id) => {
    const state = get();
    const index = state.indicators.findIndex((ind) => ind.id === id);
    if (index === -1) return null;
    return { indicator: state.indicators[index], index };
  },

  findConditionById: (id) => {
    const state = get();

    const entryIdx = state.entry.conditions.findIndex((c) => c.id === id);
    if (entryIdx !== -1) {
      return { condition: state.entry.conditions[entryIdx], target: 'entry' as const, index: entryIdx };
    }

    const exitIdx = state.exit.conditions.findIndex((c) => c.id === id);
    if (exitIdx !== -1) {
      return { condition: state.exit.conditions[exitIdx], target: 'exit' as const, index: exitIdx };
    }

    return null;
  },
}));
