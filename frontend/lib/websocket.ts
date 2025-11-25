'use client'

import { useEffect, useState } from 'react'

type MessageListener = (event: MessageEvent) => void
type ConnectionListener = (connected: boolean) => void

const messageListeners = new Set<MessageListener>()
const connectionListeners = new Set<ConnectionListener>()

let socket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let heartbeatInterval: ReturnType<typeof setInterval> | null = null
let initialized = false
let isConnected = false
let isConnecting = false
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 10
const INITIAL_RECONNECT_DELAY = 1000 // 1 second
const MAX_RECONNECT_DELAY = 30000 // 30 seconds
const HEARTBEAT_INTERVAL = 30000 // 30 seconds - send ping every 30s to keep connection alive
const CONNECTION_TIMEOUT = 10000 // 10 seconds - if no pong received, consider connection dead
let lastPongTime = 0

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const HEARTBEAT_URL = `${API_BASE_URL.replace(/\/$/, '')}/health`

// Only log in development
const isDev = process.env.NODE_ENV === 'development'
const log = (...args: any[]) => {
  if (isDev) {
    console.log(...args)
  }
}
const logError = (...args: any[]) => {
  if (isDev) {
    console.error(...args)
  }
}

const notifyConnection = (status: boolean) => {
  isConnected = status
  if (status) {
    reconnectAttempts = 0 // Reset on successful connection
  }
  connectionListeners.forEach((listener) => {
    try {
      listener(status)
    } catch (error) {
      logError('WebSocket connection listener error', error)
    }
  })
}

const notifyMessage = (event: MessageEvent) => {
  messageListeners.forEach((listener) => {
    try {
      listener(event)
    } catch (error) {
      logError('WebSocket message listener error', error)
    }
  })
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const startHeartbeat = () => {
  stopHeartbeat() // Clear any existing heartbeat
  
  heartbeatInterval = setInterval(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      // Check if we've received a pong recently
      const timeSinceLastPong = Date.now() - lastPongTime
      if (timeSinceLastPong > CONNECTION_TIMEOUT) {
        log('[WebSocket] No pong received, connection may be dead. Closing...')
        socket.close()
        return
      }
      
      // Send ping
      try {
        socket.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
        log('[WebSocket] Sent ping')
      } catch (error) {
        logError('[WebSocket] Error sending ping:', error)
        stopHeartbeat()
      }
    } else {
      stopHeartbeat()
    }
  }, HEARTBEAT_INTERVAL)
}

const stopHeartbeat = () => {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval)
    heartbeatInterval = null
  }
}

const scheduleReconnect = () => {
  if (reconnectTimer || isConnecting) {
    return
  }
  
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    log('[WebSocket] Max reconnection attempts reached. Stopping reconnection attempts.')
    return
  }
  
  // Exponential backoff with jitter
  const baseDelay = Math.min(
    INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempts),
    MAX_RECONNECT_DELAY
  )
  const jitter = Math.random() * 1000 // Add up to 1 second of jitter
  const delay = baseDelay + jitter
  
  reconnectAttempts++
  log(`[WebSocket] Scheduling reconnect attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS} in ${Math.round(delay)}ms`)
  
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    void connect()
  }, delay)
}

let backendReady = false
let backendCheckPromise: Promise<boolean> | null = null

const waitForBackendReady = async (): Promise<boolean> => {
  if (backendReady) return true
  if (backendCheckPromise) return backendCheckPromise

  backendCheckPromise = (async () => {
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const response = await fetch(HEARTBEAT_URL, { cache: 'no-store' })
        if (response.ok) {
          backendReady = true
          return true
        }
      } catch (error) {
        console.warn('[WebSocket] Backend heartbeat failed', error)
      }
      await sleep(500 * (attempt + 1))
    }
    return false
  })().finally(() => {
    backendCheckPromise = null
  })

  return backendCheckPromise
}

