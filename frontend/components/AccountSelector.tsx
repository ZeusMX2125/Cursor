'use client'

import { useState, useEffect } from 'react'
import api from '@/lib/api'

interface Account {
  account_id: string
  id?: string | number  // ProjectX accounts use 'id'
  name?: string
  accountName?: string  // ProjectX accounts may use 'accountName'
  stage?: string
  size?: string
  running?: boolean
  paper_trading?: boolean
  paperTrading?: boolean
  enabled?: boolean
}

interface AccountSelectorProps {
  selectedAccount: string | null
  onAccountChange: (accountId: string) => void
}

export default function AccountSelector({ selectedAccount, onAccountChange }: AccountSelectorProps) {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAccounts()
  }, [])

  const fetchAccounts = async () => {
    try {
      setError(null)
      // Try ProjectX accounts first (from dashboard state)
      const dashboardResponse = await api.get('/api/dashboard/state')
      const projectxAccounts = dashboardResponse.data?.projectx?.accounts || []
      
      // Also try /api/accounts endpoint
      let apiAccounts: any[] = []
      try {
        const accountsResponse = await api.get('/api/accounts')
        apiAccounts = accountsResponse.data?.accounts || []
      } catch (e) {
        // Fallback if endpoint doesn't exist
      }
      
      // Merge accounts, prioritizing ProjectX accounts
      const allAccounts: Account[] = []
      
      // Add ProjectX accounts
      projectxAccounts.forEach((acc: any) => {
        allAccounts.push({
          account_id: String(acc.id || acc.account_id || ''),
          id: acc.id,
          name: acc.name || acc.accountName || `Account ${acc.id}`,
          accountName: acc.name || acc.accountName,
          enabled: acc.canTrade !== false,
          paper_trading: acc.simulated || false,
        })
      })
      
      // Add API accounts (avoid duplicates)
      apiAccounts.forEach((acc: any) => {
        const accountId = String(acc.account_id || acc.id || '')
        if (!allAccounts.find(a => String(a.account_id) === accountId)) {
          allAccounts.push({
            account_id: accountId,
            id: acc.id || acc.account_id,
            name: acc.name || acc.accountName || `Account ${accountId}`,
            accountName: acc.name || acc.accountName,
            stage: acc.stage,
            size: acc.size,
            running: acc.running,
            paper_trading: acc.paper_trading || acc.paperTrading,
            enabled: acc.enabled !== false,
          })
        }
      })
      
      setAccounts(allAccounts)
    } catch (error) {
      console.error('Error fetching accounts:', error)
      const message =
        (error as any)?.response?.data?.detail ||
        (error as any)?.message ||
        'Unable to load accounts'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-sm text-dark-text-muted">Loading accounts...</div>
  }

  if (error) {
    return (
      <div className="text-sm text-danger flex flex-col gap-2">
        <span>{error}</span>
        <button
          className="self-start px-3 py-1 text-xs rounded bg-dark-border text-dark-text"
          onClick={() => {
            setLoading(true)
            fetchAccounts()
          }}
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="mb-4">
      <label className="block text-sm font-medium mb-2">Select Account</label>
      <select
        value={selectedAccount || ''}
        onChange={(e) => onAccountChange(e.target.value)}
        className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
      >
        <option value="">-- Select Account --</option>
        {accounts.map((account) => {
          const accountId = account.account_id || account.id || ''
          const accountName = account.name || account.accountName || accountId
          const size = account.size ? `(${account.size.toUpperCase()})` : ''
          const stage = account.stage ? ` - ${account.stage}` : ''
          const isPaper = account.paper_trading ?? account.paperTrading ?? false
          const isRunning = account.running ?? false
          
          return (
            <option key={accountId} value={String(accountId)}>
              {accountName} {size}{stage}
              {isPaper ? ' [Paper]' : ' [Live]'}
              {isRunning ? ' 🟢' : ' ⚫'}
            </option>
          )
        })}
      </select>
    </div>
  )
}

