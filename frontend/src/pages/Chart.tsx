import { Header } from '@/components/layout'

export function ChartPage() {
  return (
    <>
      <Header title="Chart" />
      <div className="p-6">
        <div className="flex items-center justify-center h-[600px] border border-dashed border-border rounded-lg">
          <p className="text-muted-foreground">Live chart coming soon...</p>
        </div>
      </div>
    </>
  )
}
