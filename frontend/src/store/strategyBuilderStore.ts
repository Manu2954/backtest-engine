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

// Target types for conditions - includes short entry/exit
export type ConditionTarget = 'entry' | 'exit' | 'shortEntry' | 'shortExit';

export interface StrategyState {
  // Strategy metadata
  name: string;
  description: string;
  chartType: string;

  // Indicators
  indicators: IndicatorInput[];

  // Condition groups - named groups mode
  entryGroups: Record<string, ConditionGroupInput>;
  exitGroups: Record<string, ConditionGroupInput>;
  shortEntryGroups: Record<string, ConditionGroupInput>;
  shortExitGroups: Record<string, ConditionGroupInput>;

  // Boolean expressions for combining named groups
  entryExpression: string;
  exitExpression: string;
  shortEntryExpression: string;
  shortExitExpression: string;

  // Legacy single group mode (for backward compatibility)
  entry: ConditionGroupInput;
  exit: ConditionGroupInput;
  shortEntry: ConditionGroupInput;
  shortExit: ConditionGroupInput;

  // History for undo/redo
  history: StrategySnapshot[];
  historyIndex: number;

  // UI state - Visual Builder
  selectedBlockId: string | null;
  selectedBlockType: BlockType;
  selectedIndicatorIndex: number | null; // Legacy support
  selectedGroupName: string | null; // For group selection
  selectedGroupTarget: ConditionTarget | null; // Track which target the selected group belongs to
  isDirty: boolean;
}

interface StrategySnapshot {
  name: string;
  description: string;
  indicators: IndicatorInput[];
  entryGroups: Record<string, ConditionGroupInput>;
  exitGroups: Record<string, ConditionGroupInput>;
  shortEntryGroups: Record<string, ConditionGroupInput>;
  shortExitGroups: Record<string, ConditionGroupInput>;
  entryExpression: string;
  exitExpression: string;
  shortEntryExpression: string;
  shortExitExpression: string;
  entry: ConditionGroupInput;
  exit: ConditionGroupInput;
  shortEntry: ConditionGroupInput;
  shortExit: ConditionGroupInput;
}

interface StrategyActions {
  // Metadata
  setName: (name: string) => void;
  setDescription: (description: string) => void;
  setChartType: (chartType: string) => void;

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
  selectGroup: (target: ConditionTarget, groupName: string | null) => void;
  getSelectedIndicator: () => IndicatorInput | null;
  getSelectedCondition: () => { condition: ConditionInput; target: ConditionTarget; groupName: string; index: number } | null;
  getSelectedGroup: () => { target: ConditionTarget; groupName: string; group: ConditionGroupInput } | null;

  // Named group actions
  createGroup: (target: ConditionTarget, name: string) => void;
  renameGroup: (target: ConditionTarget, oldName: string, newName: string) => void;
  deleteGroup: (target: ConditionTarget, name: string) => void;
  getGroups: (target: ConditionTarget) => Record<string, ConditionGroupInput>;
  setGroupLogic: (target: ConditionTarget, groupName: string, logic: "AND" | "OR") => void;

  // Boolean expression actions
  setExpression: (target: ConditionTarget, expression: string) => void;
  getExpression: (target: ConditionTarget) => string;

  // Condition group actions (legacy - single group mode)
  setConditionLogic: (target: ConditionTarget, logic: "AND" | "OR") => void;
  setEntryLogic: (logic: "AND" | "OR") => void;
  setExitLogic: (logic: "AND" | "OR") => void;
  setShortEntryLogic: (logic: "AND" | "OR") => void;
  setShortExitLogic: (logic: "AND" | "OR") => void;

  // Condition actions (updated to support group names)
  addCondition: (target: ConditionTarget, groupName?: string) => void;
  addConditionWithId: (target: ConditionTarget, groupName?: string) => string; // Returns the new ID
  removeCondition: (target: ConditionTarget, index: number, groupName?: string) => void;
  removeConditionById: (id: string) => void;
  updateCondition: (target: ConditionTarget, index: number, patch: Partial<ConditionInput>, groupName?: string) => void;
  updateConditionById: (id: string, patch: Partial<ConditionInput>) => void;