const connect = async () => {
  // Prevent multiple simultaneous connection attempts
  if (isConnecting) {
    log('[WebSocket] Connection attempt already in progress, skipping...')
    return
  }
  
  if (socket && socket.readyState === WebSocket.OPEN) {
    log('[WebSocket] Already connected')
    return
  }

  isConnecting = true

  try {
    const backendIsReady = await waitForBackendReady()
    if (!backendIsReady) {
      log('[WebSocket] Backend not ready yet; delaying connection attempt')
      notifyConnection(false)
      scheduleReconnect()
      return
    }
    
    if (socket) {
      // Clean up existing socket if it's in a bad state
      try {
        socket.close()
      } catch (e) {
        // Ignore errors when closing
      }
      socket = null
    }

    log(`[WebSocket] Attempting to connect to ${WS_URL}`)
    socket = new WebSocket(WS_URL)
  } catch (error) {
    logError('[WebSocket] Initialization failed:', error)
    notifyConnection(false)
    isConnecting = false
    scheduleReconnect()
    return
  }

  socket.onopen = () => {
    log('[WebSocket] Connected successfully')
    isConnecting = false
    reconnectAttempts = 0 // Reset on successful connection
    lastPongTime = Date.now()
    notifyConnection(true)
    
    // Start heartbeat to keep connection alive
    startHeartbeat()
  }

  socket.onmessage = (event: MessageEvent) => {
    try {
      // Check if it's a pong response
      const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data
      if (data?.type === 'pong') {
        lastPongTime = Date.now()
        log('[WebSocket] Received pong, connection alive')
        return
      }
    } catch (e) {
      // Not JSON or not a pong, continue to normal message handling
    }
    
    notifyMessage(event)
  }

  socket.onerror = (error) => {
    logError('[WebSocket] Connection error:', error)
    isConnecting = false
    notifyConnection(false)
  }

  socket.onclose = (event) => {
    const reason = event.reason || 'No reason provided'
    log(`[WebSocket] Connection closed. Code: ${event.code}, Reason: ${reason}`)
    stopHeartbeat()
    socket = null
    isConnecting = false
    notifyConnection(false)
    
    // Fast Refresh (HMR) often closes with code 1001 (going away) or 1006 (abnormal closure)
    // Also, code 1000 (normal closure) without a reason might be Fast Refresh
    // In development, we should always try to reconnect unless it's an explicit clean close
    const isFastRefresh = 
      process.env.NODE_ENV === 'development' && 
      (event.code === 1001 || event.code === 1006 || (event.code === 1000 && !reason))
    
    if (isFastRefresh) {
      log('[WebSocket] Detected Fast Refresh, will reconnect shortly...')
      // Reconnect after a short delay to allow Fast Refresh to complete
      setTimeout(() => {
        if (!socket && !isConnecting) {
          log('[WebSocket] Reconnecting after Fast Refresh...')
          reconnectAttempts = 0 // Reset attempts for Fast Refresh
          void connect()
        }
      }, 1000)
    } else if (event.code !== 1000) {
      // Abnormal closure - schedule reconnect
      scheduleReconnect()
    } else {
      // Clean close with reason - don't reconnect
      log('[WebSocket] Clean close, not reconnecting')
      reconnectAttempts = 0
    }
  }
}

const init = () => {
  if (initialized) {
    // If already initialized but not connected and not already connecting, try to reconnect
    // This handles Fast Refresh scenarios where the module reloads but connection is lost
    if (!isConnected && !socket && !isConnecting) {
      log('[WebSocket] Module reloaded (possibly Fast Refresh), reconnecting...')
      reconnectAttempts = 0 // Reset attempts
      void connect()
    }
    return
  }
  initialized = true
  log('[WebSocket] Initializing WebSocket connection to', WS_URL)
  
  // Small delay to ensure page is fully loaded
  if (typeof window !== 'undefined') {
    setTimeout(() => {
      void connect()
    }, 100)
  } else {
    void connect()
  }
  
  // Handle Fast Refresh in development - reconnect if connection is lost
  if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
    // Listen for visibility change (Fast Refresh often happens when tab regains focus)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !isConnected && !socket && !isConnecting) {
        log('[WebSocket] Tab became visible and connection is lost, reconnecting...')
        reconnectAttempts = 0
        void connect()
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    // Also check periodically in development
    const devCheckInterval = setInterval(() => {
      if (!isConnected && !socket && !isConnecting && document.visibilityState === 'visible') {
        log('[WebSocket] Development: Connection lost, reconnecting...')
        reconnectAttempts = 0
        void connect()
      }
    }, 5000) // Check every 5 seconds in dev
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
      clearInterval(devCheckInterval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    })
  }
}

export const subscribeToWebSocketMessages = (listener: MessageListener) => {
  init()
  messageListeners.add(listener)
  return () => {
    messageListeners.delete(listener)
  }
}

export const subscribeToWebSocketConnection = (listener: ConnectionListener) => {
  init()
  connectionListeners.add(listener)
  // Check socket state directly - it might be connected before listener was added
  const socketConnected = socket && socket.readyState === WebSocket.OPEN
  if (socketConnected && !isConnected) {
    console.log('[WebSocket] Socket already open, updating status')
    isConnected = true
  }
  // Immediately emit current status (or detected status)
  listener(isConnected || socketConnected || false)
  return () => {
    connectionListeners.delete(listener)
  }
}

export const getWebSocketConnectionStatus = () => isConnected

export const testWebSocketConnection = async (): Promise<boolean> => {
  return new Promise((resolve) => {
    if (isConnected) {
      resolve(true)
      return
    }
    
    const testSocket = new WebSocket(WS_URL)
    const timeout = setTimeout(() => {
      testSocket.close()
      resolve(false)
    }, 3000)
    
    testSocket.onopen = () => {
      clearTimeout(timeout)
      testSocket.close()
      resolve(true)
    }
    
    testSocket.onerror = () => {
      clearTimeout(timeout)
      resolve(false)
    }
  })
}

export function useWebSocket() {
  const [connected, setConnected] = useState<boolean>(isConnected)
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null)

  useEffect(() => {
    init()
    const unsubscribeConnection = subscribeToWebSocketConnection(setConnected)
    const unsubscribeMessages = subscribeToWebSocketMessages((event) => setLastMessage(event))
    return () => {
      unsubscribeConnection()
      unsubscribeMessages()
    }
  }, [])

  return { connected, lastMessage }
}

