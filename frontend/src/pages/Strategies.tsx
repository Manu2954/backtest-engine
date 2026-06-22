import { Header } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import { Link } from 'react-router-dom'

export function StrategiesPage() {
  return (
    <>
      <Header title="Strategies">
        <Button asChild>
          <Link to="/strategies/new">
            <Plus className="h-4 w-4" />
            New Strategy
          </Link>
        </Button>
      </Header>
      <div className="p-6">
        <div className="flex items-center justify-center h-[400px] border border-dashed border-border rounded-lg">
          <p className="text-muted-foreground">Strategies list coming soon...</p>
        </div>
      </div>
    </>
  )
}
