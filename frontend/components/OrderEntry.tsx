'use client'

import { useState } from 'react'

export default function OrderEntry() {
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market')
  const [quantity, setQuantity] = useState(1)
  const [autoClose, setAutoClose] = useState(true)

  const handleBuy = () => {
    // TODO: Implement buy order
    console.log('Buy order:', { orderType, quantity })
  }

  const handleSell = () => {
    // TODO: Implement sell order
    console.log('Sell order:', { orderType, quantity })
  }

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

      <div className="grid grid-cols-2 gap-3 mb-4">
        <button
          onClick={handleBuy}
          className="bg-success hover:bg-success/80 py-3 rounded-lg font-semibold"
        >
          BUY MKT
        </button>
        <button
          onClick={handleSell}
          className="bg-danger hover:bg-danger/80 py-3 rounded-lg font-semibold"
        >
          SELL MKT
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

