import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import Dashboard from "@/pages/Dashboard";
import StrategyList from "@/pages/StrategyList";
import StrategyBuilder from "@/pages/StrategyBuilder";
import BacktestList from "@/pages/BacktestList";
import BacktestReport from "@/pages/BacktestReport";
import TradeLog from "@/pages/TradeLog";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/strategies" element={<StrategyList />} />
            <Route path="/strategies/new" element={<StrategyBuilder />} />
            <Route path="/strategies/:id" element={<StrategyBuilder />} />
            <Route path="/backtests" element={<BacktestList />} />
            <Route path="/backtests/:id" element={<BacktestReport />} />
            <Route path="/backtests/:id/trades" element={<TradeLog />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
