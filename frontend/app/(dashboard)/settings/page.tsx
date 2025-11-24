'use client'

import Sidebar from '@/components/Sidebar'
import Header from '@/components/Header'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useSharedTradingState } from '@/hooks/useSharedTradingState'

export default function SettingsPage() {
  const { data: dashboardData } = useDashboardData({ pollInterval: 10000 })
  const sharedState = useSharedTradingState()
  const totalBalance =
    sharedState.accountBalance ||
    dashboardData?.projectx?.accounts?.reduce((sum, acc) => sum + (acc.balance || 0), 0) ||
    0

  return (
    <div className="flex h-screen bg-dark-bg text-dark-text">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header accountBalance={totalBalance} />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-4">Settings</h1>
          <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
            <p className="text-dark-text-muted">Settings page coming soon...</p>
          </div>
        </main>
      </div>
    </div>
  )
}


