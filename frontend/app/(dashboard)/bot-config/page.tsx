'use client'

import { useState } from 'react'
import api from '@/lib/api'
import Sidebar from '@/components/Sidebar'
import Header from '@/components/Header'
import AccountSelector from '@/components/AccountSelector'
import StrategyParams from '@/components/BotConfig/StrategyParams'
import RiskManagement from '@/components/BotConfig/RiskManagement'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useSharedTradingState } from '@/hooks/useSharedTradingState'

export default function BotConfigPage() {
  const { data: dashboardData } = useDashboardData({ pollInterval: 10000 })
  const sharedState = useSharedTradingState()
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null)

  const totalBalance =
    sharedState.accountBalance ||
    dashboardData?.projectx?.accounts?.reduce((sum, acc) => sum + (acc.balance || 0), 0) ||
    0
  const [config, setConfig] = useState({
    strategyType: 'momentum_scalp',
    timeframe: '1m',
    contracts: 2,
    longEntries: true,
    shortEntries: true,
    maxDailyLoss: 500,
    dailyProfitTarget: 1000,
    maxDrawdown: 2.5,
    trailingStop: 12,
  })

  const [saving, setSaving] = useState(false)
  const [starting, setStarting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const handleSave = async () => {
    if (!selectedAccount) {
      setMessage('Please select an account first')
      return
    }
    setSaving(true)
    setMessage(null)
    try {
      await api.post('/api/config/save', {
        account_id: selectedAccount,
        strategy_settings: {
          strategy_type: config.strategyType,
          timeframe: config.timeframe,
          contracts: config.contracts,
          long_entries: config.longEntries,
          short_entries: config.shortEntries,
        },
        risk_settings: {
          max_daily_loss: config.maxDailyLoss,
          daily_profit_target: config.dailyProfitTarget,
          max_drawdown: config.maxDrawdown,
          trailing_stop: config.trailingStop,
        }
      })
      setMessage('Configuration saved successfully')
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || error?.message || 'Failed to save config')
    } finally {
      setSaving(false)
    }
  }

  const handleStart = async () => {
    if (!selectedAccount) {
      setMessage('Please select an account first')
      return
    }
    setStarting(true)
    setMessage(null)
    try {
      // First save config, then start
      await handleSave()
      await api.post(`/api/accounts/${selectedAccount}/start`)
      setMessage('Engine started successfully')
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || error?.message || 'Failed to start engine')
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="flex h-screen bg-dark-bg text-dark-text">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header accountBalance={totalBalance} />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mb-4">
            <h1 className="text-2xl font-bold mb-2">Bot Config</h1>
            <p className="text-dark-text-muted">
              Welcome back, Trader. Market is <span className="text-success">OPEN</span>.
            </p>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-2">Bot Configuration</h2>
            <p className="text-dark-text-muted mb-4">
              Manage your automated trading strategies and risk parameters.
            </p>

            <AccountSelector
              selectedAccount={selectedAccount}
              onAccountChange={setSelectedAccount}
            />
            {message && (
              <div className={`mb-4 p-3 rounded-lg text-sm ${
                message.includes('success') ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
              }`}>
                {message}
              </div>
            )}
            <div className="flex gap-4">
              <button
                onClick={handleSave}
                disabled={saving || !selectedAccount}
                className="px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span>💾</span> {saving ? 'Saving...' : 'Save Config'}
              </button>
              <button
                onClick={handleStart}
                disabled={starting || !selectedAccount}
                className="px-4 py-2 bg-success hover:bg-success/80 rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span>▶️</span> {starting ? 'Starting...' : 'Start Engine'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <StrategyParams config={config} setConfig={setConfig} />
            <RiskManagement config={config} setConfig={setConfig} />
          </div>
        </main>
      </div>
    </div>
  )
}

