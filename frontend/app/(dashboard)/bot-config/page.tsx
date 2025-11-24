'use client'

import { useState } from 'react'
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

  const handleSave = async () => {
    // TODO: Implement API call to save config
    console.log('Saving config:', config)
  }

  const handleStart = async () => {
    // TODO: Implement API call to start engine
    console.log('Starting engine')
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
            <div className="flex gap-4">
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg flex items-center gap-2"
              >
                <span>💾</span> Save Config
              </button>
              <button
                onClick={handleStart}
                className="px-4 py-2 bg-success hover:bg-success/80 rounded-lg flex items-center gap-2"
              >
                <span>▶️</span> Start Engine
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

