import { useState, useEffect } from 'react'
import { Header } from '@/components/layout'
import { ComparisonSelector } from '@/components/comparison/ComparisonSelector'
import ComparisonTable from '@/components/comparison/ComparisonTable'
import OverlaidEquityCurve from '@/components/comparison/OverlaidEquityCurve'
import { useComparisonStore } from '@/store/comparisonStore'
import { getBacktest } from '@/api'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
import type { BacktestOut } from '@/types'

export function ComparePage() {
  const { selectedIds } = useComparisonStore()
  const [backtests, setBacktests] = useState<BacktestOut[]>([])
  const [loading, setLoading] = useState(false)
  const [showResults, setShowResults] = useState(false)

  useEffect(() => {
    if (selectedIds.length < 2 || !showResults) {
      setBacktests([])
      return
    }

    setLoading(true)
    Promise.all(selectedIds.map((id) => getBacktest(id)))
      .then((results) => setBacktests(results))
      .catch((err) => console.error('Failed to load backtests:', err))
      .finally(() => setLoading(false))
  }, [selectedIds, showResults])

  const handleCompare = () => {
    setShowResults(true)
  }

  const handleBack = () => {
    setShowResults(false)
  }

  return (
    <>
      <Header title="Compare Backtests" />
      <div className="p-6 space-y-6">
        {!showResults ? (
          <ComparisonSelector onCompare={handleCompare} />
        ) : loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-muted-foreground">Loading comparison data...</div>
          </div>
        ) : (
          <>
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold">
                Comparing {backtests.length} Backtests
              </h2>
              <Button
                variant="outline"
                onClick={handleBack}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Change Selection
              </Button>
            </div>
            <OverlaidEquityCurve backtests={backtests} />
            <ComparisonTable backtests={backtests} />
          </>
        )}
      </div>
    </>
  )
}
