import { Link, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
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
  Menu,
  X,
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
  const { sidebarCollapsed, toggleSidebar, mobileMenuOpen, setMobileMenuOpen } = useUIStore()

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/'
    return location.pathname.startsWith(href)
  }

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname, setMobileMenuOpen])

  // Close mobile menu on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileMenuOpen) {
        setMobileMenuOpen(false)
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [mobileMenuOpen, setMobileMenuOpen])

  return (
    <>
      {/* Mobile menu button - shown in header area on mobile */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed left-4 top-3 z-50 md:hidden"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
        aria-expanded={mobileMenuOpen}
      >
        {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </Button>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-border bg-surface-1 transition-all duration-300',
          // Mobile: slide in/out
          'max-md:-translate-x-full max-md:w-56',
          mobileMenuOpen && 'max-md:translate-x-0',
          // Desktop: collapse/expand
          'md:translate-x-0',
          sidebarCollapsed ? 'md:w-16' : 'md:w-56'
        )}
        role="navigation"
        aria-label="Main navigation"
      >
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-border px-3">
        <Link
          to="/"
          aria-label="Backtest Engine - Home"
          className={cn(
            'flex items-center gap-2 font-semibold text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-lg',
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
      <nav className="flex-1 space-y-1 p-2" aria-label="Main">
        {navigation.map((item) => {
          const active = isActive(item.href)
          const NavItem = (
            <Link
              key={item.name}
              to={item.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-surface-2 hover:text-foreground',
                sidebarCollapsed && 'justify-center px-2'
              )}
            >
              <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {!sidebarCollapsed && <span>{item.name}</span>}
              {sidebarCollapsed && <span className="sr-only">{item.name}</span>}
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
      <nav className="space-y-1 p-2" aria-label="Settings">
        {bottomNavigation.map((item) => {
          const active = isActive(item.href)
          const NavItem = (
            <Link
              key={item.name}
              to={item.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-surface-2 hover:text-foreground',
                sidebarCollapsed && 'justify-center px-2'
              )}
            >
              <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {!sidebarCollapsed && <span>{item.name}</span>}
              {sidebarCollapsed && <span className="sr-only">{item.name}</span>}
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

      {/* Collapse button - hidden on mobile */}
      <div className="hidden border-t border-border p-2 md:block">
        <Button
          variant="ghost"
          size={sidebarCollapsed ? 'icon' : 'sm'}
          onClick={toggleSidebar}
          className={cn('w-full', !sidebarCollapsed && 'justify-start')}
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
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
    </>
  )
}
