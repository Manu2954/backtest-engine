import { create } from 'zustand'

interface ComparisonState {
  selectedIds: string[]
  maxSelected: number
  addToComparison: (id: string) => void
  removeFromComparison: (id: string) => void
  clearComparison: () => void
  isSelected: (id: string) => boolean
  canAddMore: () => boolean
}

export const useComparisonStore = create<ComparisonState>((set, get) => ({
  selectedIds: [],
  maxSelected: 4,

  addToComparison: (id) => {
    const { selectedIds, maxSelected } = get()
    if (selectedIds.length < maxSelected && !selectedIds.includes(id)) {
      set({ selectedIds: [...selectedIds, id] })
    }
  },

  removeFromComparison: (id) => {
    set((state) => ({
      selectedIds: state.selectedIds.filter((i) => i !== id),
    }))
  },

  clearComparison: () => {
    set({ selectedIds: [] })
  },

  isSelected: (id) => {
    return get().selectedIds.includes(id)
  },

  canAddMore: () => {
    const { selectedIds, maxSelected } = get()
    return selectedIds.length < maxSelected
  },
}))
