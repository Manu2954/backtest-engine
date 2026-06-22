import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  LineChart,
  FlaskConical,
  Settings,
  GitCompare,
  Shield,
  CandlestickChart,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'
import { useUIStore } from '@/store/uiStore'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Strategies', href: '/strategies', icon: FlaskConical },
  { name: 'Backtests', href: '/backtests', icon: LineChart },
  { name: 'Compare', href: '/compare', icon: GitCompare },
  { name: 'Chart', href: '/chart', icon: CandlestickChart },
  { name: 'Robustness', href: '/robustness', icon: Shield },
]

const bottomNavigation = [
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const location = useLocation()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/'
    return location.pathname.startsWith(href)
  }

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-border bg-surface-1 transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-56'
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-border px-3">
        <Link
          to="/"
          className={cn(
            'flex items-center gap-2 font-semibold text-foreground',
            sidebarCollapsed && 'justify-center'
          )}
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <LineChart className="h-4 w-4 text-primary-foreground" />
          </div>
          {!sidebarCollapsed && <span>Backtest</span>}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {navigation.map((item) => {
          const active = isActive(item.href)
          const NavItem = (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-surface-2 hover:text-foreground',
                sidebarCollapsed && 'justify-center px-2'
              )}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {!sidebarCollapsed && <span>{item.name}</span>}
            </Link>
          )

          if (sidebarCollapsed) {
            return (
              <Tooltip key={item.name} delayDuration={0}>
                <TooltipTrigger asChild>{NavItem}</TooltipTrigger>
                <TooltipContent side="right">{item.name}</TooltipContent>
              </Tooltip>
            )
          }

          return NavItem
        })}
      </nav>

      <Separator />

      {/* Bottom navigation */}
      <nav className="space-y-1 p-2">
        {bottomNavigation.map((item) => {
          const active = isActive(item.href)
          const NavItem = (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-surface-2 hover:text-foreground',
                sidebarCollapsed && 'justify-center px-2'
              )}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {!sidebarCollapsed && <span>{item.name}</span>}
            </Link>
          )

          if (sidebarCollapsed) {
            return (
              <Tooltip key={item.name} delayDuration={0}>
                <TooltipTrigger asChild>{NavItem}</TooltipTrigger>
                <TooltipContent side="right">{item.name}</TooltipContent>
              </Tooltip>
            )
          }

          return NavItem
        })}
      </nav>

      {/* Collapse button */}
      <div className="border-t border-border p-2">
        <Button
          variant="ghost"
          size={sidebarCollapsed ? 'icon' : 'sm'}
          onClick={toggleSidebar}
          className={cn('w-full', !sidebarCollapsed && 'justify-start')}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span>Collapse</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  )
}
