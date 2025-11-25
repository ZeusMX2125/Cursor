'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import TopBar from '@/components/TopBar'
import CandlestickChart from '@/components/CandlestickChart'
import ALGOXAccountPanel from '@/components/ALGOXAccountPanel'
import ALGOXOrderEntry from '@/components/ALGOXOrderEntry'
import ALGOXQuickStrategies from '@/components/ALGOXQuickStrategies'
import ALGOXPositionsTable from '@/components/ALGOXPositionsTable'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useContracts } from '@/contexts/ContractsContext'
import { getContractDisplayName } from '@/lib/contractUtils'
import api from '@/lib/api'
import { subscribeToWebSocketMessages } from '@/lib/websocket'
import type { ProjectXContract } from '@/components/InstrumentSelector'
import type { Position, ProjectXOrder } from '@/types/dashboard'

export default function ALGOXTradingPage() {
  const { data, loading, error, refresh } = useDashboardData({ pollInterval: 7000 })
  const { contracts, getFirstContract, loading: contractsLoading } = useContracts()
  const [selectedAccountId, setSelectedAccountId] = useState<string | undefined>()
  const [symbol, setSymbol] = useState<string>('')
  const [timeframe, setTimeframe] = useState('1m')
  const [currentPrice, setCurrentPrice] = useState(0)
  const [priceChange, setPriceChange] = useState(0)
  const [priceChangePercent, setPriceChangePercent] = useState(0)
  const [selectedInstrument, setSelectedInstrument] = useState<ProjectXContract | null>(null)

  // Position and order state
  const [accountPositions, setAccountPositions] = useState<Position[]>([])
  const [openOrders, setOpenOrders] = useState<ProjectXOrder[]>([])
  const [recentOrders, setRecentOrders] = useState<ProjectXOrder[]>([])
  const [fetching, setFetching] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const fetchInFlightRef = useRef(false)
  const consecutiveErrorsRef = useRef(0) // Track consecutive errors for backoff

  // Initialize symbol from first available ProjectX contract
  useEffect(() => {
    if (!contractsLoading && contracts.length > 0 && !symbol) {
      const firstContract = getFirstContract()
      if (firstContract?.symbol) {
        setSymbol(firstContract.symbol)
        setSelectedInstrument(firstContract)
      }
    }
  }, [contractsLoading, contracts, symbol, getFirstContract])

  useEffect(() => {
    if (!selectedAccountId && data?.accounts?.length) {
      setSelectedAccountId(data.accounts[0].account_id)
    }
  }, [data, selectedAccountId])

  const selectedAccount = useMemo(
    () => data?.accounts.find((acct) => acct.account_id === selectedAccountId),
    [data, selectedAccountId]
  )

  // Filter positions by selected account_id
  const positions = useMemo(() => {
    if (!selectedAccountId) return []
    return accountPositions.filter((p: Position) => {
      const posAccountId = p.account_id ? String(p.account_id) : null
      return posAccountId === selectedAccountId
    })
  }, [accountPositions, selectedAccountId])

  // Helper to get price multiplier from position metadata
  const getPriceMultiplier = (position: any): number => {
    const pointValue = typeof position?.point_value === 'number' && Number.isFinite(position.point_value)
      ? position.point_value
      : undefined
    if (pointValue && pointValue !== 0) {
      return pointValue
    }

    const tickValue = typeof position?.tick_value === 'number' && Number.isFinite(position.tick_value)
      ? position.tick_value
      : undefined
    const tickSize = typeof position?.tick_size === 'number' && Number.isFinite(position.tick_size)
      ? position.tick_size
      : undefined

    if (tickValue && tickSize && tickSize !== 0) {
      return tickValue / tickSize
    }

    return 1
  }

  // Fetch trading data for the selected account
  const fetchTradingData = useCallback(
    async (accountId?: string) => {
      if (!accountId) {
        setAccountPositions([])
        setOpenOrders([])
        setRecentOrders([])
        consecutiveErrorsRef.current = 0
        return
      }
      if (fetchInFlightRef.current) {
        return
      }
      fetchInFlightRef.current = true
      setFetching(true)
      
      try {
        // Use Promise.allSettled to handle partial failures gracefully
        const [positionsResult, pendingResult, recentResult] = await Promise.allSettled([
          api.get(`/api/trading/positions/${accountId}`),
          api.get(`/api/trading/pending-orders/${accountId}`),
          api.get(`/api/trading/previous-orders/${accountId}`),
        ])

        // Process positions if successful
        if (positionsResult.status === 'fulfilled') {
          const positionsWithAccount = (positionsResult.value.data.positions ?? []).map((p: any) => {
            const position: Position = {
              ...p,
              account_id: p.account_id || accountId,
              unrealized_pnl: typeof p.unrealized_pnl === 'number' ? p.unrealized_pnl : undefined,
              realized_pnl: typeof p.realized_pnl === 'number' ? p.realized_pnl : undefined,
              entry_value: typeof p.entry_value === 'number' ? p.entry_value : undefined,
              current_value: typeof p.current_value === 'number' ? p.current_value : undefined,
              pnl_percent: typeof p.pnl_percent === 'number' ? p.pnl_percent : undefined,
              tick_size: typeof p.tick_size === 'number' ? p.tick_size : undefined,
              tick_value: typeof p.tick_value === 'number' ? p.tick_value : undefined,
              point_value: typeof p.point_value === 'number' ? p.point_value : undefined,
            }
            return position
          })
          setAccountPositions(positionsWithAccount)
        } else {
          // Keep existing positions on error (don't clear them)
          console.warn('[ALGOX] Failed to fetch positions:', positionsResult.reason)
        }

        // Process orders if successful
        if (pendingResult.status === 'fulfilled') {
          setOpenOrders(pendingResult.value.data.orders ?? [])
        } else {
          console.warn('[ALGOX] Failed to fetch pending orders:', pendingResult.reason)
        }

        if (recentResult.status === 'fulfilled') {
          setRecentOrders(recentResult.value.data.orders ?? [])
        } else {
          console.warn('[ALGOX] Failed to fetch recent orders:', recentResult.reason)
        }

        // Check if all requests failed
        const allFailed = 
          positionsResult.status === 'rejected' && 
          pendingResult.status === 'rejected' && 
          recentResult.status === 'rejected'

        if (allFailed) {
          const error = positionsResult.reason || pendingResult.reason || recentResult.reason
          const isTimeout = error?.response?.status === 504 || error?.code === 'ECONNABORTED'
          setFetchError(isTimeout 
            ? 'Backend timeout - ProjectX API is slow. Data may be stale.' 
            : 'Unable to load trading data')
          consecutiveErrorsRef.current += 1
        } else {
          // At least one request succeeded
          setFetchError(null)
          consecutiveErrorsRef.current = 0
        }
      } catch (err: any) {
        const isTimeout = err?.response?.status === 504 || err?.code === 'ECONNABORTED'
        setFetchError(isTimeout 
          ? 'Backend timeout - ProjectX API is slow. Data may be stale.' 
          : err?.message ?? 'Unable to load trading data')
        consecutiveErrorsRef.current += 1
      } finally {
        setFetching(false)
        fetchInFlightRef.current = false
      }
    },
    []
  )

  // Fetch data when account changes
  useEffect(() => {
    fetchTradingData(selectedAccountId)
  }, [fetchTradingData, selectedAccountId])

  // Refresh periodically to get real-time updates with backoff on errors
  useEffect(() => {
    if (!selectedAccountId) return

    // Use a longer interval when backend is struggling (every 15s instead of 5s)
    // This reduces load on the backend when it's timing out
    const baseInterval = 15000 // 15 seconds - longer to reduce backend load
    
    const interval = setInterval(() => {
      // Only fetch if we haven't had too many consecutive errors
      // If we have 3+ consecutive errors, skip this refresh to give backend time
      if (consecutiveErrorsRef.current < 3) {
        fetchTradingData(selectedAccountId)
      } else {
        // After 3 consecutive errors, wait longer (60s) before trying again
        // This will be handled by the next interval cycle
        if (process.env.NODE_ENV === 'development') {
          console.log('[ALGOX] Skipping refresh due to consecutive errors, will retry later')
        }
      }
    }, baseInterval)

    // Initial fetch
    fetchTradingData(selectedAccountId)

    return () => clearInterval(interval)
  }, [selectedAccountId, fetchTradingData])

  // Listen for WebSocket quote updates - update prices and recalculate P&L locally
  useEffect(() => {
    if (!selectedAccountId) return

    const unsubscribe = subscribeToWebSocketMessages((event: MessageEvent) => {
      try {
        const message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data

        if (message?.type === 'quote_update') {
          const payload = message.payload || message
          const quoteSymbol = (payload?.symbol || payload?.symbolId || '').toString().toUpperCase()
          const quotePrice = Number(payload?.price ?? payload?.lastPrice ?? payload?.close)

          if (!quoteSymbol || !quotePrice || Number.isNaN(quotePrice)) {
            return
          }

          // Update positions that match this symbol
          setAccountPositions((prev) => {
            let updated = false
            const newPositions = prev.map((position) => {
              const positionSymbol = (position.symbol || '').toUpperCase()

              // Check if this quote matches the position symbol
              const symbolMatches =
                positionSymbol === quoteSymbol ||
                positionSymbol.includes(quoteSymbol) ||
                quoteSymbol.includes(positionSymbol) ||
                positionSymbol.replace(/[0-9]/g, '') === quoteSymbol.replace(/[0-9]/g, '')

              if (!symbolMatches) {
                return position
              }

              updated = true

              // Update current price and recalculate P&L using metadata from API
              const entryPrice = position.entry_price || 0
              const quantity = position.quantity || 0
              const direction = position.side === 'SHORT' ? -1 : 1
              const priceMultiplier = getPriceMultiplier(position)

              const entryValue = position.entry_value ?? (entryPrice * Math.abs(quantity) * priceMultiplier)
              const currentValue = quotePrice * Math.abs(quantity) * priceMultiplier
              const unrealized = (quotePrice - entryPrice) * Math.abs(quantity) * priceMultiplier * direction
              const pnlPercent = entryValue ? (unrealized / entryValue) * 100 : 0

              return {
                ...position,
                current_price: quotePrice,
                current_value: currentValue,
                unrealized_pnl: unrealized,
                pnl_percent: pnlPercent,
              }
            })

            return updated ? newPositions : prev
          })
        }
      } catch (err) {
        // Silently ignore parsing errors
      }
    })

    return unsubscribe
  }, [selectedAccountId])

  const handlePriceUpdate = (price: number, change: number, changePercent: number) => {
    setCurrentPrice(price)
    setPriceChange(change)
    setPriceChangePercent(changePercent)
  }

  const instrumentName = useMemo(() => {
    return getContractDisplayName(selectedInstrument)
  }, [selectedInstrument])

  const handleRefresh = useCallback(() => {
    refresh()
    fetchTradingData(selectedAccountId)
  }, [refresh, fetchTradingData, selectedAccountId])

  return (
    <div className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden">
      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <TopBar
          symbol={symbol}
          instrumentName={instrumentName}
          price={currentPrice}
          priceChange={priceChange}
          priceChangePercent={priceChangePercent}
          wsConnected={true}
          mdConnected={!fetchError}
          ordConnected={!fetchError}
          simMode={selectedAccount?.paper_trading ?? true}
        />

        {/* Chart area with price display */}
        <div className="flex-1 flex flex-col relative">
          {/* Error display */}
          {(error || fetchError) && (
            <div className="absolute top-2 right-2 text-xs text-red-400 bg-[#1a1a1a] px-3 py-1 rounded border border-red-500/40 z-10">
              {error || fetchError}
            </div>
          )}

          {/* Price display overlay */}
          {currentPrice > 0 && (
            <div className="absolute top-4 left-4 z-10 bg-[#1a1a1a]/90 border border-[#2a2a2a] rounded px-3 py-2">
              <div className="text-lg font-bold text-white">
                {symbol} {currentPrice.toFixed(2)}
                {priceChangePercent !== 0 && (
                  <span className={`ml-2 text-sm ${priceChangePercent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    ({priceChangePercent >= 0 ? '+' : ''}{priceChangePercent.toFixed(2)}%)
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Candlestick chart */}
          <CandlestickChart
            symbol={symbol}
            timeframe={timeframe}
            onTimeframeChange={setTimeframe}
            onPriceUpdate={handlePriceUpdate}
            positions={positions.filter((p: Position) => {
              const posSymbol = p.symbol?.toUpperCase() || ''
              const currentSymbol = symbol.toUpperCase()
              return posSymbol === currentSymbol || posSymbol.includes(currentSymbol) || currentSymbol.includes(posSymbol)
            })}
          />

          {/* Positions table */}
          <ALGOXPositionsTable
            accountId={selectedAccountId}
            positions={positions}
            openOrders={openOrders}
            recentOrders={recentOrders}
            onRefresh={handleRefresh}
          />
        </div>
      </div>

      {/* Right sidebar */}
      <div className="w-80 bg-[#0a0a0a] border-l border-[#1a1a1a] overflow-y-auto flex flex-col">
        <ALGOXAccountPanel
          accounts={(data?.accounts ?? []).map(acct => ({
            id: acct.account_id,
            name: acct.name,
            balance: acct.balance,
            simulated: acct.paper_trading,
            canTrade: acct.enabled,
          }))}
          selectedAccountId={selectedAccountId}
          onSelectAccount={setSelectedAccountId}
          onRefresh={handleRefresh}
          loading={loading}
        />
        <ALGOXOrderEntry 
          accountId={selectedAccountId} 
          accountName={selectedAccount?.name}
          defaultSymbol={symbol} 
          onOrderPlaced={handleRefresh} 
        />
        <ALGOXQuickStrategies account={selectedAccount} onRefresh={handleRefresh} />
      </div>
    </div>
  )
}