  // History actions
  undo: () => void;
  redo: () => void;
  saveToHistory: () => void;

  // Load/reset
  loadStrategy: (data: {
    name: string;
    description: string;
    chartType?: string;
    indicators: IndicatorInput[];
    entry?: ConditionGroupInput;
    exit?: ConditionGroupInput;
    shortEntry?: ConditionGroupInput;
    shortExit?: ConditionGroupInput;
    entryGroups?: Record<string, ConditionGroupInput>;
    exitGroups?: Record<string, ConditionGroupInput>;
    shortEntryGroups?: Record<string, ConditionGroupInput>;
    shortExitGroups?: Record<string, ConditionGroupInput>;
    entryExpression?: string;
    exitExpression?: string;
    shortEntryExpression?: string;
    shortExitExpression?: string;
  }) => void;
  reset: () => void;

  // Computed helpers
  getIndicatorAliases: () => string[];
  findIndicatorById: (id: string) => { indicator: IndicatorInput; index: number } | null;
  findConditionById: (id: string) => { condition: ConditionInput; target: ConditionTarget; groupName: string; index: number } | null;
  getConditionGroup: (target: ConditionTarget) => ConditionGroupInput;
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
  chartType: "ohlcv",
  indicators: [],
  entryGroups: {},
  exitGroups: {},
  shortEntryGroups: {},
  shortExitGroups: {},
  entryExpression: "",
  exitExpression: "",
  shortEntryExpression: "",
  shortExitExpression: "",
  entry: emptyConditionGroup(),
  exit: emptyConditionGroup(),
  shortEntry: emptyConditionGroup(),
  shortExit: emptyConditionGroup(),
  history: [],
  historyIndex: -1,
  selectedBlockId: null,
  selectedBlockType: null,
  selectedIndicatorIndex: null,
  selectedGroupName: null,
  selectedGroupTarget: null,
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

