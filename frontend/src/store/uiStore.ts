import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Theme = 'dark' | 'light' | 'system'
export type EffectiveTheme = 'dark' | 'light'

// Helper to get the effective theme based on system preference
export function getEffectiveTheme(theme: Theme): EffectiveTheme {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light'
  }
  return theme
}

// Apply theme to document
function applyTheme(theme: Theme) {
  const effective = getEffectiveTheme(theme)
  if (effective === 'light') {
    document.documentElement.classList.add('light')
  } else {
    document.documentElement.classList.remove('light')
  }
}

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void

  // Theme
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void

  // Modal states
  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      // Sidebar - default collapsed on mobile, expanded on desktop
      sidebarCollapsed: false,
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      // Theme - default dark
      theme: 'dark',
      setTheme: (theme) => {
        set({ theme })
        applyTheme(theme)
      },
      toggleTheme: () => {
        const current = get().theme
        // Cycle: dark -> light -> system -> dark
        const next: Theme =
          current === 'dark' ? 'light' : current === 'light' ? 'system' : 'dark'
        set({ theme: next })
        applyTheme(next)
      },

      // Command palette
      commandPaletteOpen: false,
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
      }),
      onRehydrateStorage: () => (state) => {
        // Apply theme on rehydration
        if (state?.theme) {
          applyTheme(state.theme)
        }
      },
    }
  )
)

// Listen for system theme changes when in 'system' mode
if (typeof window !== 'undefined') {
  window
    .matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => {
      const { theme } = useUIStore.getState()
      if (theme === 'system') {
        applyTheme('system')
      }
    })
}
