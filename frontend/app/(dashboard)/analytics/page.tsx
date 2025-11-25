'use client'

import { useState, useMemo } from 'react'
import Sidebar from '@/components/Sidebar'
import Header from '@/components/Header'
import AccountSelector from '@/components/AccountSelector'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useSharedTradingState } from '@/hooks/useSharedTradingState'
import { useContracts } from '@/contexts/ContractsContext'
import api from '@/lib/api'

export default function AnalyticsPage() {
  const { data: dashboardData } = useDashboardData({ pollInterval: 10000 })
  const sharedState = useSharedTradingState()
  const { contracts, isValidSymbol } = useContracts()
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null)
  const [backtestRunning, setBacktestRunning] = useState(false)
  const [backtestResults, setBacktestResults] = useState<any>(null)
  const [startDate, setStartDate] = useState(
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  )
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0])
  const [timeframe, setTimeframe] = useState('5m')
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  // Get available symbols from contracts
  const availableSymbols = useMemo(() => {
    return contracts.map(c => c.symbol || '').filter(Boolean)
  }, [contracts])

  const totalBalance =
    sharedState.accountBalance ||
    dashboardData?.projectx?.accounts?.reduce((sum, acc) => sum + (acc.balance || 0), 0) ||
    0

  const handleRunBacktest = async () => {
    if (!selectedAccount) {
      setError('Please select an account')
      return
    }

    if (selectedSymbols.length === 0) {
      setError('Please select at least one symbol')
      return
    }

    // Validate all selected symbols
    const invalidSymbols = selectedSymbols.filter(s => !isValidSymbol(s))
    if (invalidSymbols.length > 0) {
      setError(`Invalid symbols: ${invalidSymbols.join(', ')}`)
      return
    }

    setBacktestRunning(true)
    setError(null)
    setBacktestResults(null)
    try {
      const response = await api.post('/api/backtest/run', {
        account_ids: [selectedAccount],
        symbols: selectedSymbols,
        timeframe,
        start_date: startDate,
        end_date: endDate,
      })

      setBacktestResults(response.data.results || response.data)
    } catch (err: any) {
      console.error('Error running backtest:', err)
      setError(err?.response?.data?.detail || err?.message || 'Error running backtest')
    } finally {
      setBacktestRunning(false)
    }
  }

  return (
    <div className="flex h-screen bg-dark-bg text-dark-text">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header accountBalance={totalBalance} />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mb-4">
            <h1 className="text-2xl font-bold mb-2">Analytics & Backtesting</h1>
            <p className="text-dark-text-muted">
              Run deep backtests using ProjectX API historical data
            </p>
          </div>

          <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
            <h2 className="text-lg font-semibold mb-4">Deep Backtesting</h2>

            <AccountSelector
              selectedAccount={selectedAccount}
              onAccountChange={setSelectedAccount}
            />

            {error && (
              <div className="mb-4 p-3 bg-red-500/20 text-red-400 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div className="mb-4">
              <label className="block text-sm mb-2">Symbols (select from available contracts)</label>
              <div className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  {availableSymbols.map((sym) => (
                    <label key={sym} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedSymbols.includes(sym)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedSymbols([...selectedSymbols, sym])
                          } else {
                            setSelectedSymbols(selectedSymbols.filter(s => s !== sym))
                          }
                        }}
                        className="rounded"
                      />
                      <span className="text-sm">{sym}</span>
                    </label>
                  ))}
                </div>
                {selectedSymbols.length > 0 && (
                  <div className="text-xs text-gray-400">
                    Selected: {selectedSymbols.join(', ')}
                  </div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm mb-2">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm mb-2">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
                />
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm mb-2">Timeframe</label>
              <select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
              >
                <option value="1m">1 Minute</option>
                <option value="5m">5 Minute</option>
                <option value="15m">15 Minute</option>
                <option value="1h">1 Hour</option>
                <option value="4h">4 Hour</option>
                <option value="1d">1 Day</option>
              </select>
            </div>

            <button
              onClick={handleRunBacktest}
              disabled={backtestRunning || !selectedAccount}
              className="px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {backtestRunning ? 'Running Backtest...' : 'Run Deep Backtest'}
            </button>
          </div>

          {backtestResults && (
            <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
              <h2 className="text-lg font-semibold mb-4">Backtest Results</h2>
              <pre className="bg-dark-bg p-4 rounded text-sm overflow-auto">
                {JSON.stringify(backtestResults, null, 2)}
              </pre>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

