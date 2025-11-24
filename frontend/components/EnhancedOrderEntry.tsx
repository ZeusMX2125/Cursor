'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import type { AccountSnapshot } from '@/types/dashboard'

interface EnhancedOrderEntryProps {
  account?: AccountSnapshot
  defaultSymbol: string
  onOrderPlaced: () => void
}

export default function EnhancedOrderEntry({ account, defaultSymbol, onOrderPlaced }: EnhancedOrderEntryProps) {
  const [symbol, setSymbol] = useState(defaultSymbol)
  const [orderType, setOrderType] = useState('MARKET')
  const [quantity, setQuantity] = useState(1)
  const [timeInForce, setTimeInForce] = useState('DAY')
  const [price, setPrice] = useState<string>('')
  const [stopLoss, setStopLoss] = useState<string>('')
  const [takeProfit, setTakeProfit] = useState<string>('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    setSymbol(defaultSymbol)
  }, [defaultSymbol])

  const submitOrder = async (side: 'BUY' | 'SELL') => {
    if (!account) {
      setMessage('Select an account to trade')
      return
    }
    setSubmitting(true)
    setMessage(null)
    try {
      await api.post('/api/trading/place-order', {
        account_id: account.account_id,
        symbol,
        side,
        order_type: orderType,
        quantity,
        time_in_force: timeInForce,
        price: price ? parseFloat(price) : undefined,
        stop_loss: stopLoss ? parseFloat(stopLoss) : undefined,
        take_profit: takeProfit ? parseFloat(takeProfit) : undefined,
      })
      setMessage(`${side} order submitted`)
      onOrderPlaced()
    } catch (error: any) {
      console.error('Order placement failed', error)
      setMessage(error?.message ?? 'Order failed')
    } finally {
      setSubmitting(false)
    }
  }

  const flattenPositions = async () => {
    if (!account) return
    setSubmitting(true)
    setMessage(null)
    try {
      await api.post(`/api/trading/accounts/${account.account_id}/flatten`)
      setMessage('Flatten request sent')
      onOrderPlaced()
    } catch (error: any) {
      setMessage(error?.message ?? 'Flatten failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm">Order Entry</h3>
          <p className="text-xs text-dark-text-muted">{account ? account.name : 'No account selected'}</p>
        </div>
        {submitting && <span className="text-xs text-dark-text-muted">Sending...</span>}
      </div>

      {message && <div className="text-xs text-primary">{message}</div>}

      <div>
        <label className="block text-xs text-dark-text-muted mb-1">Symbol</label>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm"
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-dark-text-muted mb-1">Order Type</label>
          <select value={orderType} onChange={(e) => setOrderType(e.target.value)} className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm">
            <option value="MARKET">Market</option>
            <option value="LIMIT">Limit</option>
            <option value="STOP">Stop</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-dark-text-muted mb-1">Contracts</label>
          <input
            type="number"
            min={1}
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
            className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm"
          />
        </div>
      </div>

      {orderType !== 'MARKET' && (
        <div>
          <label className="block text-xs text-dark-text-muted mb-1">Price</label>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm"
          />
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-dark-text-muted mb-1">Stop Loss</label>
          <input
            type="number"
            value={stopLoss}
            onChange={(e) => setStopLoss(e.target.value)}
            placeholder="ticks or price"
            className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-dark-text-muted mb-1">Take Profit</label>
          <input
            type="number"
            value={takeProfit}
            onChange={(e) => setTakeProfit(e.target.value)}
            placeholder="ticks or price"
            className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs text-dark-text-muted mb-1">Time in Force</label>
        <select value={timeInForce} onChange={(e) => setTimeInForce(e.target.value)} className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm">
          <option value="DAY">DAY</option>
          <option value="GTC">GTC</option>
          <option value="IOC">IOC</option>
        </select>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-2">
        <button onClick={() => submitOrder('BUY')} disabled={submitting} className="bg-success hover:bg-success/80 py-2 rounded font-semibold">
          BUY MKT
        </button>
        <button onClick={() => submitOrder('SELL')} disabled={submitting} className="bg-danger hover:bg-danger/80 py-2 rounded font-semibold">
          SELL MKT
        </button>
        <button onClick={flattenPositions} disabled={submitting || !account} className="bg-primary hover:bg-primary-hover py-2 rounded font-semibold">
          Close All Positions
        </button>
      </div>
    </div>
  )
}
