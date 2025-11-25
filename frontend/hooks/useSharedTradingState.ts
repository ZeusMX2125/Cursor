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

const normalizeSymbol = (symbol: string): string => {
  // Extract symbol from ProjectX format without hardcoded mappings
  // Components using this hook should use ContractsContext for proper matching
  // "F.US.MES" -> "MES"
  // "F.US.EP" -> "EP" (components will map to actual contracts)
  // "MES" -> "MES"
  if (!symbol) return ''
  const upper = symbol.toUpperCase()
  if (upper.includes('.')) {
    const parts = upper.split('.')
    // Handle "F.US.MES" or "F.US.EP" format
    if (parts.length >= 3 && parts[0] === 'F' && parts[1] === 'US') {
      return parts[parts.length - 1] // Return last part (MES, EP, etc.)
    }
    // Handle contract ID format "CON.F.US.MES.H25" -> "MES"
    if (parts.length >= 4 && parts[0] === 'CON') {
      return parts[3] || upper
    }
  }
  return upper
}

const getPriceMultiplier = (source: any): number => {
  const pointValue = typeof source?.point_value === 'number' && Number.isFinite(source.point_value)
    ? source.point_value
    : undefined
  if (pointValue && pointValue !== 0) {
    return pointValue
  }

  const tickValue = typeof source?.tick_value === 'number' && Number.isFinite(source.tick_value)
    ? source.tick_value
    : undefined
  const tickSize = typeof source?.tick_size === 'number' && Number.isFinite(source.tick_size)
    ? source.tick_size
    : undefined

  if (tickValue && tickSize && tickSize !== 0) {
    return tickValue / tickSize
  }

  return 1
}

