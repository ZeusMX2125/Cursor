'use client'

import { useState } from 'react'
import api from '@/lib/api'
import type { AccountSnapshot } from '@/types/dashboard'

interface AccountPanelProps {
  accounts: AccountSnapshot[]
  selectedAccountId?: string
  onSelectAccount: (accountId: string) => void
  onRefresh: () => void
  loading?: boolean
}

export default function AccountPanel({ accounts, selectedAccountId, onSelectAccount, onRefresh, loading }: AccountPanelProps) {
  const [expanded, setExpanded] = useState(true)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const handleAction = async (accountId: string, action: 'start' | 'stop' | 'flatten') => {
    try {
      setActionMessage(null)
      if (action === 'flatten') {
        await api.post(`/api/trading/accounts/${accountId}/flatten`)
      } else {
        await api.post(`/api/accounts/${accountId}/${action}`)
      }
      setActionMessage(`Action ${action} sent to ${accountId}`)
      onRefresh()
    } catch (error: any) {
      console.error(`Failed to ${action} account`, error)
      setActionMessage(error?.message ?? 'Action failed')
    }
  }

  const formatCurrency = (value: number) => `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold">Accounts</h3>
        <div className="flex items-center gap-2 text-xs text-dark-text-muted">
          {loading && <span>Refreshing...</span>}
          <button onClick={onRefresh} className="px-2 py-1 rounded bg-dark-border hover:bg-dark-border/80">Refresh</button>
          <button onClick={() => setExpanded(!expanded)}>{expanded ? '▼' : '▶'}</button>
        </div>
      </div>

      {actionMessage && <div className="text-xs text-primary mb-2">{actionMessage}</div>}

      {expanded && (
        <div className="space-y-3 max-h-[420px] overflow-auto pr-1">
          {accounts.map((account) => {
            const isSelected = selectedAccountId === account.account_id
            const pnlColor = account.metrics.daily_pnl >= 0 ? 'text-success' : 'text-danger'
            return (
              <div
                key={account.account_id}
                className={`p-3 rounded border ${
                  isSelected ? 'border-primary bg-dark-bg/80' : 'border-dark-border bg-dark-bg'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-sm font-semibold truncate">{account.name}</div>
                    <div className="text-xs text-dark-text-muted">
                      {account.stage.toUpperCase()} · {account.size.toUpperCase()}
                    </div>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded ${
                      account.running ? 'bg-success/20 text-success' : 'bg-dark-border text-dark-text-muted'
                    }`}
                  >
                    {account.running ? 'RUNNING' : 'IDLE'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                  <div>
                    <div className="text-dark-text-muted">Balance</div>
                    <div className="text-sm font-semibold">{formatCurrency(account.balance)}</div>
                  </div>
                  <div>
                    <div className="text-dark-text-muted">Buying Power</div>
                    <div className="text-sm font-semibold">{formatCurrency(account.buying_power)}</div>
                  </div>
                  <div>
                    <div className="text-dark-text-muted">Daily P&L</div>
                    <div className={`text-sm font-semibold ${pnlColor}`}>{formatCurrency(account.metrics.daily_pnl)}</div>
                  </div>
                  <div>
                    <div className="text-dark-text-muted">Strategies</div>
                    <div className="text-sm">{account.strategies.active ?? 'None'}</div>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3 text-xs">
                  <div className="text-dark-text-muted">Equity Goal: {formatCurrency(account.profit_target)}</div>
                  <div className="flex gap-1">
                    <button className="px-2 py-1 rounded bg-primary text-white" onClick={() => onSelectAccount(account.account_id)}>
                      Focus
                    </button>
                    <button className="px-2 py-1 rounded bg-dark-border" onClick={() => handleAction(account.account_id, 'stop')}>
                      Stop
                    </button>
                    <button className="px-2 py-1 rounded bg-dark-border" onClick={() => handleAction(account.account_id, 'start')}>
                      Make Leader
                    </button>
                    <button className="px-2 py-1 rounded bg-dark-border" onClick={() => handleAction(account.account_id, 'flatten')}>
                      Flatten
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
          {!accounts.length && <div className="text-sm text-dark-text-muted">No accounts configured</div>}
        </div>
      )}
    </div>
  )
}
