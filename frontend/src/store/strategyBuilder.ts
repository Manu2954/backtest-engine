import { create } from "zustand";
import type { Indicator, ConditionGroup, Condition } from "@/types";

interface StrategyBuilderState {
  // Basic info
  name: string;
  description: string;

  // Current step (0-4)
  currentStep: number;

  // Indicators
  indicators: Indicator[];

  // Mode toggle
  useExpressions: boolean;

  // Simple mode - single group per type
  entryGroup: ConditionGroup;
  exitGroup: ConditionGroup;

  // Advanced mode - named groups with expressions
  entryGroups: Record<string, ConditionGroup>;
  exitGroups: Record<string, ConditionGroup>;
  entryExpression: string;
  exitExpression: string;

  // Backtest config
  backtestConfig: {
    ticker: string;
    assetClass: "STOCK" | "CRYPTO";
    startDate: string;
    endDate: string;
    barResolution: string;
    initialCapital: number;
    positionSizeType: string;
    positionSizeValue: number;
    stopLossPct: number | null;
    takeProfitPct: number | null;
    commissionPerTrade: number;
    commissionPct: number;
    slippagePct: number;
  };

  // Actions
  setName: (name: string) => void;
  setDescription: (description: string) => void;
  setCurrentStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;

  // Indicator actions
  addIndicator: () => void;
  updateIndicator: (index: number, indicator: Partial<Indicator>) => void;
  removeIndicator: (index: number) => void;

  // Mode toggle
  setUseExpressions: (use: boolean) => void;

  // Simple mode actions
  setEntryGroup: (group: ConditionGroup) => void;
  setExitGroup: (group: ConditionGroup) => void;
  addEntryCondition: () => void;
  addExitCondition: () => void;
  updateEntryCondition: (index: number, condition: Partial<Condition>) => void;
  updateExitCondition: (index: number, condition: Partial<Condition>) => void;
  removeEntryCondition: (index: number) => void;
  removeExitCondition: (index: number) => void;
  setEntryLogic: (logic: "AND" | "OR") => void;
  setExitLogic: (logic: "AND" | "OR") => void;

  // Backtest config actions
  updateBacktestConfig: (config: Partial<StrategyBuilderState["backtestConfig"]>) => void;

  // Reset
  reset: () => void;

  // Load existing strategy
  loadStrategy: (strategy: {
    name: string;
    description?: string;
    indicators: Indicator[];
    condition_groups: ConditionGroup[];
    entry_expression?: string;
    exit_expression?: string;
  }) => void;
}

const createEmptyCondition = (): Condition => ({
  left_operand_type: "INDICATOR",
  left_operand_value: "",
  operator: "GT",
  right_operand_type: "SCALAR",
  right_operand_value: "",
});

const createEmptyGroup = (): ConditionGroup => ({
  logic: "AND",
  conditions: [createEmptyCondition()],
});

const getDefaultBacktestConfig = () => ({
  ticker: "",
  assetClass: "STOCK" as const,
  startDate: "",
  endDate: "",
  barResolution: "1d",
  initialCapital: 10000,
  positionSizeType: "full_capital",
  positionSizeValue: 100,
  stopLossPct: null,
  takeProfitPct: null,
  commissionPerTrade: 0,
  commissionPct: 0,
  slippagePct: 0,
});

const initialState = {
  name: "",
  description: "",
  currentStep: 0,
  indicators: [],
  useExpressions: false,
  entryGroup: createEmptyGroup(),
  exitGroup: createEmptyGroup(),
  entryGroups: {},
  exitGroups: {},
  entryExpression: "",
  exitExpression: "",
  backtestConfig: getDefaultBacktestConfig(),
};

export const useStrategyBuilderStore = create<StrategyBuilderState>((set) => ({
  ...initialState,

  setName: (name) => set({ name }),
  setDescription: (description) => set({ description }),
  setCurrentStep: (currentStep) => set({ currentStep }),
  nextStep: () => set((state) => ({ currentStep: Math.min(state.currentStep + 1, 4) })),
  prevStep: () => set((state) => ({ currentStep: Math.max(state.currentStep - 1, 0) })),

  addIndicator: () => set((state) => ({
    indicators: [
      ...state.indicators,
      {
        indicator_type: "RSI",
        alias: `indicator_${state.indicators.length + 1}`,
        params: { period: 14, source: "close" },
      },
    ],
  })),

  updateIndicator: (index, indicator) => set((state) => ({
    indicators: state.indicators.map((ind, i) =>
      i === index ? { ...ind, ...indicator } : ind
    ),
  })),

  removeIndicator: (index) => set((state) => ({
    indicators: state.indicators.filter((_, i) => i !== index),
  })),

  setUseExpressions: (useExpressions) => set({ useExpressions }),

  setEntryGroup: (entryGroup) => set({ entryGroup }),
  setExitGroup: (exitGroup) => set({ exitGroup }),

  addEntryCondition: () => set((state) => ({
    entryGroup: {
      ...state.entryGroup,
      conditions: [...state.entryGroup.conditions, createEmptyCondition()],
    },
  })),

  addExitCondition: () => set((state) => ({
    exitGroup: {
      ...state.exitGroup,
      conditions: [...state.exitGroup.conditions, createEmptyCondition()],
    },
  })),

  updateEntryCondition: (index, condition) => set((state) => ({
    entryGroup: {
      ...state.entryGroup,
      conditions: state.entryGroup.conditions.map((c, i) =>
        i === index ? { ...c, ...condition } : c
      ),
    },
  })),

  updateExitCondition: (index, condition) => set((state) => ({
    exitGroup: {
      ...state.exitGroup,
      conditions: state.exitGroup.conditions.map((c, i) =>
        i === index ? { ...c, ...condition } : c
      ),
    },
  })),

  removeEntryCondition: (index) => set((state) => ({
    entryGroup: {
      ...state.entryGroup,
      conditions: state.entryGroup.conditions.filter((_, i) => i !== index),
    },
  })),

  removeExitCondition: (index) => set((state) => ({
    exitGroup: {
      ...state.exitGroup,
      conditions: state.exitGroup.conditions.filter((_, i) => i !== index),
    },
  })),

  setEntryLogic: (logic) => set((state) => ({
    entryGroup: { ...state.entryGroup, logic },
  })),

  setExitLogic: (logic) => set((state) => ({
    exitGroup: { ...state.exitGroup, logic },
  })),

  updateBacktestConfig: (config) => set((state) => ({
    backtestConfig: { ...state.backtestConfig, ...config },
  })),

  reset: () => set(initialState),

  loadStrategy: (strategy) => {
    const entryGroups = strategy.condition_groups.filter(g => g.group_type === "ENTRY");
    const exitGroups = strategy.condition_groups.filter(g => g.group_type === "EXIT");

    set({
      name: strategy.name,
      description: strategy.description || "",
      indicators: strategy.indicators,
      useExpressions: !!strategy.entry_expression,
      entryGroup: entryGroups[0] || createEmptyGroup(),
      exitGroup: exitGroups[0] || createEmptyGroup(),
      entryExpression: strategy.entry_expression || "",
      exitExpression: strategy.exit_expression || "",
    });
  },
}));
