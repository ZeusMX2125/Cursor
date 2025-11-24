'use client'

import { useEffect, useMemo, useState } from 'react'
import TopBar from '@/components/TopBar'
import CandlestickChart from '@/components/CandlestickChart'
import ALGOXAccountPanel from '@/components/ALGOXAccountPanel'
import ALGOXOrderEntry from '@/components/ALGOXOrderEntry'
import ALGOXQuickStrategies from '@/components/ALGOXQuickStrategies'
import ALGOXPositionsTable from '@/components/ALGOXPositionsTable'
import { useDashboardData } from '@/hooks/useDashboardData'

export default function ALGOXTradingPage() {
  const { data, loading, error, refresh } = useDashboardData({ pollInterval: 7000 })
  const [selectedAccountId, setSelectedAccountId] = useState<string | undefined>()
  const [symbol, setSymbol] = useState('ESZ25')
  const [timeframe, setTimeframe] = useState('1m')
  const [currentPrice, setCurrentPrice] = useState(0)
  const [priceChange, setPriceChange] = useState(0)
  const [priceChangePercent, setPriceChangePercent] = useState(0)

  useEffect(() => {
    if (!selectedAccountId && data?.accounts?.length) {
      setSelectedAccountId(data.accounts[0].account_id)
    }
  }, [data, selectedAccountId])

  const selectedAccount = useMemo(
    () => data?.accounts.find((acct) => acct.account_id === selectedAccountId),
    [data, selectedAccountId]
  )

  const handlePriceUpdate = (price: number, change: number, changePercent: number) => {
    setCurrentPrice(price)
    setPriceChange(change)
    setPriceChangePercent(changePercent)
  }

  const instrumentName = useMemo(() => {
    // Map common symbols to full names
    const symbolMap: Record<string, string> = {
      ESZ25: 'E-mini S&P 500: December 2025',
      NQZ25: 'E-mini NASDAQ-100: December 2025',
      M2KZ5: 'Micro E-mini Russell 2000: December 2025',
    }
    return symbolMap[symbol] || ''
  }, [symbol])

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
          mdConnected={true}
          ordConnected={true}
          simMode={true}
        />

        {/* Chart area with price display */}
        <div className="flex-1 flex flex-col relative">
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
          />

          {/* Positions table */}
          <ALGOXPositionsTable account={selectedAccount} onRefresh={refresh} />
        </div>
      </div>

      {/* Right sidebar */}
      <div className="w-80 bg-[#0a0a0a] border-l border-[#1a1a1a] overflow-y-auto flex flex-col">
        <ALGOXAccountPanel
          accounts={data?.accounts ?? []}
          selectedAccountId={selectedAccountId}
          onSelectAccount={setSelectedAccountId}
          onRefresh={refresh}
          loading={loading}
        />
        <ALGOXOrderEntry account={selectedAccount} defaultSymbol={symbol} onOrderPlaced={refresh} />
        <ALGOXQuickStrategies account={selectedAccount} onRefresh={refresh} />
      </div>
    </div>
  )
}

