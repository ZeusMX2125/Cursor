import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
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

    const hasResponse = Boolean(error?.response)
    const hasRequest = Boolean(error?.request)
    const corsHeader = error?.response?.headers?.['access-control-allow-origin']
    const isBrowser = typeof window !== 'undefined'
    let diagnostic: 'backend-error' | 'cors-blocked' | 'missing-cors-header' | 'network-unreachable' | undefined

    if (backendMessage) {
      error.message = backendMessage
      diagnostic = 'backend-error'
    }

    if (!hasResponse && hasRequest) {
      const looksLikeCorsBlock = isBrowser && error?.message?.toLowerCase().includes('network error')
      if (looksLikeCorsBlock) {
        error.message = backendMessage || 'Request blocked by browser CORS. Verify FastAPI has this origin in its allow list.'
        diagnostic = 'cors-blocked'
      } else {
        error.message = backendMessage || 'Unable to reach backend (network failure). Is http://localhost:8000 running?'
        diagnostic = 'network-unreachable'
      }
    } else if (hasResponse && !corsHeader && isBrowser) {
      diagnostic = 'missing-cors-header'
      error.message =
        backendMessage ||
        'Backend responded without Access-Control-Allow-Origin. Check FastAPI CORS configuration.'
    }

    // More detailed error logging (skip 404s to reduce console noise)
    if (error.response?.status !== 404) {
      const errorDetails = {
        url: error.config?.url || 'unknown',
        method: error.config?.method?.toUpperCase() || 'unknown',
        status: error.response?.status || 'no response',
        statusText: error.response?.statusText || 'no response',
        message: error.message || 'Unknown error',
        code: error.code || 'no code',
        responseData: error.response?.data || null,
        diagnostic,
      }

      console.error('API request failed:', JSON.stringify(errorDetails, null, 2))
    }
    
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
