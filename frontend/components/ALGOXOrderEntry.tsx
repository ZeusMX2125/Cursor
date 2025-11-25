'use client'

import { useState, useEffect, useMemo } from 'react'
import api from '@/lib/api'
import InstrumentSelector from '@/components/InstrumentSelector'
import { useContracts } from '@/contexts/ContractsContext'
import { formatSymbolForDisplay } from '@/lib/contractUtils'

interface ALGOXOrderEntryProps {
  accountId?: string
  accountName?: string
  defaultSymbol: string
  currentPrice?: number
  onOrderPlaced: () => void
}

export default function ALGOXOrderEntry({ accountId, accountName, defaultSymbol, currentPrice, onOrderPlaced }: ALGOXOrderEntryProps) {
  const { isValidSymbol, getContractBySymbol } = useContracts()
  const [symbol, setSymbol] = useState(defaultSymbol)
  const [symbolError, setSymbolError] = useState<string | null>(null)
  
  // Sync symbol when defaultSymbol changes from parent
  useEffect(() => {
    if (defaultSymbol && isValidSymbol(defaultSymbol)) {
      setSymbol(defaultSymbol)
      setSymbolError(null)
    }
  }, [defaultSymbol, isValidSymbol])
  
  const contract = useMemo(() => getContractBySymbol(symbol), [symbol, getContractBySymbol])
  const displaySymbol = useMemo(() => formatSymbolForDisplay(symbol, contract || undefined), [symbol, contract])
  const [orderType, setOrderType] = useState('Market')
  const [quantity, setQuantity] = useState(1)
  const [timeInForce, setTimeInForce] = useState('Day')
  const [bracketEnabled, setBracketEnabled] = useState(false)
  const [stopLoss, setStopLoss] = useState('10')
  const [takeProfit, setTakeProfit] = useState('20')
  const [trail, setTrail] = useState('None')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const submitOrder = async (side: 'BUY' | 'SELL') => {
    if (!accountId) {
      setMessage('Select an account to trade')
      return
    }
    if (!symbol || !isValidSymbol(symbol)) {
      setSymbolError('Invalid symbol. Please select a valid contract.')
      setMessage('Invalid symbol')
      return
    }
    setSymbolError(null)
    setSubmitting(true)
    setMessage(null)
    try {
      const response = await api.post('/api/trading/place-order', {
        account_id: Number(accountId),
        symbol,
        side,
        order_type: orderType.toUpperCase(),
        quantity,
        time_in_force: timeInForce.toUpperCase(),
        stop_loss: bracketEnabled && stopLoss ? parseFloat(stopLoss) : undefined,
        take_profit: bracketEnabled && takeProfit ? parseFloat(takeProfit) : undefined,
      })
      
      // Check for market hours warning
      const data = response.data || response
      if (data.market_warning) {
        setMessage(`${side} order submitted - ${data.market_warning}`)
        // Show notification for closed hours
        if (typeof window !== 'undefined') {
          setTimeout(() => {
            window.alert(data.market_warning)
          }, 100)
        }
      } else {
        setMessage(`${side} order submitted`)
      }
      onOrderPlaced()
    } catch (error: any) {
      console.error('Order placement failed', error)
      setMessage(error?.message ?? 'Order failed')
    } finally {
      setSubmitting(false)
    }
  }

  const flattenPositions = async () => {
    if (!accountId) return
    setSubmitting(true)
    setMessage(null)
    try {
      await api.post(`/api/trading/accounts/${accountId}/flatten`)
      setMessage('Flatten request sent')
      onOrderPlaced()
    } catch (error: any) {
      setMessage(error?.message ?? 'Flatten failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-[#0a0a0a] border-b border-[#1a1a1a] p-4 space-y-4" suppressHydrationWarning>
      <div>
        <h3 className="text-sm font-semibold text-white mb-4">ORDER ENTRY</h3>
        
        <div className="space-y-3.5" suppressHydrationWarning>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Account</label>
            <div className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1.5 text-sm text-white">
              {accountName || 'No account selected'}
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Contract</label>
            <div className="space-y-1">
              <InstrumentSelector
                value={symbol}
                onChange={(newSymbol) => {
                  setSymbol(newSymbol)
                  setSymbolError(null)
                }}
                className="w-full"
                disabled={submitting}
              />
              {symbolError && (
                <div className="text-xs text-red-400">{symbolError}</div>
              )}
              {currentPrice && currentPrice > 0 && !symbolError && (
                <div className="text-xs text-gray-400">
                  {displaySymbol} @ {currentPrice.toFixed(2)}
                </div>
              )}
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Order Type</label>
            <select
              value={orderType}
              onChange={(e) => setOrderType(e.target.value)}
              className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1.5 text-sm text-white"
            >
              <option>Market</option>
              <option>Limit</option>
              <option>Stop</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Size</label>
            <input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
              className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1.5 text-sm text-white"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">TIF</label>
            <select
              value={timeInForce}
              onChange={(e) => setTimeInForce(e.target.value)}
              className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1.5 text-sm text-white"
            >
              <option>Day</option>
              <option>GTC</option>
              <option>IOC</option>
            </select>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-gray-400">Bracket Orders</label>
              <button
                onClick={() => setBracketEnabled(!bracketEnabled)}
                className={`w-10 h-5 rounded-full transition-colors ${
                  bracketEnabled ? 'bg-blue-600' : 'bg-[#2a2a2a]'
                }`}
              >
                <div
                  className={`w-4 h-4 bg-white rounded-full transition-transform ${
                    bracketEnabled ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
            {bracketEnabled && (
              <div className="space-y-2 mt-2">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">SL (ticks)</label>
                  <input
                    type="number"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">TP (ticks)</label>
                  <input
                    type="number"
                    value={takeProfit}
                    onChange={(e) => setTakeProfit(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Trail</label>
                  <select
                    value={trail}
                    onChange={(e) => setTrail(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1 text-xs text-white"
                  >
                    <option>None</option>
                    <option>Trail</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {message && (
            <div className={`text-xs p-2 rounded ${
              message.includes('submitted') || message.includes('sent')
                ? 'bg-green-500/20 text-green-400'
                : 'bg-blue-500/20 text-blue-400'
            }`}>
              {message}
            </div>
          )}

          <div className="space-y-2.5 pt-3">
            <button
              onClick={() => submitOrder('BUY')}
              disabled={submitting}
              className="w-full bg-green-600 hover:bg-green-700 py-3 rounded font-semibold text-white disabled:opacity-50"
            >
              BUY MKT
            </button>
            <button
              onClick={() => submitOrder('SELL')}
              disabled={submitting}
              className="w-full bg-red-600 hover:bg-red-700 py-3 rounded font-semibold text-white disabled:opacity-50"
            >
              SELL MKT
            </button>
            <button
              onClick={flattenPositions}
              disabled={submitting || !accountId}
              className="w-full bg-purple-600 hover:bg-purple-700 py-2 rounded font-semibold text-white disabled:opacity-50"
              title={!accountId ? 'Select an account first' : 'Close all positions'}
            >
              Close All Positions
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

