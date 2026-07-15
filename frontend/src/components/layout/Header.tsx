import { Search, Moon, Sun, Monitor, Bell } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useUIStore } from '@/store/uiStore'
import { cn } from '@/lib/utils'

interface HeaderProps {
  title?: string
  children?: React.ReactNode
}

export function Header({ title, children }: HeaderProps) {
  const { theme, toggleTheme, sidebarCollapsed } = useUIStore()

  const ThemeIcon =
    theme === 'dark' ? Sun : theme === 'light' ? Moon : Monitor

  return (
    <header
      className={cn(
        'sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60',
        sidebarCollapsed ? 'ml-16' : 'ml-56'
      )}
    >
      <div className="flex items-center gap-4">
        {title && (
          <h1 className="text-lg font-semibold text-foreground">{title}</h1>
        )}
        {children}
      </div>

      <div className="flex items-center gap-2">
        {/* Search */}
        <div className="relative hidden md:block">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search... (⌘K)"
            className="w-64 pl-8"
          />
        </div>

        {/* Notifications */}
        <Button variant="ghost" size="icon">
          <Bell className="h-5 w-5" />
        </Button>

        {/* Theme toggle */}
        <Button variant="ghost" size="icon" onClick={toggleTheme}>
          <ThemeIcon className="h-5 w-5" />
        </Button>
      </div>
    </header>
  )
}