const normalizePosition = (position: any): Position => {
  const sideLabel = (position.side || position.type || 'LONG').toString().toUpperCase().includes('SHORT') ? 'SHORT' : 'LONG'
  const quantity = Number(position.quantity ?? position.size ?? 0) || 0
  const entryPrice = Number(position.entry_price ?? position.averagePrice ?? position.price ?? 0) || 0
  const positionSymbol = normalizeSymbol(position.symbol || '')
  const currentPrice = Number(
    position.current_price ??
      position.marketPrice ??
      position.lastPrice ??
      state.quotes[positionSymbol] ??
      entryPrice
  )

  const direction = sideLabel === 'SHORT' ? -1 : 1
  const priceMultiplier = getPriceMultiplier(position)

  const fallbackEntryValue = entryPrice * Math.abs(quantity) * priceMultiplier
  const entryValue =
    typeof position.entry_value === 'number' && Number.isFinite(position.entry_value)
      ? position.entry_value
      : fallbackEntryValue
  const fallbackCurrentValue = currentPrice * Math.abs(quantity) * priceMultiplier
  const currentValue =
    typeof position.current_value === 'number' && Number.isFinite(position.current_value)
      ? position.current_value
      : fallbackCurrentValue

  const fallbackUnrealized = (currentPrice - entryPrice) * Math.abs(quantity) * priceMultiplier * direction
  const unrealized =
    typeof position.unrealized_pnl === 'number' && Number.isFinite(position.unrealized_pnl)
      ? position.unrealized_pnl
      : fallbackUnrealized

  const pnlPercent =
    typeof position.pnl_percent === 'number' && Number.isFinite(position.pnl_percent)
      ? position.pnl_percent
      : entryValue
        ? (unrealized / entryValue) * 100
        : 0

  return {
    position_id: position.position_id ?? position.id ?? undefined,
    contract_id: position.contract_id,
    symbol: positionSymbol || (position.symbol ?? position.contractId ?? ''),
    side: sideLabel,
    quantity,
    entry_price: entryPrice,
    current_price: currentPrice,
    entry_time: position.entry_time ?? position.creationTimestamp ?? position.timestamp,
    account_id: position.account_id ?? position.accountId,
    entry_value: entryValue,
    current_value: currentValue,
    unrealized_pnl: unrealized,
    realized_pnl: typeof position.realized_pnl === 'number' ? position.realized_pnl : undefined,
    pnl_percent: pnlPercent,
    tick_size: typeof position.tick_size === 'number' ? position.tick_size : undefined,
    tick_value: typeof position.tick_value === 'number' ? position.tick_value : undefined,
    point_value: typeof position.point_value === 'number' ? position.point_value : undefined,
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
  let symbol = (payload?.symbol || payload?.symbolId || '').toString()
  symbol = normalizeSymbol(symbol)
  const price = Number(payload?.price ?? payload?.lastPrice ?? payload?.close)
  if (!symbol || !price || Number.isNaN(price)) {
    return
  }

  const quotes = { ...state.quotes, [symbol]: price }
  let changed = false
  const positions = state.positions.map((position) => {
    const positionSymbol = normalizeSymbol(position.symbol || '')
    if (positionSymbol !== symbol) {
      return position
    }

    const entryPrice = position.entry_price ?? price
    const quantity = position.quantity ?? 0
    const direction = position.side === 'SHORT' ? -1 : 1
    const priceMultiplier = getPriceMultiplier(position)
    const entryValue = entryPrice * Math.abs(quantity) * priceMultiplier
    const unrealized = (price - entryPrice) * Math.abs(quantity) * priceMultiplier * direction
    const pnlPercent = entryValue ? (unrealized / entryValue) * 100 : 0
    changed = true
    return {
      ...position,
      current_price: price,
      current_value: price * Math.abs(quantity) * priceMultiplier,
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
    // Merge snapshot positions with existing positions to preserve quote-updated prices
    const existingPositions = state.positions
    updates.positions = snapshot.positions.map((snapPos: any) => {
      const normalized = normalizePosition(snapPos)
      // If we have an existing position with quote-updated price, prefer that
      const existing = existingPositions.find(
        (p) => p.position_id === normalized.position_id || 
               (p.symbol === normalized.symbol && p.account_id === normalized.account_id)
      )
      if (existing && existing.current_price && existing.current_price !== normalized.entry_price) {
        // Use existing position's quote-updated price and recalculate P&L
        const entryPrice = normalized.entry_price ?? existing.entry_price ?? 0
        const currentPrice = existing.current_price
        const quantity = normalized.quantity ?? existing.quantity ?? 0
        const direction = normalized.side === 'SHORT' ? -1 : 1
        const entryValue = entryPrice * Math.abs(quantity)
        const unrealized = (currentPrice - entryPrice) * Math.abs(quantity) * direction
        const pnlPercent = entryValue ? (unrealized / entryValue) * 100 : 0
        
        return {
          ...normalized,
          current_price: currentPrice,
          current_value: currentPrice * Math.abs(quantity),
          entry_value: entryValue,
          unrealized_pnl: unrealized,
          pnl_percent: pnlPercent,
        }
      }
      return normalized
    })
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
    // Only update if position belongs to currently selected account
    // This will be filtered by the component using the position
    handlePositionUpdate(data.payload)
    return
  }

  if (data.type === 'realtime_snapshot' || data.accountBalance !== undefined || data.positions) {
    handleRealtimeSnapshot(data)
  }
  
  // Handle realized P&L updates from trade completions
  if (data.type === 'realized_pnl_update' || data.type === 'trade_update') {
    // Update positions with new realized P&L
    if (data.realized_pnl_by_symbol) {
      const positions = state.positions.map((position) => {
        const symbol = (position.symbol || '').toUpperCase()
        if (symbol in data.realized_pnl_by_symbol) {
          return {
            ...position,
            realized_pnl: data.realized_pnl_by_symbol[symbol],
          }
        }
        return position
      })
      emit({ positions, lastUpdate: new Date().toISOString() })
    }
  }
  
  // Handle positions refresh (triggered by quote updates to recalculate unrealized P&L)
  if (data.type === 'positions_refresh' && Array.isArray(data.positions)) {
    const refreshedPositions = data.positions.map(normalizePosition)
    emit({ 
      positions: refreshedPositions, 
      lastUpdate: data.timestamp || new Date().toISOString() 
    })
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
        // Only log status changes, not every check
        if (process.env.NODE_ENV === 'development') {
          console.log('[SharedState] WebSocket connection status:', connected)
        }
        emit({ connected })
      })
    } else {
      if (process.env.NODE_ENV === 'development') {
        console.warn('[SharedState] subscribeToWebSocketConnection not available')
      }
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


