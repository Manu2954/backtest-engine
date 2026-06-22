import axios, { type AxiosError, type AxiosInstance } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081/api/v1'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      // Server responded with error status
      const status = error.response.status
      const data = error.response.data as { detail?: string; message?: string }

      if (status === 422) {
        // Validation error
        console.error('[API] Validation error:', data)
      } else if (status === 404) {
        console.error('[API] Resource not found:', error.config?.url)
      } else if (status === 429) {
        console.error('[API] Rate limit exceeded')
      } else if (status >= 500) {
        console.error('[API] Server error:', status, data)
      }
    } else if (error.request) {
      // Request made but no response
      console.error('[API] Network error - no response received')
    } else {
      console.error('[API] Request error:', error.message)
    }

    return Promise.reject(error)
  }
)

export default apiClient
