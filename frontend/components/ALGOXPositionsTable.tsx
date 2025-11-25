'use client'

import { type CSSProperties, useMemo, useState } from 'react'
import api from '@/lib/api'
import type { Position, ProjectXOrder } from '@/types/dashboard'

interface ALGOXPositionsTableProps {
  accountId?: string
  positions: Position[]
  openOrders: ProjectXOrder[]
  recentOrders: ProjectXOrder[]
  onRefresh: () => void
}

type TabId = 'positions' | 'pending' | 'previous'

const orderTypeMap: Record<number, string> = {
  1: 'LIMIT',
  2: 'MARKET',
  4: 'STOP',
  5: 'TRAIL',
}

const orderSideMap: Record<number, string> = {
  0: 'BUY',
  1: 'SELL',
}

export default function ALGOXPositionsTable({
  accountId,
  positions,
  openOrders,
  recentOrders,
  onRefresh,
}: ALGOXPositionsTableProps) {
  const [activeTab, setActiveTab] = useState<TabId>('positions')
  const [flattening, setFlattening] = useState<boolean>(false)

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

  const positionTotals = useMemo(() => {
    // Calculate totals from positions - use API values directly
    const totalUnrealized = positions.reduce((sum, position) => {
      // Use API value if available, otherwise calculate with correct multiplier
      let pnl: number
      if (typeof position.unrealized_pnl === 'number' && Number.isFinite(position.unrealized_pnl)) {
        pnl = position.unrealized_pnl
      } else if (position.current_price && position.entry_price && position.quantity) {
        const priceMultiplier = getPriceMultiplier(position)
        const direction = position.side === 'LONG' ? 1 : -1
        const priceDiff = position.current_price - position.entry_price
        pnl = priceDiff * priceMultiplier * Math.abs(position.quantity) * direction
      } else {
        pnl = 0
      }
      
      // Debug logging in development
      if (process.env.NODE_ENV === 'development' && positions.length > 0) {
        console.log('[PositionsTable] Position P&L:', {
          symbol: position.symbol,
          unrealized_pnl: position.unrealized_pnl,
          calculated: pnl,
          current_price: position.current_price,
          entry_price: position.entry_price,
          quantity: position.quantity,
          side: position.side,
          point_value: position.point_value,
          tick_value: position.tick_value,
          tick_size: position.tick_size,
          price_multiplier: getPriceMultiplier(position)
        })
      }
      
      return sum + pnl
    }, 0)
    
    // Realized P&L is from closed trades, so sum it up
    const totalRealized = positions.reduce((sum, position) => {
      const realized = position.realized_pnl
      return sum + (typeof realized === 'number' ? realized : 0)
    }, 0)
    
    // Use entry_value from API, or calculate if not provided (with correct multiplier)
    const totalExposure = positions.reduce((sum, position) => {
      if (typeof position.entry_value === 'number' && Number.isFinite(position.entry_value)) {
        return sum + position.entry_value
      }
      if (position.entry_price && position.quantity) {
        const priceMultiplier = getPriceMultiplier(position)
        return sum + (position.entry_price * Math.abs(position.quantity) * priceMultiplier)
      }
      return sum
    }, 0)
    
    return {
      totalUnrealized,
      totalRealized,
      totalExposure,
    }
  }, [positions])

  const handleFlatten = async () => {
    if (!accountId) return
    setFlattening(true)
    try {
      await api.post(`/api/trading/accounts/${accountId}/flatten`)
      onRefresh()
    } catch (error: any) {
      console.error('Flatten failed', error)
    } finally {
      setFlattening(false)
    }
  }

  const formatTime = (timestamp?: string) => {
    if (!timestamp) return '--'
    return new Date(timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const resolveSide = (side: string | number | undefined) => {
    if (typeof side === 'number') return orderSideMap[side] ?? String(side)
    return side ?? '--'
  }

  const resolveType = (type: string | number | undefined) => {
    if (typeof type === 'number') return orderTypeMap[type] ?? String(type)
    return type ?? '--'
  }

  const formatValue = (value?: number, fractionDigits = 2) => {
    if (typeof value !== 'number' || Number.isNaN(value)) {
      return '--'
    }
    // Always show 0 values, don't hide them
    return value.toLocaleString('en-US', {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    })
  }

  const getPnlStyles = (value?: number) => {
    if (typeof value !== 'number' || Number.isNaN(value)) {
      return { className: 'text-gray-400', style: {} as CSSProperties }
    }
    const positive = value >= 0
    const intensity = Math.min(Math.abs(value) / 1000, 1)
    const color = positive ? `rgba(34,197,94,${0.4 + intensity * 0.6})` : `rgba(248,113,113,${0.4 + intensity * 0.6})`
    return {
      className: positive ? 'font-semibold' : 'font-semibold',
      style: { color },
    }
  }

  return (
    <div className="h-64 bg-[#0a0a0a] border-t border-[#1a1a1a] flex flex-col">
      <div className="grid grid-cols-3 gap-4 border-b border-[#1a1a1a] px-4 py-3 text-sm bg-[#0f0f0f]">
        <div>
          <div className="text-xs text-gray-400 uppercase mb-1">Unrealized P&L</div>
          <div {...getPnlStyles(positionTotals.totalUnrealized)} className="text-lg font-bold">
            {typeof positionTotals.totalUnrealized === 'number' 
              ? `${positionTotals.totalUnrealized >= 0 ? '+' : ''}${formatValue(positionTotals.totalUnrealized)}`
              : formatValue(0)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 uppercase mb-1">Realized P&L</div>
          <div {...getPnlStyles(positionTotals.totalRealized)} className="text-lg font-bold">
            {typeof positionTotals.totalRealized === 'number'
              ? `${positionTotals.totalRealized >= 0 ? '+' : ''}${formatValue(positionTotals.totalRealized)}`
              : formatValue(0)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 uppercase mb-1">Exposure</div>
          <div className="font-bold text-white text-lg">
            {typeof positionTotals.totalExposure === 'number' ? formatValue(positionTotals.totalExposure) : formatValue(0)}
          </div>
        </div>
      </div>
      <div className="flex border-b border-[#1a1a1a]">
        <button
          className={`flex-1 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'positions'
              ? 'border-blue-600 text-blue-400 bg-[#1a1a1a]'
              : 'border-transparent text-gray-400 hover:text-white hover:bg-[#0f0f0f]'
          }`}
          onClick={() => setActiveTab('positions')}
        >
          ACTIVE POSITIONS ({positions.length})
        </button>
        <button
          className={`flex-1 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'pending'
              ? 'border-blue-600 text-blue-400 bg-[#1a1a1a]'
              : 'border-transparent text-gray-400 hover:text-white hover:bg-[#0f0f0f]'
          }`}
          onClick={() => setActiveTab('pending')}
        >
          PENDING ORDERS ({openOrders.length})
        </button>
        <button
          className={`flex-1 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'previous'
              ? 'border-blue-600 text-blue-400 bg-[#1a1a1a]'
              : 'border-transparent text-gray-400 hover:text-white hover:bg-[#0f0f0f]'
          }`}
          onClick={() => setActiveTab('previous')}
        >
          RECENT ORDERS ({recentOrders.length})
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        {activeTab === 'positions' && (
          <table className="w-full text-xs">
            <thead className="bg-[#1a1a1a] sticky top-0">
              <tr className="text-left text-gray-400 border-b border-[#2a2a2a]">
                <th className="px-4 py-2 font-semibold">TIME</th>
                <th className="px-4 py-2 font-semibold">SYMBOL</th>
                <th className="px-4 py-2 font-semibold">SIDE</th>
                <th className="px-4 py-2 font-semibold">SIZE</th>
                <th className="px-4 py-2 font-semibold">ENTRY</th>
                <th className="px-4 py-2 font-semibold">CURRENT</th>
                <th className="px-4 py-2 font-semibold">P&L %</th>
                <th className="px-4 py-2 font-semibold text-right">UNREALIZED</th>
                <th className="px-4 py-2 font-semibold text-right">REALIZED</th>
                <th className="px-4 py-2 font-semibold text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {positions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-gray-500">
                    No active positions
                  </td>
                </tr>
              ) : (
                positions.map((position, idx) => {
                  // Use API values directly, calculate if missing (with correct multiplier)
                  let unrealized: number
                  if (typeof position.unrealized_pnl === 'number' && Number.isFinite(position.unrealized_pnl)) {
                    unrealized = position.unrealized_pnl
                  } else if (position.current_price && position.entry_price && position.quantity) {
                    const priceMultiplier = getPriceMultiplier(position)
                    const direction = position.side === 'LONG' ? 1 : -1
                    const priceDiff = position.current_price - position.entry_price
                    unrealized = priceDiff * priceMultiplier * Math.abs(position.quantity) * direction
                  } else {
                    unrealized = 0
                  }
                  
                  // Realized P&L comes from closed trades (includes commissions)
                  // For open positions, this will be null/undefined, which is correct
                  const realized = typeof position.realized_pnl === 'number' ? position.realized_pnl : null
                  
                  // Calculate P&L percentage if not provided
                  let entryValue: number
                  if (typeof position.entry_value === 'number' && Number.isFinite(position.entry_value)) {
                    entryValue = position.entry_value
                  } else if (position.entry_price && position.quantity) {
                    const priceMultiplier = getPriceMultiplier(position)
                    entryValue = position.entry_price * Math.abs(position.quantity) * priceMultiplier
                  } else {
                    entryValue = 0
                  }
                  const pnlPercent = typeof position.pnl_percent === 'number' && Number.isFinite(position.pnl_percent)
                    ? position.pnl_percent
                    : (entryValue ? (unrealized / entryValue) * 100 : 0)
                  
                  const pnlStyles = getPnlStyles(unrealized)
                  return (
                    <tr
                      key={position.position_id ?? idx}
                      className="border-b border-[#1a1a1a] hover:bg-[#1a1a1a]"
                      title={`Entry: ${formatValue(position.entry_value)} | Current: ${formatValue(position.current_value)}`}
                    >
                      <td className="px-4 py-2 text-gray-300">{formatTime(position.entry_time)}</td>
                      <td className="px-4 py-2 text-white font-medium">{position.symbol}</td>
                      <td className={`px-4 py-2 font-semibold ${position.side === 'LONG' ? 'text-green-500' : 'text-red-500'}`}>
                        {position.side}
                      </td>
                      <td className="px-4 py-2 text-white">{position.quantity}</td>
                      <td className="px-4 py-2 text-white">{formatValue(position.entry_price)}</td>
                      <td className="px-4 py-2 text-white">{formatValue(position.current_price)}</td>
                      <td className={`px-4 py-2 ${pnlStyles.className}`} style={pnlStyles.style}>
                        {typeof pnlPercent === 'number' ? `${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%` : '--'}
                      </td>
                      <td className={`px-4 py-2 text-right ${pnlStyles.className}`} style={pnlStyles.style}>
                        {typeof unrealized === 'number' ? `${unrealized >= 0 ? '+' : ''}${formatValue(unrealized)}` : '--'}
                      </td>
                      <td className={`px-4 py-2 text-right ${realized !== null ? (realized >= 0 ? 'text-green-500' : 'text-red-500') : 'text-gray-300'}`}>
                        {realized !== null ? formatValue(realized) : '--'}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={async () => {
                            if (!accountId || !position.position_id) return
                            setFlattening(true)
                            try {
                              // Close individual position by placing opposite order
                              await api.post('/api/trading/place-order', {
                                account_id: Number(accountId),
                                symbol: position.symbol,
                                side: position.side === 'LONG' ? 'SELL' : 'BUY',
                                order_type: 'MARKET',
                                quantity: position.quantity,
                                time_in_force: 'DAY',
                              })
                              onRefresh()
                            } catch (error: any) {
                              console.error('Failed to close position:', error)
                              alert(error?.response?.data?.detail || error?.message || 'Failed to close position')
                            } finally {
                              setFlattening(false)
                            }
                          }}
                          disabled={flattening || !accountId}
                          className="px-3 py-1.5 bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#2a2a2a] rounded text-xs text-white disabled:opacity-50 transition-colors"
                          title="Close this position"
                        >
                          {flattening ? '...' : 'Close'}
                        </button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        )}

        {activeTab === 'pending' && (
          <table className="w-full text-xs">
            <thead className="bg-[#1a1a1a] sticky top-0">
              <tr className="text-left text-gray-400 border-b border-[#2a2a2a]">
                <th className="px-4 py-2 font-semibold">TIME</th>
                <th className="px-4 py-2 font-semibold">SYMBOL</th>
                <th className="px-4 py-2 font-semibold">SIDE</th>
                <th className="px-4 py-2 font-semibold">TYPE</th>
                <th className="px-4 py-2 font-semibold">QTY</th>
                <th className="px-4 py-2 font-semibold text-right">STATUS</th>
              </tr>
            </thead>
            <tbody>
              {openOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-500">
                    No pending orders
                  </td>
                </tr>
              ) : (
                openOrders.map((order, idx) => (
                  <tr key={order.orderId ?? idx} className="border-b border-[#1a1a1a] hover:bg-[#1a1a1a]">
                    <td className="px-4 py-2 text-gray-300">{formatTime(order.creationTimestamp)}</td>
                    <td className="px-4 py-2 text-white">{order.contractId ?? order.symbolId ?? '--'}</td>
                    <td className={`px-4 py-2 font-semibold ${resolveSide(order.side) === 'BUY' ? 'text-green-500' : 'text-red-500'}`}>
                      {resolveSide(order.side)}
                    </td>
                    <td className="px-4 py-2 text-white">{resolveType(order.type)}</td>
                    <td className="px-4 py-2 text-white">{order.size ?? '--'}</td>
                    <td className="px-4 py-2 text-right text-gray-300">{order.status ?? '--'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {activeTab === 'previous' && (
          <table className="w-full text-xs">
            <thead className="bg-[#1a1a1a] sticky top-0">
              <tr className="text-left text-gray-400 border-b border-[#2a2a2a]">
                <th className="px-4 py-2 font-semibold">TIME</th>
                <th className="px-4 py-2 font-semibold">SYMBOL</th>
                <th className="px-4 py-2 font-semibold">SIDE</th>
                <th className="px-4 py-2 font-semibold">TYPE</th>
                <th className="px-4 py-2 font-semibold">QTY</th>
                <th className="px-4 py-2 font-semibold text-right">STATUS</th>
              </tr>
            </thead>
            <tbody>
              {recentOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-500">
                    No recent orders
                  </td>
                </tr>
              ) : (
                recentOrders.map((order, idx) => (
                  <tr key={`${order.orderId ?? idx}-recent`} className="border-b border-[#1a1a1a] hover:bg-[#1a1a1a]">
                    <td className="px-4 py-2 text-gray-300">{formatTime(order.updateTimestamp ?? order.creationTimestamp)}</td>
                    <td className="px-4 py-2 text-white">{order.contractId ?? order.symbolId ?? '--'}</td>
                    <td className={`px-4 py-2 font-semibold ${resolveSide(order.side) === 'BUY' ? 'text-green-500' : 'text-red-500'}`}>
                      {resolveSide(order.side)}
                    </td>
                    <td className="px-4 py-2 text-white">{resolveType(order.type)}</td>
                    <td className="px-4 py-2 text-white">{order.size ?? '--'}</td>
                    <td className="px-4 py-2 text-right text-gray-300">{order.status ?? '--'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

