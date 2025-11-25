'use client'

import { useEffect, useState } from 'react'
import Sidebar from '@/components/Sidebar'
import Header from '@/components/Header'
import StatsCards from '@/components/StatsCards'
import PriceChart from '@/components/PriceChart'
import OrderEntry from '@/components/OrderEntry'
import ActivePositions from '@/components/ActivePositions'
import BotStatus from '@/components/BotStatus'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useSharedTradingState } from '@/hooks/useSharedTradingState'

export default function DashboardPage() {
  const { data: dashboardData, loading, error } = useDashboardData({ pollInterval: 5000 })
  const sharedState = useSharedTradingState()

  // Calculate aggregate stats from dashboard data
  const totalBalance =
    sharedState.accountBalance ||
    dashboardData?.projectx?.accounts?.reduce((sum, acc) => sum + (acc.balance || 0), 0) ||
    0
  const totalDailyPnl = sharedState.dailyPnl || dashboardData?.metrics?.dailyPnl || 0
  const totalTradesToday = sharedState.tradesToday || dashboardData?.metrics?.pendingOrders || 0
  const totalPositions = dashboardData?.metrics?.openPositions || sharedState.positions.length || 0

  // Calculate win rate from accounts if available
  const winRate = dashboardData?.accounts?.length
    ? dashboardData.accounts.reduce((sum, acc) => sum + (acc.metrics?.win_rate || 0), 0) / dashboardData.accounts.length
    : 0

  // Calculate drawdown (simplified - use first account's drawdown or 0)
  const drawdown = dashboardData?.accounts?.[0]?.metrics?.daily_pnl
    ? Math.min(0, dashboardData.accounts[0].metrics.daily_pnl)
    : 0

  return (
    <div className="flex h-screen bg-dark-bg text-dark-text">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header accountBalance={totalBalance} />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mb-4">
            <h1 className="text-2xl font-bold mb-2">Active Trades</h1>
            <p className="text-dark-text-muted">
              Welcome back, Trader. Market is <span className="text-success">OPEN</span>.
            </p>
          </div>

          {loading && !dashboardData ? (
            <div className="text-center py-8 text-dark-text-muted">
              <div className="animate-pulse">Loading dashboard data...</div>
            </div>
          ) : error ? (
            <div className="bg-red-500/20 border border-red-500/40 rounded-lg p-4 text-red-400">
              <div className="font-semibold mb-2">Error loading dashboard</div>
              <div className="text-sm">{error}</div>
            </div>
          ) : (
            <>
              <StatsCards
                dailyPnl={totalDailyPnl}
                winRate={sharedState.winRate || winRate}
                drawdown={sharedState.drawdown || drawdown}
                tradesToday={totalTradesToday}
              />

              <div className="grid grid-cols-2 gap-6 mt-6">
                <PriceChart />
                <OrderEntry />
              </div>

              <div className="grid grid-cols-2 gap-6 mt-6">
                <ActivePositions
                  positions={
                    (sharedState.positions.length
                      ? sharedState.positions
                      : dashboardData?.projectx?.positions || []
                    ).map((pos, idx) => ({
                      id: String(pos.position_id || pos.id || idx),
                      symbol: pos.symbol || '',
                      side: (pos.side === 'LONG' ? 'LONG' : 'SHORT') as 'LONG' | 'SHORT',
                      entry: pos.entry_price || 0,
                      pnl: pos.unrealized_pnl || 0,
                    }))
                  }
                />
                <BotStatus
                  strategy={dashboardData?.accounts?.[0]?.strategies?.active || 'None'}
                  riskLevel="Moderate"
                  targetPerDay={dashboardData?.accounts?.[0]?.profit_target || 0}
                  goalProgress={
                    dashboardData?.accounts?.[0]?.profit_target
                      ? Math.min(100, (Math.max(0, totalDailyPnl) / dashboardData.accounts[0].profit_target) * 100)
                      : 0
                  }
                />
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}

