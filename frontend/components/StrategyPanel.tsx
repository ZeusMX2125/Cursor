'use client'

import { useState } from 'react'
import api from '@/lib/api'
import type { AccountSnapshot } from '@/types/dashboard'

interface StrategyPanelProps {
  account?: AccountSnapshot
  onRefresh: () => void
}

const QUICK_STRATEGIES = [
  { id: 'scalp_2_4', label: 'Scalp 2/4' },
  { id: 'breakout', label: 'Breakout' },
  { id: 'mean_revert', label: 'Mean Reversion' },
]

export default function StrategyPanel({ account, onRefresh }: StrategyPanelProps) {
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const triggerStrategy = async (strategyId: string) => {
    if (!account) {
      setMessage('Select an account to route strategy')
      return
    }
    setSubmitting(true)
    setMessage(null)
    try {
      await api.post(`/api/strategies/${account.account_id}/activate`, { strategy: strategyId })
      setMessage(`Strategy ${strategyId} armed`)
      onRefresh()
    } catch (error: any) {
      setMessage(error?.message ?? 'Unable to trigger strategy')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg p-4 space-y-3">
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-semibold">Quick Strategies</h3>
        {submitting && <span className="text-xs text-dark-text-muted">routing...</span>}
      </div>
      {message && <div className="text-xs text-primary">{message}</div>}
      <div className="grid grid-cols-2 gap-2">
        {QUICK_STRATEGIES.map((strategy) => (
          <button
            key={strategy.id}
            disabled={submitting}
            onClick={() => triggerStrategy(strategy.id)}
            className={`px-3 py-2 rounded text-xs font-semibold ${
              account?.strategies.active === strategy.id ? 'bg-primary text-white' : 'bg-dark-bg border border-dark-border'
            }`}
          >
            {strategy.label}
          </button>
        ))}
      </div>
      <div className="pt-2 border-t border-dark-border">
        <div className="flex items-center justify-between text-xs">
          <span className="text-dark-text-muted">Active strategy</span>
          <span className="font-semibold">{account?.strategies.active ?? 'None'}</span>
        </div>
        <div className="text-xs text-dark-text-muted mt-1">
          Agent: {account?.strategies.agent ?? 'rule_based'}
        </div>
      </div>
    </div>
  )
}
