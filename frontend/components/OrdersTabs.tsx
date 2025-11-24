'use client'

import { useMemo, useState } from 'react'
import type { AccountSnapshot } from '@/types/dashboard'

interface OrdersTabsProps {
  account?: AccountSnapshot
}

type TabId = 'positions' | 'pending' | 'previous'

export default function OrdersTabs({ account }: OrdersTabsProps) {
  const [activeTab, setActiveTab] = useState<TabId>('positions')

  const positions = account?.positions ?? []
  const pendingOrders = account?.pending_orders ?? []
  const previousOrders = account?.manual_orders ?? []

  const summary = useMemo(() => {
    return {
      positions: positions.length,
      pending: pendingOrders.length,
      previous: previousOrders.length,
    }
  }, [positions, pendingOrders, previousOrders])

  const renderPositions = () => {
    if (!positions.length) {
      return <div className="text-center text-dark-text-muted py-6">No active positions</div>
    }
    return (
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-dark-text-muted border-b border-dark-border">
            <th className="py-2">Symbol</th>
            <th className="py-2">Side</th>
            <th className="py-2">Size</th>
            <th className="py-2">Entry</th>
            <th className="py-2">Last</th>
            <th className="py-2 text-right">Unrealized</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => (
            <tr key={position.position_id ?? `${position.symbol}-${position.entry_price}`} className="border-b border-dark-border">
              <td className="py-2">{position.symbol}</td>
              <td className="py-2">{position.side}</td>
              <td className="py-2">{position.quantity}</td>
              <td className="py-2">{position.entry_price?.toFixed(2)}</td>
              <td className="py-2">{position.current_price?.toFixed(2) ?? '--'}</td>
              <td className={`py-2 text-right font-semibold ${position.unrealized_pnl && position.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                {position.unrealized_pnl?.toFixed(2) ?? '--'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  const renderPendingOrders = () => {
    if (!pendingOrders.length) {
      return <div className="text-center text-dark-text-muted py-6">No pending orders</div>
    }
    return (
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-dark-text-muted border-b border-dark-border">
            <th className="py-2">Time</th>
            <th className="py-2">Symbol</th>
            <th className="py-2">Side</th>
            <th className="py-2">Type</th>
            <th className="py-2">Qty</th>
            <th className="py-2 text-right">Status</th>
          </tr>
        </thead>
        <tbody>
          {pendingOrders.map((order) => (
            <tr key={order.order_id} className="border-b border-dark-border">
              <td className="py-2">{order.created_at ? new Date(order.created_at).toLocaleTimeString() : '--'}</td>
              <td className="py-2">{order.symbol}</td>
              <td className="py-2">{order.side}</td>
              <td className="py-2">{order.order_type}</td>
              <td className="py-2">{order.quantity}</td>
              <td className="py-2 text-right">{order.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  const renderPreviousOrders = () => {
    if (!previousOrders.length) {
      return <div className="text-center text-dark-text-muted py-6">No submitted orders</div>
    }
    return (
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-dark-text-muted border-b border-dark-border">
            <th className="py-2">Timestamp</th>
            <th className="py-2">Symbol</th>
            <th className="py-2">Side</th>
            <th className="py-2">Type</th>
            <th className="py-2">Qty</th>
            <th className="py-2 text-right">Status</th>
          </tr>
        </thead>
        <tbody>
          {previousOrders.map((order) => (
            <tr key={order.order_id} className="border-b border-dark-border">
              <td className="py-2">{order.timestamp ? new Date(order.timestamp).toLocaleString() : '--'}</td>
              <td className="py-2">{order.symbol}</td>
              <td className="py-2">{order.side}</td>
              <td className="py-2">{order.order_type}</td>
              <td className="py-2">{order.quantity}</td>
              <td className="py-2 text-right">{order.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'positions':
        return renderPositions()
      case 'pending':
        return renderPendingOrders()
      case 'previous':
        return renderPreviousOrders()
      default:
        return null
    }
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg h-full flex flex-col">
      <div className="flex border-b border-dark-border">
        <button
          className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 ${
            activeTab === 'positions' ? 'border-primary text-primary' : 'border-transparent text-dark-text-muted'
          }`}
          onClick={() => setActiveTab('positions')}
        >
          Active Positions ({summary.positions})
        </button>
        <button
          className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 ${
            activeTab === 'pending' ? 'border-primary text-primary' : 'border-transparent text-dark-text-muted'
          }`}
          onClick={() => setActiveTab('pending')}
        >
          Pending Orders ({summary.pending})
        </button>
        <button
          className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 ${
            activeTab === 'previous' ? 'border-primary text-primary' : 'border-transparent text-dark-text-muted'
          }`}
          onClick={() => setActiveTab('previous')}
        >
          Previous Orders ({summary.previous})
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">{renderActiveTab()}</div>
    </div>
  )
}
