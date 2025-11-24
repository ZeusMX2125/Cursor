'use client'

import { useEffect, useState } from 'react'

type MessageListener = (event: MessageEvent) => void
type ConnectionListener = (connected: boolean) => void

const messageListeners = new Set<MessageListener>()
const connectionListeners = new Set<ConnectionListener>()

let socket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let initialized = false
let isConnected = false

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'

const notifyConnection = (status: boolean) => {
  isConnected = status
  connectionListeners.forEach((listener) => {
    try {
      listener(status)
    } catch (error) {
      console.error('WebSocket connection listener error', error)
    }
  })
}

const notifyMessage = (event: MessageEvent) => {
  messageListeners.forEach((listener) => {
    try {
      listener(event)
    } catch (error) {
      console.error('WebSocket message listener error', error)
    }
  })
}

const scheduleReconnect = () => {
  if (reconnectTimer) {
    return
  }
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    connect()
  }, 5000)
}

const connect = () => {
  if (socket && socket.readyState === WebSocket.OPEN) {
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

  try {
    console.log(`[WebSocket] Attempting to connect to ${WS_URL}`)
    socket = new WebSocket(WS_URL)
  } catch (error) {
    console.error('[WebSocket] Initialization failed:', error)
    notifyConnection(false)
    scheduleReconnect()
    return
  }

  socket.onopen = () => {
    console.log('[WebSocket] Connected successfully')
    notifyConnection(true)
  }

  socket.onmessage = (event: MessageEvent) => {
    notifyMessage(event)
  }

  socket.onerror = (error) => {
    console.error('[WebSocket] Connection error:', error)
    notifyConnection(false)
  }

  socket.onclose = (event) => {
    console.log(`[WebSocket] Connection closed. Code: ${event.code}, Reason: ${event.reason || 'No reason provided'}`)
    socket = null
    notifyConnection(false)
    scheduleReconnect()
  }
}

const init = () => {
  if (initialized) {
    // If already initialized but not connected, try to reconnect
    if (!isConnected && !socket) {
      console.log('[WebSocket] Reconnecting...')
      connect()
    }
    return
  }
  initialized = true
  console.log('[WebSocket] Initializing WebSocket connection to', WS_URL)
  
  // Small delay to ensure page is fully loaded
  if (typeof window !== 'undefined') {
    setTimeout(() => {
      connect()
    }, 100)
  } else {
    connect()
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

