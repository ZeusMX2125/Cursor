'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import TopBar from '@/components/TopBar'
import CandlestickChart from '@/components/CandlestickChart'
import ALGOXAccountPanel from '@/components/ALGOXAccountPanel'
import ALGOXOrderEntry from '@/components/ALGOXOrderEntry'
import ALGOXQuickStrategies from '@/components/ALGOXQuickStrategies'
import ALGOXPositionsTable from '@/components/ALGOXPositionsTable'
import InstrumentSelector, { ProjectXContract } from '@/components/InstrumentSelector'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useSharedTradingState } from '@/hooks/useSharedTradingState'
import Sidebar from '@/components/Sidebar'
import api from '@/lib/api'
import type { AccountSnapshot, Position, ProjectXOrder } from '@/types/dashboard'

export default function TradingPage() {
  const { data, loading, error, refresh } = useDashboardData({ pollInterval: 7000 })
  const sharedState = useSharedTradingState()
  
  // Debug: Log WebSocket connection status
  useEffect(() => {
    console.log('[TradingPage] WebSocket connected:', sharedState.connected)
  }, [sharedState.connected])
  const [selectedAccountId, setSelectedAccountId] = useState<string | undefined>()
  const [botAccountId, setBotAccountId] = useState<string | undefined>()
  const [openOrders, setOpenOrders] = useState<ProjectXOrder[]>([])
  const [recentOrders, setRecentOrders] = useState<ProjectXOrder[]>([])
  const [fetching, setFetching] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [symbol, setSymbol] = useState('ESZ25')
  
  // Use shared state positions, but also fetch account-specific positions
  const sharedPositions = sharedState.positions || []
  const [accountPositions, setAccountPositions] = useState<Position[]>([])
  
  // Merge shared positions with account-specific positions, prioritizing account-specific
  const positions = useMemo(() => {
    const accountPosMap = new Map<string, Position>()
    accountPositions.forEach(p => {
      const key = p.position_id || `${p.symbol}-${p.side}`
      accountPosMap.set(key, p)
    })
    
    const sharedPosMap = new Map<string, Position>()
    sharedPositions.forEach(p => {
      const key = p.position_id || `${p.symbol}-${p.side}`
      if (!accountPosMap.has(key)) {
        sharedPosMap.set(key, p)
      }
    })
    
    // Combine: account-specific first, then shared state
    const result: Position[] = []
    accountPosMap.forEach(p => result.push(p))
    sharedPosMap.forEach(p => result.push(p))
    return result
  }, [accountPositions, sharedPositions])
  const [timeframe, setTimeframe] = useState('1m')
  const [currentPrice, setCurrentPrice] = useState(0)
  const [priceChange, setPriceChange] = useState(0)
  const [priceChangePercent, setPriceChangePercent] = useState(0)
  const [selectedInstrument, setSelectedInstrument] = useState<ProjectXContract | null>(null)

  useEffect(() => {
    if (!selectedAccountId && data?.projectx?.accounts?.length) {
      setSelectedAccountId(String(data.projectx.accounts[0].id))
    }
  }, [data, selectedAccountId])

  useEffect(() => {
    if (data?.accounts?.length) {
      const matched = data.accounts.find((acct) => acct.account_id === selectedAccountId)
      if (matched) {
        setBotAccountId(matched.account_id)
      } else if (!botAccountId) {
        setBotAccountId(data.accounts[0].account_id)
      }
    }
  }, [data, selectedAccountId, botAccountId])

  const fetchTradingData = useCallback(
    async (accountId?: string) => {
      if (!accountId) return
      setFetching(true)
      setFetchError(null)
      try {
        const [positionsRes, pendingRes, recentRes] = await Promise.all([
          api.get(`/api/trading/positions/${accountId}`),
          api.get(`/api/trading/pending-orders/${accountId}`),
          api.get(`/api/trading/previous-orders/${accountId}`),
        ])
        setAccountPositions(positionsRes.data.positions ?? [])
        setOpenOrders(pendingRes.data.orders ?? [])
        setRecentOrders(recentRes.data.orders ?? [])
      } catch (err: any) {
        setFetchError(err?.message ?? 'Unable to load trading data')
      } finally {
        setFetching(false)
      }
    },
    []
  )

  useEffect(() => {
    fetchTradingData(selectedAccountId)
  }, [fetchTradingData, selectedAccountId])

  const selectedAccount = useMemo(
    () => data?.projectx?.accounts.find((acct) => String(acct.id) === selectedAccountId),
    [data, selectedAccountId]
  )

  const selectedBotAccount: AccountSnapshot | undefined = useMemo(() => {
    if (!data?.accounts?.length) return undefined
    if (botAccountId) {
      return data.accounts.find((acct) => acct.account_id === botAccountId)
    }
    return data.accounts[0]
  }, [data, botAccountId])

  const handlePriceUpdate = (price: number, change: number, changePercent: number) => {
    setCurrentPrice(price)
    setPriceChange(change)
    setPriceChangePercent(changePercent)
  }

  const instrumentName = useMemo(() => {
    if (selectedInstrument) {
      return selectedInstrument.description || selectedInstrument.name || selectedInstrument.symbol || ''
    }
    // Map common symbols to full names as fallback
    const symbolMap: Record<string, string> = {
      ESZ25: 'E-mini S&P 500: December 2025',
      NQZ25: 'E-mini NASDAQ-100: December 2025',
      M2KZ5: 'Micro E-mini Russell 2000: December 2025',
      ESZ5: 'E-mini S&P 500: December 2025',
    }
    return symbolMap[symbol] || ''
  }, [selectedInstrument, symbol])

  const handleGlobalRefresh = () => {
    refresh()
    fetchTradingData(selectedAccountId)
  }

  return (
    <div className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <TopBar
          symbol={symbol}
          instrumentName={instrumentName}
          price={currentPrice}
          priceChange={priceChange}
          priceChangePercent={priceChangePercent}
          wsConnected={sharedState?.connected ?? false}
          mdConnected={!fetchError}
          ordConnected={!fetchError}
          simMode={selectedAccount?.simulated ?? true}
          onSymbolChange={setSymbol}
          instrumentSelector={
            <InstrumentSelector
              value={symbol}
              onChange={(newSymbol) => {
                setSymbol(newSymbol)
                // Reset price when symbol changes
                setCurrentPrice(0)
                setPriceChange(0)
                setPriceChangePercent(0)
              }}
              onContractChange={setSelectedInstrument}
              showLabel
            />
          }
        />

        {/* Chart area with price display */}
        <div className="flex-1 flex flex-col relative">
          {(error || fetchError) && (
            <div className="absolute top-2 right-2 text-xs text-red-400 bg-[#1a1a1a] px-3 py-1 rounded border border-red-500/40">
              {error || fetchError}
            </div>
          )}
          {/* Price display in top-left of chart (matching reference) */}
          {currentPrice > 0 && (
            <div className="absolute top-2 left-2 z-10">
              <div className="text-base font-bold text-white">
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
            onRefresh={() => fetchTradingData(selectedAccountId)}
          />
        </div>
      </div>

      {/* Right sidebar */}
      <div className="w-80 bg-[#0a0a0a] border-l border-[#1a1a1a] overflow-y-auto flex flex-col">
        <ALGOXAccountPanel
          accounts={data?.projectx?.accounts ?? []}
          selectedAccountId={selectedAccountId}
          onSelectAccount={setSelectedAccountId}
          onRefresh={handleGlobalRefresh}
          loading={loading}
        />
        <ALGOXOrderEntry
          accountId={selectedAccountId}
          accountName={selectedAccount?.name}
          defaultSymbol={symbol}
          onOrderPlaced={() => fetchTradingData(selectedAccountId)}
        />
        <ALGOXQuickStrategies account={selectedBotAccount} onRefresh={refresh} />
      </div>
    </div>
  )
}


