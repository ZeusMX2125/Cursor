'use client'

import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import Header from '@/components/Header'
import AccountSelector from '@/components/AccountSelector'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useSharedTradingState } from '@/hooks/useSharedTradingState'
import api from '@/lib/api'

export default function AnalyticsPage() {
  const { data: dashboardData } = useDashboardData({ pollInterval: 10000 })
  const sharedState = useSharedTradingState()
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null)
  const [backtestRunning, setBacktestRunning] = useState(false)
  const [backtestResults, setBacktestResults] = useState<any>(null)

  const totalBalance =
    sharedState.accountBalance ||
    dashboardData?.projectx?.accounts?.reduce((sum, acc) => sum + (acc.balance || 0), 0) ||
    0

  const handleRunBacktest = async () => {
    if (!selectedAccount) {
      alert('Please select an account')
      return
    }

    setBacktestRunning(true)
    try {
      const response = await api.post('/api/backtest/run', {
        account_ids: [selectedAccount],
        symbols: ['MNQ', 'MES', 'MGC'],
        timeframe: '5m',
        start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        end_date: new Date().toISOString().split('T')[0],
      })

      setBacktestResults(response.data.results)
    } catch (error) {
      console.error('Error running backtest:', error)
      alert('Error running backtest')
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

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm mb-2">Start Date</label>
                <input
                  type="date"
                  defaultValue={new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}
                  className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm mb-2">End Date</label>
                <input
                  type="date"
                  defaultValue={new Date().toISOString().split('T')[0]}
                  className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
                />
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm mb-2">Timeframe</label>
              <select className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2">
                <option value="1m">1 Minute</option>
                <option value="5m" selected>5 Minute</option>
                <option value="15m">15 Minute</option>
                <option value="1h">1 Hour</option>
              </select>
            </div>

            <button
              onClick={handleRunBacktest}
              disabled={backtestRunning || !selectedAccount}
              className="px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg disabled:opacity-50"
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

