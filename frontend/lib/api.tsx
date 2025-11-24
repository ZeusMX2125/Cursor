import axios from 'axios'

// Next.js automatically makes NEXT_PUBLIC_* env vars available
// Use a type-safe approach that works in both client and server
const API_BASE_URL = 
  // @ts-ignore - Next.js injects this at build time
  (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_URL) || 
  'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const backendMessage =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.response?.data?.error ||
      error?.message

    if (backendMessage) {
      error.message = backendMessage
    }

    // More detailed error logging
    const errorDetails = {
      url: error.config?.url || 'unknown',
      method: error.config?.method?.toUpperCase() || 'unknown',
      status: error.response?.status || 'no response',
      statusText: error.response?.statusText || 'no response',
      message: error.message || 'Unknown error',
      code: error.code || 'no code',
      responseData: error.response?.data || null,
    }

    console.error('API request failed:', JSON.stringify(errorDetails, null, 2))
    
    // Log CORS-specific errors
    if (error.code === 'ERR_NETWORK' || error.message?.includes('CORS')) {
      console.error('CORS Error detected. Check:')
      console.error('1. Is backend running on http://localhost:8000?')
      console.error('2. Did you restart the backend after CORS changes?')
      console.error('3. Check backend logs for errors')
    }

    return Promise.reject(error)
  }
)

export default api

