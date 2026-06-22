import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useUIStore } from '@/store/uiStore'
import { cn } from '@/lib/utils'

export function AppShell() {
  const { sidebarCollapsed } = useUIStore()

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background">
        <Sidebar />
        <main
          className={cn(
            'min-h-screen transition-all duration-300',
            sidebarCollapsed ? 'ml-16' : 'ml-56'
          )}
        >
          <Outlet />
        </main>
      </div>
    </TooltipProvider>
  )
}
