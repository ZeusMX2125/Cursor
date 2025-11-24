'use client'

import { useSyncExternalStore } from 'react'
import api from '@/lib/api'
import type { Position } from '@/types/dashboard'
import {
  subscribeToWebSocketConnection,
  subscribeToWebSocketMessages,
} from '@/lib/websocket'

interface SharedTradingState {
  ready: boolean
  connected: boolean
  accountBalance: number
  dailyPnl: number
  winRate: number
  drawdown: number
  tradesToday: number
  positions: Position[]
  quotes: Record<string, number>
  lastUpdate?: string
}

const initialState: SharedTradingState = {
  ready: false,
  connected: false,
  accountBalance: 0,
  dailyPnl: 0,
  winRate: 0,
  drawdown: 0,
  tradesToday: 0,
  positions: [],
  quotes: {},
}

let state: SharedTradingState = initialState
const listeners = new Set<() => void>()
let initialized = false

const emit = (partial: Partial<SharedTradingState>) => {
  state = { ...state, ...partial }
  listeners.forEach((listener) => listener())
}

const subscribe = (listener: () => void) => {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

const getSnapshot = () => state

const normalizePosition = (position: any): Position => {
  const sideLabel = (position.side || position.type || 'LONG').toString().toUpperCase().includes('SHORT') ? 'SHORT' : 'LONG'
  const quantity = Number(position.quantity ?? position.size ?? 0) || 0
  const entryPrice = Number(position.entry_price ?? position.averagePrice ?? position.price ?? 0) || 0
  const currentPrice = Number(
    position.current_price ??
      position.marketPrice ??
      position.lastPrice ??
      state.quotes[position.symbol?.toUpperCase?.() || ''] ??
      entryPrice
  )

  const entryValue = entryPrice * Math.abs(quantity)
  const direction = sideLabel === 'SHORT' ? -1 : 1
  const unrealized =
    typeof position.unrealized_pnl === 'number'
      ? position.unrealized_pnl
      : (currentPrice - entryPrice) * Math.abs(quantity) * direction

  const pnlPercent = entryValue ? (unrealized / entryValue) * 100 : 0

  return {
    position_id: position.position_id ?? position.id ?? undefined,
    contract_id: position.contract_id,
    symbol: position.symbol ?? position.contractId ?? '',
    side: sideLabel,
    quantity,
    entry_price: entryPrice,
    current_price: currentPrice,
    entry_time: position.entry_time ?? position.creationTimestamp ?? position.timestamp,
    account_id: position.account_id ?? position.accountId,
    entry_value: entryValue,
    current_value: currentPrice * Math.abs(quantity),
    unrealized_pnl: unrealized,
    realized_pnl: typeof position.realized_pnl === 'number' ? position.realized_pnl : undefined,
    pnl_percent: pnlPercent,
  }
}

const upsertPosition = (incoming: Position) => {
  const key = incoming.position_id || `${incoming.symbol}-${incoming.side}`
  const updated = state.positions.filter((pos) => {
    const existingKey = pos.position_id || `${pos.symbol}-${pos.side}`
    return existingKey !== key
  })
  if (incoming.quantity !== 0) {
    updated.push(incoming)
  }
  emit({ positions: updated })
}

const handleQuoteUpdate = (payload: any) => {
  const symbol = (payload?.symbol || '').toString().toUpperCase()
  const price = Number(payload?.price ?? payload?.lastPrice ?? payload?.close)
  if (!symbol || !price || Number.isNaN(price)) {
    return
  }

  const quotes = { ...state.quotes, [symbol]: price }
  let changed = false
  const positions = state.positions.map((position) => {
    if ((position.symbol || '').toUpperCase() !== symbol) {
      return position
    }

    const entryPrice = position.entry_price ?? price
    const quantity = position.quantity ?? 0
    const direction = position.side === 'SHORT' ? -1 : 1
    const entryValue = entryPrice * Math.abs(quantity)
    const unrealized = (price - entryPrice) * Math.abs(quantity) * direction
    const pnlPercent = entryValue ? (unrealized / entryValue) * 100 : 0
    changed = true
    return {
      ...position,
      current_price: price,
      current_value: price * Math.abs(quantity),
      entry_value: entryValue,
      unrealized_pnl: unrealized,
      pnl_percent: pnlPercent,
    }
  })

  emit({
    quotes,
    positions: changed ? positions : state.positions,
    lastUpdate: new Date().toISOString(),
  })
}

const handlePositionUpdate = (payload: any) => {
  const normalized = normalizePosition(payload)
  upsertPosition(normalized)
}

const handleRealtimeSnapshot = (snapshot: any) => {
  const updates: Partial<SharedTradingState> = {
    ready: true,
    lastUpdate: snapshot.timestamp ?? new Date().toISOString(),
  }

  if (typeof snapshot.accountBalance === 'number') {
    updates.accountBalance = snapshot.accountBalance
  }
  if (typeof snapshot.dailyPnl === 'number') {
    updates.dailyPnl = snapshot.dailyPnl
  }
  if (typeof snapshot.winRate === 'number') {
    updates.winRate = snapshot.winRate
  }
  if (typeof snapshot.drawdown === 'number') {
    updates.drawdown = snapshot.drawdown
  }
  if (typeof snapshot.tradesToday === 'number') {
    updates.tradesToday = snapshot.tradesToday
  }

  if (Array.isArray(snapshot.positions)) {
    updates.positions = snapshot.positions.map(normalizePosition)
  }

  emit(updates)
}

const handleWebSocketMessage = (event: MessageEvent) => {
  let data: any
  try {
    data = JSON.parse(event.data)
  } catch {
    return
  }

  if (!data) {
    return
  }

  if (data.type === 'quote_update') {
    handleQuoteUpdate(data.payload)
    return
  }

  if (data.type === 'position_update') {
    handlePositionUpdate(data.payload)
    return
  }

  if (data.type === 'realtime_snapshot' || data.accountBalance !== undefined || data.positions) {
    handleRealtimeSnapshot(data)
  }
}

const fetchInitialSnapshot = async () => {
  try {
    const response = await api.get('/api/dashboard/state')
    const payload = response.data
    const accountBalance =
      payload?.projectx?.accounts?.reduce((sum: number, account: any) => sum + (account.balance || 0), 0) || 0
    handleRealtimeSnapshot({
      type: 'realtime_snapshot',
      accountBalance,
      dailyPnl: payload?.metrics?.dailyPnl || 0,
      winRate: payload?.metrics?.winRate || 0,
      drawdown: payload?.metrics?.drawdown || 0,
      tradesToday: payload?.metrics?.tradesToday || 0,
      positions: payload?.projectx?.positions || [],
      timestamp: payload?.timestamp,
    })
  } catch (error) {
    console.error('Failed to load initial dashboard snapshot', error)
  }
}

const initStore = () => {
  if (initialized) {
    return
  }
  initialized = true
  fetchInitialSnapshot()
  
  // Initialize WebSocket subscriptions
  try {
    if (typeof subscribeToWebSocketConnection === 'function') {
      subscribeToWebSocketConnection((connected) => {
        console.log('[SharedState] WebSocket connection status:', connected)
        emit({ connected })
      })
    } else {
      console.warn('[SharedState] subscribeToWebSocketConnection not available')
    }
    
    if (typeof subscribeToWebSocketMessages === 'function') {
      subscribeToWebSocketMessages(handleWebSocketMessage)
    } else {
      console.warn('[SharedState] subscribeToWebSocketMessages not available')
    }
  } catch (error) {
    console.error('[SharedState] Error initializing WebSocket:', error)
  }
}

export function useSharedTradingState() {
  initStore()
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
}


