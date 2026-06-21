import axios from "axios";

// Determine API base URL
const getBaseUrl = () => {
  // Check for environment variable first
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  // In development, use localhost
  if (import.meta.env.DEV) {
    return "http://localhost:8000/api/v1";
  }
  // In production, use relative URL (same origin)
  return "/api/v1";
};

export const api = axios.create({
  baseURL: getBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected error occurred";

    console.error(`[API Error] ${message}`, error.response?.data);

    // Re-throw with a cleaner error message
    return Promise.reject(new Error(message));
  }
);
