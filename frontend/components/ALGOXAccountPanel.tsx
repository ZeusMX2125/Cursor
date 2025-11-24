'use client'

import { useState } from 'react'
import api from '@/lib/api'
import type { ProjectXAccount } from '@/types/dashboard'

interface ALGOXAccountPanelProps {
  accounts: ProjectXAccount[]
  selectedAccountId?: string
  onSelectAccount: (accountId: string) => void
  onRefresh: () => void
  loading?: boolean
}

export default function ALGOXAccountPanel({
  accounts,
  selectedAccountId,
  onSelectAccount,
  onRefresh,
  loading,
}: ALGOXAccountPanelProps) {
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [flattening, setFlattening] = useState<string | null>(null)

  const handleFlatten = async (accountId: string) => {
    try {
      setFlattening(accountId)
      setActionMessage(null)
      await api.post(`/api/trading/accounts/${accountId}/flatten`)
      setActionMessage('Flatten request sent')
      onRefresh()
    } catch (error: any) {
      console.error('Failed to flatten account', error)
      setActionMessage(error?.message ?? 'Flatten failed')
    } finally {
      setFlattening(null)
    }
  }

  const formatCurrency = (value?: number) => {
    if (typeof value !== 'number') return '--'
    return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
  }

  return (
    <div className="bg-[#0a0a0a] border-b border-[#1a1a1a] p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">ACCOUNTS</h3>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="px-2 py-1 text-xs bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#2a2a2a] rounded text-gray-400 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {actionMessage && <div className="text-xs text-blue-500">{actionMessage}</div>}

      <div className="space-y-3 max-h-[400px] overflow-auto">
        {accounts.map((account) => {
          const id = String(account.id)
          const isSelected = selectedAccountId === id

          return (
            <div
              key={id}
              className={`p-3 rounded border ${
                isSelected ? 'border-blue-600 bg-[#1a1a1a]' : 'border-[#2a2a2a] bg-[#0f0f0f]'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="text-sm font-semibold text-white">{account.name || `Account ${id}`}</div>
                  <div className="text-xs text-gray-400">ID: {id}</div>
                </div>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded ${
                    account.canTrade ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'
                  }`}
                >
                  {account.canTrade ? 'TRADABLE' : 'RESTRICTED'}
                </span>
              </div>

              <div className="space-y-2 mb-3">
                <div className="flex justify-between">
                  <span className="text-xs text-gray-400">Balance</span>
                  <span className="text-sm font-semibold text-white">{formatCurrency(account.balance)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-gray-400">Mode</span>
                  <span className="text-sm font-semibold text-white">
                    {account.simulated ? 'Simulated' : 'Live'}
                  </span>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => onSelectAccount(id)}
                  className="flex-1 px-2 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold"
                >
                  Select
                </button>
                <button
                  onClick={() => handleFlatten(id)}
                  disabled={flattening === id}
                  className="flex-1 px-2 py-1.5 text-xs bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#2a2a2a] text-white rounded font-semibold disabled:opacity-50"
                >
                  {flattening === id ? '...' : 'Flatten'}
                </button>
              </div>
            </div>
          )
        })}
        {!accounts.length && <div className="text-sm text-gray-500 text-center py-4">No ProjectX accounts detected</div>}
      </div>
    </div>
  )
}

