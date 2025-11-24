'use client'

import { useEffect, useState } from 'react'
import { useWebSocket } from '@/lib/websocket'

interface RealtimeData {
  accountBalance: number
  dailyPnl: number
  winRate: number
  drawdown: number
  tradesToday: number
  positions: Array<{
    id: string
    symbol: string
    side: 'LONG' | 'SHORT'
    entry: number
    pnl: number
  }>
  strategy: string
  riskLevel: string
  targetPerDay: number
  goalProgress: number
}

export function useRealtimeData() {
  const [data, setData] = useState<RealtimeData | null>(null)
  const { connected, lastMessage } = useWebSocket()

  useEffect(() => {
    if (lastMessage) {
      try {
        const parsed = JSON.parse(lastMessage.data)
        setData(parsed)
      } catch (e) {
        console.error('Error parsing WebSocket message:', e)
      }
    }
  }, [lastMessage])

  return { data, connected }
}

