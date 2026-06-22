// Re-export all API functions
export * from './endpoints/strategies'
export * from './endpoints/backtests'
export * from './endpoints/robustness'
export * from './endpoints/tickers'

// Also export the client itself
export { default as apiClient } from './client'

// Backward compatibility - import specific functions for re-export from client
import {
  getStrategies,
  getStrategy,
  createStrategy,
  updateStrategy,
  deleteStrategy,
} from './endpoints/strategies'

import {
  getBacktests,
  getBacktest,
  createBacktest,
  deleteBacktest,
  getBacktestTrades,
} from './endpoints/backtests'

import {
  validateTicker,
  checkHealth,
} from './endpoints/tickers'

// Named re-exports for client.ts compatibility
export {
  getStrategies,
  getStrategy,
  createStrategy,
  updateStrategy,
  deleteStrategy,
  getBacktests,
  getBacktest,
  createBacktest,
  deleteBacktest,
  getBacktestTrades,
  validateTicker,
  checkHealth,
}
