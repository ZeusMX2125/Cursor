import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  // withCredentials: false, // default; keep it off if using Bearer tokens
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const backendMessage =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.response?.data?.error

    if (backendMessage) {
      error.message = backendMessage
    }

    console.error('API request failed:', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
    })

    return Promise.reject(error)
  }
)

export default api

