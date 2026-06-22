import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from '@/components/layout'
import {
  Dashboard,
  StrategiesPage,
  StrategyDetailPage,
  StrategyBuilderPage,
  BacktestsPage,
  BacktestReportPage,
  ComparePage,
  ChartPage,
  RobustnessPage,
  SettingsPage,
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
            <Route path="/backtests/:id/trades" element={<BacktestReportPage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/chart" element={<ChartPage />} />
            <Route path="/chart/:ticker" element={<ChartPage />} />
            <Route path="/robustness" element={<RobustnessPage />} />
            <Route path="/robustness/:id" element={<RobustnessPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
