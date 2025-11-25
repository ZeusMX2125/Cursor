'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import TopBar from '@/components/TopBar'
import ProfessionalChart from '@/components/ProfessionalChart'
import ALGOXAccountPanel from '@/components/ALGOXAccountPanel'
import ALGOXOrderEntry from '@/components/ALGOXOrderEntry'
import ALGOXQuickStrategies from '@/components/ALGOXQuickStrategies'
import ALGOXPositionsTable from '@/components/ALGOXPositionsTable'
import BotControl from '@/components/BotControl'
import InstrumentSelector, { ProjectXContract } from '@/components/InstrumentSelector'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useSharedTradingState } from '@/hooks/useSharedTradingState'
import Sidebar from '@/components/Sidebar'
import ContractsSidebar from '@/components/ContractsSidebar'
import api from '@/lib/api'
import { subscribeToWebSocketMessages } from '@/lib/websocket'
import type { AccountSnapshot, Position, ProjectXOrder } from '@/types/dashboard'
import { useContracts } from '@/contexts/ContractsContext'
import { getContractDisplayName } from '@/lib/contractUtils'

export default function TradingPage() {
  const { data, loading, error, refresh } = useDashboardData({ pollInterval: 7000 })
  const sharedState = useSharedTradingState()
  const { contracts, getFirstContract, loading: contractsLoading } = useContracts()
  
  // Debug: Log WebSocket connection status (only in development)
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[TradingPage] WebSocket connected:', sharedState.connected)
    }
  }, [sharedState.connected])
  const [selectedAccountId, setSelectedAccountId] = useState<string | undefined>()
  const [botAccountId, setBotAccountId] = useState<string | undefined>()
  const [openOrders, setOpenOrders] = useState<ProjectXOrder[]>([])
  const [recentOrders, setRecentOrders] = useState<ProjectXOrder[]>([])
  const [fetching, setFetching] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [symbol, setSymbol] = useState<string>('')
  
  // Only use account-specific positions from API - ignore shared state for account-specific view
  const [accountPositions, setAccountPositions] = useState<Position[]>([])
  
  // Filter positions by selected account_id
  const positions = useMemo(() => {
    if (!selectedAccountId) return []
    
    // Only show positions for the selected account
    return accountPositions.filter((p: Position) => {
      const posAccountId = p.account_id ? String(p.account_id) : null
      return posAccountId === selectedAccountId
    })
  }, [accountPositions, selectedAccountId])
  const [timeframe, setTimeframe] = useState('1m')
  const [currentPrice, setCurrentPrice] = useState(0)
  const [priceChange, setPriceChange] = useState(0)
  const [priceChangePercent, setPriceChangePercent] = useState(0)
  const [selectedInstrument, setSelectedInstrument] = useState<ProjectXContract | null>(null)
  const [isAlgoPanelOpen, setIsAlgoPanelOpen] = useState(true)
  const fetchInFlightRef = useRef(false)

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
      if (!accountId) {
        // Clear data when no account selected
        setAccountPositions([])
        setOpenOrders([])
        setRecentOrders([])
        return
      }
      if (fetchInFlightRef.current) {
        return
      }
      fetchInFlightRef.current = true
      setFetching(true)
      setFetchError(null)
      try {
        // Fetch all data for the selected account
        const [positionsRes, pendingRes, recentRes] = await Promise.all([
          api.get(`/api/trading/positions/${accountId}`),
          api.get(`/api/trading/pending-orders/${accountId}`),
          api.get(`/api/trading/previous-orders/${accountId}`),
        ])
        
        // Ensure positions have account_id set and preserve all P&L fields and metadata
        const positionsWithAccount = (positionsRes.data.positions ?? []).map((p: any) => {
          const position: Position = {
            ...p,
            account_id: p.account_id || accountId,
            // Ensure all P&L fields are preserved from API
            unrealized_pnl: typeof p.unrealized_pnl === 'number' ? p.unrealized_pnl : undefined,
            realized_pnl: typeof p.realized_pnl === 'number' ? p.realized_pnl : undefined,
            entry_value: typeof p.entry_value === 'number' ? p.entry_value : undefined,
            current_value: typeof p.current_value === 'number' ? p.current_value : undefined,
            pnl_percent: typeof p.pnl_percent === 'number' ? p.pnl_percent : undefined,
            // Preserve tick/point metadata for accurate P&L calculations
            tick_size: typeof p.tick_size === 'number' ? p.tick_size : undefined,
            tick_value: typeof p.tick_value === 'number' ? p.tick_value : undefined,
            point_value: typeof p.point_value === 'number' ? p.point_value : undefined,
          }
          
          // Debug logging in development
          if (process.env.NODE_ENV === 'development') {
            console.log('[TradingPage] Position from API:', {
              symbol: position.symbol,
              unrealized_pnl: position.unrealized_pnl,
              current_price: position.current_price,
              entry_price: position.entry_price,
              quantity: position.quantity,
              side: position.side,
              tick_size: position.tick_size,
              tick_value: position.tick_value,
              point_value: position.point_value,
              raw: p
            })
          }
          
          return position
        })
        
        setAccountPositions(positionsWithAccount)
        setOpenOrders(pendingRes.data.orders ?? [])
        setRecentOrders(recentRes.data.orders ?? [])
        setFetchError(null)
      } catch (err: any) {
        setFetchError(err?.message ?? 'Unable to load trading data')
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
  
  // Also refresh periodically to get real-time updates
  useEffect(() => {
    if (!selectedAccountId) return
    
    const interval = setInterval(() => {
      fetchTradingData(selectedAccountId)
    }, 5000) // Refresh every 5 seconds
    
    return () => clearInterval(interval)
  }, [selectedAccountId, fetchTradingData])
  
  // Listen for WebSocket quote updates ONLY - update prices and recalculate P&L locally
  // Single source of truth: API provides position structure/metadata, WebSocket provides live prices
  useEffect(() => {
    if (!selectedAccountId) return
    
    const unsubscribe = subscribeToWebSocketMessages((event: MessageEvent) => {
      try {
        const message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data
        
        // ONLY handle quote updates - ignore position_update and realtime_snapshot
        // Position structure comes from API, WebSocket only updates prices
        if (message?.type === 'quote_update') {
          const payload = message.payload || message
          const quoteSymbol = (payload?.symbol || payload?.symbolId || '').toString().toUpperCase()
          const quotePrice = Number(payload?.price ?? payload?.lastPrice ?? payload?.close)
          
          if (!quoteSymbol || !quotePrice || Number.isNaN(quotePrice)) {
            return
          }
          
          // Debug logging in development
          if (process.env.NODE_ENV === 'development') {
            console.log(`[TradingPage] Quote update: ${quoteSymbol} = ${quotePrice}`)
          }
          
          // Update positions that match this symbol
          setAccountPositions((prev) => {
            let updated = false
            const newPositions = prev.map((position) => {
              const positionSymbol = (position.symbol || '').toUpperCase()
              
              // Check if this quote matches the position symbol
              // Handle various formats: "MES" matches "MESZ25", "F.US.MES", etc.
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
              
              // Debug logging in development
              if (process.env.NODE_ENV === 'development') {
                console.log(`[TradingPage] Updated P&L for ${positionSymbol}: unrealized=${unrealized.toFixed(2)}, pnl%=${pnlPercent.toFixed(2)}%`)
              }
              
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
        if (process.env.NODE_ENV === 'development') {
          console.error('[TradingPage] Error processing WebSocket message:', err)
        }
      }
    })
    
    return unsubscribe
  }, [selectedAccountId])
  
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

  // Helper to normalize position data - prefer API-provided values, use correct multipliers
  const normalizePosition = (position: any): Position => {
    const sideLabel = (position.side || position.type || 'LONG').toString().toUpperCase().includes('SHORT') ? 'SHORT' : 'LONG'
    const quantity = Number(position.quantity ?? position.size ?? 0) || 0
    const entryPrice = Number(position.entry_price ?? position.averagePrice ?? position.price ?? 0) || 0
    const currentPrice = Number(
      position.current_price ??
        position.marketPrice ??
        position.lastPrice ??
        entryPrice
    )
    
    const direction = sideLabel === 'SHORT' ? -1 : 1
    const priceMultiplier = getPriceMultiplier(position)
    
    // Use API-provided values when available, calculate only as fallback with correct multiplier
    const entryValue = typeof position.entry_value === 'number' && Number.isFinite(position.entry_value)
      ? position.entry_value
      : entryPrice * Math.abs(quantity) * priceMultiplier
    
    const currentValue = typeof position.current_value === 'number' && Number.isFinite(position.current_value)
      ? position.current_value
      : currentPrice * Math.abs(quantity) * priceMultiplier
    
    const unrealized = typeof position.unrealized_pnl === 'number' && Number.isFinite(position.unrealized_pnl)
      ? position.unrealized_pnl
      : (currentPrice - entryPrice) * Math.abs(quantity) * priceMultiplier * direction
    
    const pnlPercent = typeof position.pnl_percent === 'number' && Number.isFinite(position.pnl_percent)
      ? position.pnl_percent
      : (entryValue ? (unrealized / entryValue) * 100 : 0)
    
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
      current_value: currentValue,
      unrealized_pnl: unrealized,
      realized_pnl: typeof position.realized_pnl === 'number' ? position.realized_pnl : undefined,
      pnl_percent: pnlPercent,
      tick_size: typeof position.tick_size === 'number' ? position.tick_size : undefined,
      tick_value: typeof position.tick_value === 'number' ? position.tick_value : undefined,
      point_value: typeof position.point_value === 'number' ? position.point_value : undefined,
    }
  }

  const selectedAccount = useMemo(
    () => data?.projectx?.accounts.find((acct) => String(acct.id) === selectedAccountId),
    [data, selectedAccountId]
  )

  // Get bot account from ProjectX accounts or regular accounts
  const selectedBotAccount: AccountSnapshot | undefined = useMemo(() => {
    // First try ProjectX accounts (these are the actual trading accounts)
    if (data?.projectx?.accounts?.length && selectedAccountId) {
      const projectxAccount = data.projectx.accounts.find(
        (acct) => String(acct.id) === selectedAccountId
      )
      if (projectxAccount) {
        return {
          account_id: String(projectxAccount.id),
          name: projectxAccount.name || `Account ${projectxAccount.id}`,
          stage: '',
          size: '',
          running: false, // Will be updated by BotControl
          paper_trading: projectxAccount.simulated || false,
          enabled: projectxAccount.canTrade !== false,
          account_size: 0,
          daily_loss_limit: 0,
          profit_target: 0,
          balance: projectxAccount.balance || 0,
          buying_power: 0,
          metrics: {
            daily_pnl: 0,
            win_rate: 0,
            profit_factor: 0,
            trades_today: 0,
            total_trades: 0,
          },
          positions: [],
          pending_orders: [],
          manual_orders: [],
          strategies: {
            configured: [],
            active: null,
            agent: 'rule_based',
          },
        }
      }
    }
    
    // Fallback to regular accounts
    if (data?.accounts?.length) {
      if (botAccountId) {
        return data.accounts.find((acct) => acct.account_id === botAccountId)
      }
      return data.accounts[0]
    }
    
    return undefined
  }, [data, selectedAccountId, botAccountId])

  const handlePriceUpdate = (price: number, change: number, changePercent: number) => {
    setCurrentPrice(price)
    setPriceChange(change)
    setPriceChangePercent(changePercent)
  }

  const instrumentName = useMemo(() => {
    return getContractDisplayName(selectedInstrument)
  }, [selectedInstrument])

  const handleGlobalRefresh = () => {
    refresh()
    fetchTradingData(selectedAccountId)
  }

  return (
    <div className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden">
      <Sidebar />
      <ContractsSidebar
        selectedSymbol={symbol}
        onSelectContract={(newSymbol, contract) => {
          setSymbol(newSymbol)
          setSelectedInstrument(contract)
          // Reset price when symbol changes
          setCurrentPrice(0)
          setPriceChange(0)
          setPriceChangePercent(0)
        }}
      />
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
          {/* Price display in top-left of chart (matching reference) - removed to avoid overlap with chart header */}

          {/* Professional TradingView-style chart */}
          <ProfessionalChart
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
      <div
        className={`${isAlgoPanelOpen ? 'w-80' : 'w-10'} bg-[#0a0a0a] border-l border-[#1a1a1a] overflow-y-auto flex flex-col relative transition-all duration-200`}
      >
        <button
          onClick={() => setIsAlgoPanelOpen((prev) => !prev)}
          title={isAlgoPanelOpen ? 'Collapse ALGOX panel' : 'Expand ALGOX panel'}
          className="absolute -left-3 top-4 z-20 w-6 h-6 rounded-full bg-[#1a1a1a] border border-[#2a2a2a] text-xs text-gray-300 hover:text-white flex items-center justify-center shadow-lg"
        >
          {isAlgoPanelOpen ? '›' : '‹'}
        </button>
        {isAlgoPanelOpen ? (
          <>
            <ALGOXAccountPanel
              accounts={data?.projectx?.accounts ?? []}
              selectedAccountId={selectedAccountId}
              onSelectAccount={setSelectedAccountId}
              onRefresh={handleGlobalRefresh}
              loading={loading}
            />
            <BotControl 
              account={selectedBotAccount}
              onStatusChange={() => {
                refresh()
                fetchTradingData(selectedAccountId)
              }}
            />
            <ALGOXOrderEntry
              accountId={selectedAccountId}
              accountName={selectedAccount?.name}
              defaultSymbol={symbol}
              currentPrice={currentPrice}
              onOrderPlaced={() => {
                fetchTradingData(selectedAccountId)
                refresh()
              }}
            />
            <ALGOXQuickStrategies account={selectedBotAccount} onRefresh={refresh} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-[10px] text-gray-500 rotate-90 pointer-events-none select-none">
            ALGOX PANEL
          </div>
        )}
      </div>
    </div>
  )
}


