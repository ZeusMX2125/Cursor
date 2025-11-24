'use client'

import { useState } from 'react'
import api from '@/lib/api'
import type { AccountSnapshot } from '@/types/dashboard'

interface ALGOXQuickStrategiesProps {
  account?: AccountSnapshot
  onRefresh: () => void
}

export default function ALGOXQuickStrategies({ account, onRefresh }: ALGOXQuickStrategiesProps) {
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
    <div className="bg-[#0a0a0a] border-b border-[#1a1a1a] p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-white mb-2">Quick Strategies</h3>
        {message && <div className="text-xs text-blue-500 mb-2">{message}</div>}
        <div className="flex gap-2">
          <button
            disabled={submitting}
            onClick={() => triggerStrategy('scalp_2_4')}
            className="flex-1 px-3 py-2 bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#2a2a2a] rounded text-xs font-semibold text-white disabled:opacity-50"
          >
            Scalp 2/4
          </button>
          <button
            disabled={submitting}
            onClick={() => triggerStrategy('breakout')}
            className="flex-1 px-3 py-2 bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#2a2a2a] rounded text-xs font-semibold text-white disabled:opacity-50"
          >
            Breakout
          </button>
        </div>
      </div>
      <div className="pt-3 border-t border-[#1a1a1a]">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-400">Active Bots</span>
          <span className="text-white font-semibold">
            {account?.running ? '1 RUNNING' : '0 RUNNING'}
          </span>
        </div>
      </div>
    </div>
  )
}

