import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from '@/components/layout'
import { ErrorBoundary } from '@/components/shared/ErrorBoundary'
import {
  Dashboard,
  StrategiesPage,
  StrategyDetailPage,
  StrategyBuilderPage,
  BacktestsPage,
  BacktestReportPage,
  BacktestTradesPage,
  ComparePage,
  ChartPage,
  RobustnessPage,
  SettingsPage,
  NotFoundPage,
} from '@/pages'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/strategies" element={<StrategiesPage />} />
              <Route path="/strategies/new" element={<StrategyBuilderPage />} />
              <Route path="/strategies/:id" element={<StrategyDetailPage />} />
              <Route path="/strategies/:id/edit" element={<StrategyBuilderPage />} />
              <Route path="/backtests" element={<BacktestsPage />} />
              <Route path="/backtests/:id" element={<BacktestReportPage />} />
              <Route path="/backtests/:id/trades" element={<BacktestTradesPage />} />
              <Route path="/compare" element={<ComparePage />} />
              <Route path="/chart" element={<ChartPage />} />
              <Route path="/chart/:ticker" element={<ChartPage />} />
              <Route path="/robustness" element={<RobustnessPage />} />
              <Route path="/robustness/:id" element={<RobustnessPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  )
}

export default App