  setChartType: (chartType) => {
    set({ chartType, isDirty: true });
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
      selectedGroupName: null, // Clear group selection when selecting a block
      selectedGroupTarget: null,
    });
  },

  selectGroup: (target, groupName) => {
    set({
      selectedBlockId: null,
      selectedBlockType: 'group',
      selectedIndicatorIndex: null,
      selectedGroupName: groupName,
      selectedGroupTarget: groupName ? target : null,
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

    // Helper to search in groups
    const searchInGroups = (groups: Record<string, ConditionGroupInput>, target: ConditionTarget) => {
      for (const [groupName, group] of Object.entries(groups)) {
        const idx = group.conditions.findIndex((c) => c.id === state.selectedBlockId);
        if (idx !== -1) {
          return { condition: group.conditions[idx], target, groupName, index: idx };
        }
      }
      return null;
    };

    // Search in entry groups first, then legacy entry
    let result = searchInGroups(state.entryGroups, 'entry');
    if (result) return result;

    const entryIdx = state.entry.conditions.findIndex((c) => c.id === state.selectedBlockId);
    if (entryIdx !== -1) {
      return { condition: state.entry.conditions[entryIdx], target: 'entry' as const, groupName: 'main', index: entryIdx };
    }

    // Search in exit groups, then legacy exit
    result = searchInGroups(state.exitGroups, 'exit');
    if (result) return result;

    const exitIdx = state.exit.conditions.findIndex((c) => c.id === state.selectedBlockId);
    if (exitIdx !== -1) {
      return { condition: state.exit.conditions[exitIdx], target: 'exit' as const, groupName: 'main', index: exitIdx };
    }

    // Search in short entry groups, then legacy
    result = searchInGroups(state.shortEntryGroups, 'shortEntry');
    if (result) return result;

    const shortEntryIdx = state.shortEntry.conditions.findIndex((c) => c.id === state.selectedBlockId);
    if (shortEntryIdx !== -1) {
      return { condition: state.shortEntry.conditions[shortEntryIdx], target: 'shortEntry' as const, groupName: 'main', index: shortEntryIdx };
    }

    // Search in short exit groups, then legacy
    result = searchInGroups(state.shortExitGroups, 'shortExit');
    if (result) return result;

    const shortExitIdx = state.shortExit.conditions.findIndex((c) => c.id === state.selectedBlockId);
    if (shortExitIdx !== -1) {
      return { condition: state.shortExit.conditions[shortExitIdx], target: 'shortExit' as const, groupName: 'main', index: shortExitIdx };
    }

    return null;
  },

  getSelectedGroup: () => {
    const state = get();
    if (state.selectedBlockType !== 'group' || !state.selectedGroupName || !state.selectedGroupTarget) return null;

    const groupsKey = `${state.selectedGroupTarget}Groups` as 'entryGroups' | 'exitGroups' | 'shortEntryGroups' | 'shortExitGroups';
    const groups = state[groupsKey];
    const group = groups[state.selectedGroupName];

    if (!group) return null;

    return {
      target: state.selectedGroupTarget,
      groupName: state.selectedGroupName,
      group,
    };
  },

  setConditionLogic: (target, logic) => {
    get().saveToHistory();
    set((state) => ({ [target]: { ...state[target], logic }, isDirty: true }));
  },

  setEntryLogic: (logic) => {
    get().saveToHistory();
    set((state) => ({ entry: { ...state.entry, logic }, isDirty: true }));
  },

  setExitLogic: (logic) => {
    get().saveToHistory();
    set((state) => ({ exit: { ...state.exit, logic }, isDirty: true }));
  },

  setShortEntryLogic: (logic) => {
    get().saveToHistory();
    set((state) => ({ shortEntry: { ...state.shortEntry, logic }, isDirty: true }));
  },

  setShortExitLogic: (logic) => {
    get().saveToHistory();
    set((state) => ({ shortExit: { ...state.shortExit, logic }, isDirty: true }));
  },

  // Named group actions
  createGroup: (target, name) => {
    const state = get();
    get().saveToHistory();

    const groupsKey = `${target}Groups` as 'entryGroups' | 'exitGroups' | 'shortEntryGroups' | 'shortExitGroups';
    const currentGroups = state[groupsKey];

    // Don't create if already exists
    if (currentGroups[name]) return;

    set({
      [groupsKey]: {
        ...currentGroups,
        [name]: emptyConditionGroup(),
      },
      isDirty: true,
    });

    // Auto-update expression if it's empty
    const expressionKey = `${target}Expression` as 'entryExpression' | 'exitExpression' | 'shortEntryExpression' | 'shortExitExpression';
    const currentExpression = state[expressionKey];
    if (!currentExpression) {
      const allGroupNames = [...Object.keys(currentGroups), name];
      set({
        [expressionKey]: allGroupNames.join(' OR '),
      });
    }
  },

  renameGroup: (target, oldName, newName) => {
    const state = get();
    get().saveToHistory();

    const groupsKey = `${target}Groups` as 'entryGroups' | 'exitGroups' | 'shortEntryGroups' | 'shortExitGroups';
    const currentGroups = state[groupsKey];

    // Don't rename if old doesn't exist or new already exists
    if (!currentGroups[oldName] || (currentGroups[newName] && oldName !== newName)) return;

    const newGroups = { ...currentGroups };
    newGroups[newName] = newGroups[oldName];
    delete newGroups[oldName];

    set({
      [groupsKey]: newGroups,
      selectedGroupName: state.selectedGroupName === oldName ? newName : state.selectedGroupName,
      isDirty: true,
    });

    // Update expression to replace old name with new name
    const expressionKey = `${target}Expression` as 'entryExpression' | 'exitExpression' | 'shortEntryExpression' | 'shortExitExpression';
    const currentExpression = state[expressionKey];
    if (currentExpression) {
      // Use word boundaries to only replace whole words
      const updatedExpression = currentExpression.replace(
        new RegExp(`\\b${oldName}\\b`, 'g'),
        newName
      );
      set({
        [expressionKey]: updatedExpression,
      });
    }
  },

  deleteGroup: (target, name) => {
    const state = get();
    get().saveToHistory();

    const groupsKey = `${target}Groups` as 'entryGroups' | 'exitGroups' | 'shortEntryGroups' | 'shortExitGroups';
    const currentGroups = state[groupsKey];

    const newGroups = { ...currentGroups };
    delete newGroups[name];

    set({
      [groupsKey]: newGroups,
      selectedGroupName: state.selectedGroupName === name ? null : state.selectedGroupName,
      selectedGroupTarget: state.selectedGroupName === name ? null : state.selectedGroupTarget,
      selectedBlockType: state.selectedGroupName === name ? null : state.selectedBlockType,
      isDirty: true,
    });

    // Update expression to remove references to deleted group
    const expressionKey = `${target}Expression` as 'entryExpression' | 'exitExpression' | 'shortEntryExpression' | 'shortExitExpression';
    const currentExpression = state[expressionKey];
    if (currentExpression) {
      // Remove the deleted group name from expression
      let updatedExpression = currentExpression.replace(
        new RegExp(`\\b${name}\\b`, 'g'),
        ''
      );
      // Clean up extra operators and whitespace
      updatedExpression = updatedExpression
        .replace(/\s+/g, ' ')
        .replace(/\(\s+/g, '(')
        .replace(/\s+\)/g, ')')
        .replace(/\b(AND|OR)\s+(AND|OR)\b/gi, '$1')
        .replace(/^\s*(AND|OR)\s+/i, '')
        .replace(/\s+(AND|OR)\s*$/i, '')
        .trim();

      // If expression is now empty and there are remaining groups, generate default
      if (!updatedExpression && Object.keys(newGroups).length > 0) {
        updatedExpression = Object.keys(newGroups).join(' OR ');
      }

      set({
        [expressionKey]: updatedExpression,
      });
    }
  },

  getGroups: (target) => {
    const state = get();
    const groupsKey = `${target}Groups` as 'entryGroups' | 'exitGroups' | 'shortEntryGroups' | 'shortExitGroups';
    return state[groupsKey];
  },

  setGroupLogic: (target, groupName, logic) => {
    const state = get();
    get().saveToHistory();

    const groupsKey = `${target}Groups` as 'entryGroups' | 'exitGroups' | 'shortEntryGroups' | 'shortExitGroups';
    const currentGroups = state[groupsKey];

    if (!currentGroups[groupName]) return;

    set({
      [groupsKey]: {
        ...currentGroups,
        [groupName]: {
          ...currentGroups[groupName],
          logic,
        },
      },
      isDirty: true,
    });
  },

  setExpression: (target, expression) => {
    get().saveToHistory();
    const expressionKey = `${target}Expression` as 'entryExpression' | 'exitExpression' | 'shortEntryExpression' | 'shortExitExpression';
    set({
      [expressionKey]: expression,
      isDirty: true,
    });
  },

  getExpression: (target) => {
    const state = get();
    const expressionKey = `${target}Expression` as 'entryExpression' | 'exitExpression' | 'shortEntryExpression' | 'shortExitExpression';
    return state[expressionKey];
  },

  addCondition: (target, groupName) => {
    const state = get();
    get().saveToHistory();

    // If groupName is provided, add to named group
    if (groupName) {
      const groupsKey = `${target}Groups` as 'entryGroups' | 'exitGroups' | 'shortEntryGroups' | 'shortExitGroups';
      const currentGroups = state[groupsKey];
      const group = currentGroups[groupName];

      if (!group) return;

      const newCondition: ConditionInput = {
        ...createEmptyCondition(),
        display_order: group.conditions.length,
      };

      set({
        [groupsKey]: {
          ...currentGroups,
          [groupName]: {
            ...group,
            conditions: [...group.conditions, newCondition],
          },
        },
        isDirty: true,
      });
    } else {
      // Legacy mode: add to single group
      const group = state[target];
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
    }
  },

  addConditionWithId: (target, groupName) => {
    const state = get();
    get().saveToHistory();

    const newCondition: ConditionInput = {
      ...createEmptyCondition(),
    };

    // If groupName is provided, add to named group
    if (groupName) {
      const groupsKey = `${target}Groups` as 'entryGroups' | 'exitGroups' | 'shortEntryGroups' | 'shortExitGroups';
      const currentGroups = state[groupsKey];
      const group = currentGroups[groupName];

      if (!group) return newCondition.id!;

      newCondition.display_order = group.conditions.length;

      set({
        [groupsKey]: {
          ...currentGroups,
          [groupName]: {
            ...group,
            conditions: [...group.conditions, newCondition],
          },
        },
        selectedBlockId: newCondition.id,
        selectedBlockType: 'condition',
        isDirty: true,
      });
    } else {
      // Legacy mode: add to single group
      const group = state[target];
      newCondition.display_order = group.conditions.length;

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
    }

    return newCondition.id!;
  },

  removeCondition: (target, index) => {
    const state = get();
    get().saveToHistory();
    const group = state[target];
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

    // Helper to remove from groups
    const removeFromGroups = (groups: Record<string, ConditionGroupInput>, groupsKey: string) => {
      for (const [groupName, group] of Object.entries(groups)) {
        if (group.conditions.some((c) => c.id === id)) {
          set({
            [groupsKey]: {
              ...groups,
              [groupName]: {
                ...group,
                conditions: group.conditions.filter((c) => c.id !== id),
              },
            },
            selectedBlockId: state.selectedBlockId === id ? null : state.selectedBlockId,
            selectedBlockType: state.selectedBlockId === id ? null : state.selectedBlockType,
            isDirty: true,
          });
          return true;
        }
      }
      return false;
    };

    // Try to remove from named groups first
    if (removeFromGroups(state.entryGroups, 'entryGroups')) return;
    if (removeFromGroups(state.exitGroups, 'exitGroups')) return;
    if (removeFromGroups(state.shortEntryGroups, 'shortEntryGroups')) return;
    if (removeFromGroups(state.shortExitGroups, 'shortExitGroups')) return;

    // Fallback to legacy single groups
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
      return;
    }

    if (state.shortEntry.conditions.some((c) => c.id === id)) {
      set({
        shortEntry: {
          ...state.shortEntry,
          conditions: state.shortEntry.conditions.filter((c) => c.id !== id),
        },
        selectedBlockId: state.selectedBlockId === id ? null : state.selectedBlockId,
        selectedBlockType: state.selectedBlockId === id ? null : state.selectedBlockType,
        isDirty: true,
      });
      return;
    }

    if (state.shortExit.conditions.some((c) => c.id === id)) {
      set({
        shortExit: {
          ...state.shortExit,
          conditions: state.shortExit.conditions.filter((c) => c.id !== id),
        },
        selectedBlockId: state.selectedBlockId === id ? null : state.selectedBlockId,
        selectedBlockType: state.selectedBlockId === id ? null : state.selectedBlockType,
        isDirty: true,
      });
    }
  },

  updateCondition: (target, index, patch) => {
    const state = get();
    const group = state[target];
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

    // Helper to update in groups
    const updateInGroups = (groups: Record<string, ConditionGroupInput>, groupsKey: string) => {
      for (const [groupName, group] of Object.entries(groups)) {
        const idx = group.conditions.findIndex((c) => c.id === id);
        if (idx !== -1) {
          set({
            [groupsKey]: {
              ...groups,
              [groupName]: {
                ...group,
                conditions: group.conditions.map((c, i) =>
                  i === idx ? { ...c, ...patch } : c
                ),
              },
            },
            isDirty: true,
          });
          return true;
        }
      }
      return false;
    };

    // Try named groups first
    if (updateInGroups(state.entryGroups, 'entryGroups')) return;
    if (updateInGroups(state.exitGroups, 'exitGroups')) return;
    if (updateInGroups(state.shortEntryGroups, 'shortEntryGroups')) return;
    if (updateInGroups(state.shortExitGroups, 'shortExitGroups')) return;

    // Fallback to legacy single groups
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
      return;
    }

    const shortEntryIdx = state.shortEntry.conditions.findIndex((c) => c.id === id);
    if (shortEntryIdx !== -1) {
      set({
        shortEntry: {
          ...state.shortEntry,
          conditions: state.shortEntry.conditions.map((c, i) =>
            i === shortEntryIdx ? { ...c, ...patch } : c
          ),
        },
        isDirty: true,
      });
      return;
    }

    const shortExitIdx = state.shortExit.conditions.findIndex((c) => c.id === id);
    if (shortExitIdx !== -1) {
      set({
        shortExit: {
          ...state.shortExit,
          conditions: state.shortExit.conditions.map((c, i) =>
            i === shortExitIdx ? { ...c, ...patch } : c
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
      entryGroups: JSON.parse(JSON.stringify(state.entryGroups)),
      exitGroups: JSON.parse(JSON.stringify(state.exitGroups)),
      shortEntryGroups: JSON.parse(JSON.stringify(state.shortEntryGroups)),
      shortExitGroups: JSON.parse(JSON.stringify(state.shortExitGroups)),
      entryExpression: state.entryExpression,
      exitExpression: state.exitExpression,
      shortEntryExpression: state.shortEntryExpression,
      shortExitExpression: state.shortExitExpression,
      entry: JSON.parse(JSON.stringify(state.entry)),
      exit: JSON.parse(JSON.stringify(state.exit)),
      shortEntry: JSON.parse(JSON.stringify(state.shortEntry)),
      shortExit: JSON.parse(JSON.stringify(state.shortExit)),
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
      entryGroups: JSON.parse(JSON.stringify(snapshot.entryGroups)),
      exitGroups: JSON.parse(JSON.stringify(snapshot.exitGroups)),
      shortEntryGroups: JSON.parse(JSON.stringify(snapshot.shortEntryGroups)),
      shortExitGroups: JSON.parse(JSON.stringify(snapshot.shortExitGroups)),
      entryExpression: snapshot.entryExpression,
      exitExpression: snapshot.exitExpression,
      shortEntryExpression: snapshot.shortEntryExpression,
      shortExitExpression: snapshot.shortExitExpression,
      entry: JSON.parse(JSON.stringify(snapshot.entry)),
      exit: JSON.parse(JSON.stringify(snapshot.exit)),
      shortEntry: JSON.parse(JSON.stringify(snapshot.shortEntry)),
      shortExit: JSON.parse(JSON.stringify(snapshot.shortExit)),
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
      entryGroups: JSON.parse(JSON.stringify(snapshot.entryGroups)),
      exitGroups: JSON.parse(JSON.stringify(snapshot.exitGroups)),
      shortEntryGroups: JSON.parse(JSON.stringify(snapshot.shortEntryGroups)),
      shortExitGroups: JSON.parse(JSON.stringify(snapshot.shortExitGroups)),
      entryExpression: snapshot.entryExpression,
      exitExpression: snapshot.exitExpression,
      shortEntryExpression: snapshot.shortEntryExpression,
      shortExitExpression: snapshot.shortExitExpression,
      entry: JSON.parse(JSON.stringify(snapshot.entry)),
      exit: JSON.parse(JSON.stringify(snapshot.exit)),
      shortEntry: JSON.parse(JSON.stringify(snapshot.shortEntry)),
      shortExit: JSON.parse(JSON.stringify(snapshot.shortExit)),
      historyIndex: state.historyIndex + 1,
    });
  },

  loadStrategy: (data) => {
    set({
      name: data.name,
      description: data.description,
      chartType: data.chartType || "ohlcv",
      indicators: JSON.parse(JSON.stringify(data.indicators)),
      entryGroups: data.entryGroups ? JSON.parse(JSON.stringify(data.entryGroups)) : {},
      exitGroups: data.exitGroups ? JSON.parse(JSON.stringify(data.exitGroups)) : {},
      shortEntryGroups: data.shortEntryGroups ? JSON.parse(JSON.stringify(data.shortEntryGroups)) : {},
      shortExitGroups: data.shortExitGroups ? JSON.parse(JSON.stringify(data.shortExitGroups)) : {},
      entryExpression: data.entryExpression || "",
      exitExpression: data.exitExpression || "",
      shortEntryExpression: data.shortEntryExpression || "",
      shortExitExpression: data.shortExitExpression || "",
      entry: data.entry ? JSON.parse(JSON.stringify(data.entry)) : emptyConditionGroup(),
      exit: data.exit ? JSON.parse(JSON.stringify(data.exit)) : emptyConditionGroup(),
      shortEntry: data.shortEntry ? JSON.parse(JSON.stringify(data.shortEntry)) : emptyConditionGroup(),
      shortExit: data.shortExit ? JSON.parse(JSON.stringify(data.shortExit)) : emptyConditionGroup(),
      history: [],
      historyIndex: -1,
      selectedIndicatorIndex: null,
      selectedBlockId: null,
      selectedBlockType: null,
      selectedGroupName: null,
      selectedGroupTarget: null,
      isDirty: false,
    });
  },

  reset: () => {
    set({
      ...initialState,
      chartType: "ohlcv",
      entryGroups: {},
      exitGroups: {},
      shortEntryGroups: {},
      shortExitGroups: {},
      entryExpression: "",
      exitExpression: "",
      shortEntryExpression: "",
      shortExitExpression: "",
      entry: emptyConditionGroup(),
      exit: emptyConditionGroup(),
      shortEntry: emptyConditionGroup(),
      shortExit: emptyConditionGroup(),
      history: [],
      historyIndex: -1,
      selectedGroupTarget: null,
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

    // Helper to search in groups
    const searchInGroups = (groups: Record<string, ConditionGroupInput>, target: ConditionTarget) => {
      for (const [groupName, group] of Object.entries(groups)) {
        const idx = group.conditions.findIndex((c) => c.id === id);
        if (idx !== -1) {
          return { condition: group.conditions[idx], target, groupName, index: idx };
        }
      }
      return null;
    };

    // Search in named groups first
    let result = searchInGroups(state.entryGroups, 'entry');
    if (result) return result;

    result = searchInGroups(state.exitGroups, 'exit');
    if (result) return result;

    result = searchInGroups(state.shortEntryGroups, 'shortEntry');
    if (result) return result;

    result = searchInGroups(state.shortExitGroups, 'shortExit');
    if (result) return result;

    // Fallback to legacy single groups
    const entryIdx = state.entry.conditions.findIndex((c) => c.id === id);
    if (entryIdx !== -1) {
      return { condition: state.entry.conditions[entryIdx], target: 'entry' as const, groupName: 'main', index: entryIdx };
    }

    const exitIdx = state.exit.conditions.findIndex((c) => c.id === id);
    if (exitIdx !== -1) {
      return { condition: state.exit.conditions[exitIdx], target: 'exit' as const, groupName: 'main', index: exitIdx };
    }

    const shortEntryIdx = state.shortEntry.conditions.findIndex((c) => c.id === id);
    if (shortEntryIdx !== -1) {
      return { condition: state.shortEntry.conditions[shortEntryIdx], target: 'shortEntry' as const, groupName: 'main', index: shortEntryIdx };
    }

    const shortExitIdx = state.shortExit.conditions.findIndex((c) => c.id === id);
    if (shortExitIdx !== -1) {
      return { condition: state.shortExit.conditions[shortExitIdx], target: 'shortExit' as const, groupName: 'main', index: shortExitIdx };
    }

    return null;
  },

  getConditionGroup: (target) => {
    const state = get();
    return state[target];
  },
}));
