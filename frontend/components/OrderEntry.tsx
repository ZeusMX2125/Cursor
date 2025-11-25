'use client'

import { useState, useEffect } from 'react'
import api from '@/lib/api'
import { useDashboardData } from '@/hooks/useDashboardData'
import InstrumentSelector from '@/components/InstrumentSelector'
import { useContracts } from '@/contexts/ContractsContext'

export default function OrderEntry() {
  const { data } = useDashboardData({ pollInterval: 10000 })
  const { contracts, getFirstContract, loading: contractsLoading, isValidSymbol } = useContracts()
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market')
  const [quantity, setQuantity] = useState(1)
  const [autoClose, setAutoClose] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [symbol, setSymbol] = useState<string>('')

  // Initialize symbol from first available ProjectX contract
  useEffect(() => {
    if (!contractsLoading && contracts.length > 0 && !symbol) {
      const firstContract = getFirstContract()
      if (firstContract?.symbol) {
        setSymbol(firstContract.symbol)
      }
    }
  }, [contractsLoading, contracts, symbol, getFirstContract])

  const selectedAccount = data?.projectx?.accounts?.[0]
  const accountId = selectedAccount?.id

  const handleOrder = async (side: 'BUY' | 'SELL') => {
    if (!accountId) {
      setMessage('No account available')
      return
    }
    if (!symbol || !isValidSymbol(symbol)) {
      setMessage('Invalid symbol. Please select a valid contract.')
      return
    }
    setSubmitting(true)
    setMessage(null)
    try {
      await api.post('/api/trading/place-order', {
        account_id: Number(accountId),
        symbol,
        side,
        order_type: orderType.toUpperCase(),
        quantity,
        time_in_force: 'DAY',
      })
      setMessage(`${side} order submitted`)
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || error?.message || 'Order failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleBuy = () => handleOrder('BUY')
  const handleSell = () => handleOrder('SELL')

  return (
    <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
      <div className="text-lg font-semibold mb-4">ORDER ENTRY</div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setOrderType('market')}
          className={`flex-1 py-2 rounded ${
            orderType === 'market'
              ? 'bg-primary text-white'
              : 'bg-dark-border text-dark-text-muted'
          }`}
        >
          Market
        </button>
        <button
          onClick={() => setOrderType('limit')}
          className={`flex-1 py-2 rounded ${
            orderType === 'limit'
              ? 'bg-primary text-white'
              : 'bg-dark-border text-dark-text-muted'
          }`}
        >
          Limit
        </button>
      </div>

      <div className="mb-4">
        <div className="text-xs text-dark-text-muted mb-1">MAX: 10</div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setQuantity(Math.max(1, quantity - 1))}
            className="w-8 h-8 bg-dark-border rounded flex items-center justify-center hover:bg-dark-border/80"
          >
            -
          </button>
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
            className="flex-1 bg-dark-bg border border-dark-border rounded px-3 py-2 text-center"
            min={1}
            max={10}
          />
          <button
            onClick={() => setQuantity(Math.min(10, quantity + 1))}
            className="w-8 h-8 bg-dark-border rounded flex items-center justify-center hover:bg-dark-border/80"
          >
            +
          </button>
        </div>
      </div>

      {message && (
        <div className={`mb-4 p-2 rounded text-xs ${
          message.includes('submitted') ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
        }`}>
          {message}
        </div>
      )}

      <div className="mb-4">
        <label className="block text-xs text-dark-text-muted mb-1">Symbol</label>
        <InstrumentSelector
          value={symbol}
          onChange={setSymbol}
          disabled={submitting || contractsLoading}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <button
          onClick={handleBuy}
          disabled={submitting || !accountId}
          className="bg-success hover:bg-success/80 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
        >
          BUY {orderType.toUpperCase()}
        </button>
        <button
          onClick={handleSell}
          disabled={submitting || !accountId}
          className="bg-danger hover:bg-danger/80 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
        >
          SELL {orderType.toUpperCase()}
        </button>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-dark-border">
        <div>
          <div className="text-sm font-medium">Auto-Close</div>
          <div className="text-xs text-dark-text-muted">Close all at 3:45 PM</div>
        </div>
        <button
          onClick={() => setAutoClose(!autoClose)}
          className={`w-12 h-6 rounded-full transition-colors ${
            autoClose ? 'bg-primary' : 'bg-dark-border'
          }`}
        >
          <div
            className={`w-5 h-5 bg-white rounded-full transition-transform ${
              autoClose ? 'translate-x-6' : 'translate-x-0.5'
            }`}
          />
        </button>
      </div>
    </div>
  )
}

