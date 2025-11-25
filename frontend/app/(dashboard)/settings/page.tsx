'use client'

import { useState, useEffect } from 'react'
import Sidebar from '@/components/Sidebar'
import Header from '@/components/Header'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useSharedTradingState } from '@/hooks/useSharedTradingState'
import api from '@/lib/api'

export default function SettingsPage() {
  const { data: dashboardData } = useDashboardData({ pollInterval: 10000 })
  const sharedState = useSharedTradingState()
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  
  const totalBalance =
    sharedState.accountBalance ||
    dashboardData?.projectx?.accounts?.reduce((sum, acc) => sum + (acc.balance || 0), 0) ||
    0

  // Settings state
  const [settings, setSettings] = useState({
    notifications: {
      email: false,
      sms: false,
      push: true,
    },
    trading: {
      autoClose: true,
      closeTime: '15:45',
      maxPositions: 5,
    },
    risk: {
      maxDailyLoss: 500,
      dailyProfitTarget: 1000,
      maxDrawdown: 2.5,
    },
    api: {
      refreshInterval: 5000,
      websocketEnabled: true,
    }
  })

  useEffect(() => {
    // Load settings from localStorage or API
    const saved = localStorage.getItem('tradingBotSettings')
    if (saved) {
      try {
        setSettings(JSON.parse(saved))
      } catch (e) {
        console.error('Failed to load settings:', e)
      }
    }
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      // Save to localStorage
      localStorage.setItem('tradingBotSettings', JSON.stringify(settings))
      
      // Optionally save to backend
      try {
        await api.post('/api/config/save', {
          account_id: dashboardData?.projectx?.accounts?.[0]?.id,
          settings,
        })
      } catch (e) {
        // Backend save is optional
        console.log('Backend save optional:', e)
      }
      
      setMessage('Settings saved successfully')
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      setMessage(error?.message || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex h-screen bg-dark-bg text-dark-text">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header accountBalance={totalBalance} />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mb-6">
            <h1 className="text-2xl font-bold mb-2">Settings</h1>
            <p className="text-dark-text-muted">
              Configure your trading bot preferences and notifications
            </p>
          </div>

          {message && (
            <div className={`mb-6 p-4 rounded-lg ${
              message.includes('success') 
                ? 'bg-green-500/20 text-green-400 border border-green-500/40' 
                : 'bg-red-500/20 text-red-400 border border-red-500/40'
            }`}>
              {message}
            </div>
          )}

          <div className="space-y-6">
            {/* Notifications */}
            <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
              <h2 className="text-lg font-semibold mb-4">Notifications</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Email Notifications</div>
                    <div className="text-sm text-dark-text-muted">Receive trade alerts via email</div>
                  </div>
                  <button
                    onClick={() => setSettings({
                      ...settings,
                      notifications: { ...settings.notifications, email: !settings.notifications.email }
                    })}
                    className={`w-12 h-6 rounded-full transition-colors ${
                      settings.notifications.email ? 'bg-primary' : 'bg-dark-border'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full transition-transform ${
                        settings.notifications.email ? 'translate-x-6' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">SMS Notifications</div>
                    <div className="text-sm text-dark-text-muted">Receive critical alerts via SMS</div>
                  </div>
                  <button
                    onClick={() => setSettings({
                      ...settings,
                      notifications: { ...settings.notifications, sms: !settings.notifications.sms }
                    })}
                    className={`w-12 h-6 rounded-full transition-colors ${
                      settings.notifications.sms ? 'bg-primary' : 'bg-dark-border'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full transition-transform ${
                        settings.notifications.sms ? 'translate-x-6' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Push Notifications</div>
                    <div className="text-sm text-dark-text-muted">Browser push notifications</div>
                  </div>
                  <button
                    onClick={() => setSettings({
                      ...settings,
                      notifications: { ...settings.notifications, push: !settings.notifications.push }
                    })}
                    className={`w-12 h-6 rounded-full transition-colors ${
                      settings.notifications.push ? 'bg-primary' : 'bg-dark-border'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full transition-transform ${
                        settings.notifications.push ? 'translate-x-6' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>

            {/* Trading Settings */}
            <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
              <h2 className="text-lg font-semibold mb-4">Trading Settings</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Auto-Close Positions</div>
                    <div className="text-sm text-dark-text-muted">Automatically close all positions at market close</div>
                  </div>
                  <button
                    onClick={() => setSettings({
                      ...settings,
                      trading: { ...settings.trading, autoClose: !settings.trading.autoClose }
                    })}
                    className={`w-12 h-6 rounded-full transition-colors ${
                      settings.trading.autoClose ? 'bg-primary' : 'bg-dark-border'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full transition-transform ${
                        settings.trading.autoClose ? 'translate-x-6' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </div>

                {settings.trading.autoClose && (
                  <div>
                    <label className="block text-sm mb-2">Close Time (CT)</label>
                    <input
                      type="time"
                      value={settings.trading.closeTime}
                      onChange={(e) => setSettings({
                        ...settings,
                        trading: { ...settings.trading, closeTime: e.target.value }
                      })}
                      className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm mb-2">Max Concurrent Positions</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={settings.trading.maxPositions}
                    onChange={(e) => setSettings({
                      ...settings,
                      trading: { ...settings.trading, maxPositions: parseInt(e.target.value) || 1 }
                    })}
                    className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
                  />
                </div>
              </div>
            </div>

            {/* Risk Settings */}
            <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
              <h2 className="text-lg font-semibold mb-4">Risk Management</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm mb-2">Max Daily Loss ($)</label>
                  <input
                    type="number"
                    value={settings.risk.maxDailyLoss}
                    onChange={(e) => setSettings({
                      ...settings,
                      risk: { ...settings.risk, maxDailyLoss: parseFloat(e.target.value) || 0 }
                    })}
                    className="w-full bg-dark-bg border border-danger rounded px-3 py-2"
                  />
                </div>

                <div>
                  <label className="block text-sm mb-2">Daily Profit Target ($)</label>
                  <input
                    type="number"
                    value={settings.risk.dailyProfitTarget}
                    onChange={(e) => setSettings({
                      ...settings,
                      risk: { ...settings.risk, dailyProfitTarget: parseFloat(e.target.value) || 0 }
                    })}
                    className="w-full bg-dark-bg border border-success rounded px-3 py-2"
                  />
                </div>

                <div>
                  <label className="block text-sm mb-2">Max Drawdown (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={settings.risk.maxDrawdown}
                    onChange={(e) => setSettings({
                      ...settings,
                      risk: { ...settings.risk, maxDrawdown: parseFloat(e.target.value) || 0 }
                    })}
                    className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
                  />
                </div>
              </div>
            </div>

            {/* API Settings */}
            <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
              <h2 className="text-lg font-semibold mb-4">API & Performance</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm mb-2">Data Refresh Interval (ms)</label>
                  <input
                    type="number"
                    min={1000}
                    max={60000}
                    step={1000}
                    value={settings.api.refreshInterval}
                    onChange={(e) => setSettings({
                      ...settings,
                      api: { ...settings.api, refreshInterval: parseInt(e.target.value) || 5000 }
                    })}
                    className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">WebSocket Enabled</div>
                    <div className="text-sm text-dark-text-muted">Real-time data updates</div>
                  </div>
                  <button
                    onClick={() => setSettings({
                      ...settings,
                      api: { ...settings.api, websocketEnabled: !settings.api.websocketEnabled }
                    })}
                    className={`w-12 h-6 rounded-full transition-colors ${
                      settings.api.websocketEnabled ? 'bg-primary' : 'bg-dark-border'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full transition-transform ${
                        settings.api.websocketEnabled ? 'translate-x-6' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-6 py-3 bg-primary hover:bg-primary-hover rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
