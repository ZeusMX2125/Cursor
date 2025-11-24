'use client'

import { type ChangeEvent, useEffect, useMemo, useState } from 'react'
import api from '@/lib/api'

export interface ProjectXContract {
  id?: number | string
  symbol?: string
  name?: string
  description?: string
  baseSymbol?: string
  tickSize?: number
  tickValue?: number
  exchange?: string
  live?: boolean
}

interface InstrumentSelectorProps {
  value?: string
  onChange?: (symbol: string) => void
  onContractChange?: (contract: ProjectXContract | null) => void
  className?: string
  disabled?: boolean
  showLabel?: boolean
}

const DEFAULT_SYMBOLS = ['ESZ25', 'NQZ25', 'M2KZ5', 'CLZ25']

export default function InstrumentSelector({
  value,
  onChange,
  onContractChange,
  className = '',
  disabled = false,
  showLabel = false,
}: InstrumentSelectorProps) {
  const [contracts, setContracts] = useState<ProjectXContract[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetchContracts = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await api.get('/api/market/contracts', {
          params: { live: true },
        })
        if (!cancelled) {
          const payload: ProjectXContract[] = response.data?.contracts ?? []
          setContracts(payload)
        }
      } catch (err: any) {
        if (!cancelled) {
          console.error('Unable to load contracts', err)
          setError(err?.message ?? 'Unable to load contracts')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchContracts()
    return () => {
      cancelled = true
    }
  }, [])

  const groupedContracts = useMemo(() => {
    if (!contracts.length) {
      // Provide fallback options so the selector is never empty
      return DEFAULT_SYMBOLS.reduce<Record<string, ProjectXContract[]>>((acc, symbol) => {
        acc[symbol.replace(/\d+/g, '') || symbol] = [
          {
            id: symbol,
            symbol,
            name: symbol,
            description: `${symbol} (manual)`,
            baseSymbol: symbol.replace(/\d+/g, '') || symbol,
          },
        ]
        return acc
      }, {})
    }

    return contracts.reduce<Record<string, ProjectXContract[]>>((acc, contract) => {
      const base = (contract.baseSymbol || contract.symbol || 'OTHER').toUpperCase()
      if (!acc[base]) {
        acc[base] = []
      }
      acc[base].push(contract)
      return acc
    }, {})
  }, [contracts])

  const contractLookup = useMemo(() => {
    const entries: Record<string, ProjectXContract> = {}
    Object.values(groupedContracts).forEach((group) => {
      group.forEach((contract) => {
        const symbol = contract.symbol || contract.name
        if (symbol) {
          entries[symbol] = contract
        }
      })
    })
    return entries
  }, [groupedContracts])

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const symbol = event.target.value
    onChange?.(symbol)
    onContractChange?.(contractLookup[symbol] ?? null)
  }

  useEffect(() => {
    if (value && onContractChange) {
      onContractChange(contractLookup[value] ?? null)
    }
  }, [value, contractLookup, onContractChange])

  return (
    <div className={`flex flex-col ${className}`}>
      {showLabel && (
        <label className="text-xs text-gray-400 mb-1 font-medium">
          Instrument
        </label>
      )}
      <div className="flex items-center gap-2">
        <select
          value={value ?? ''}
          onChange={handleChange}
          disabled={disabled || loading}
          className="bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-sm text-white min-w-[220px]"
        >
          {error && <option value="">Unable to load instruments</option>}
          {!error &&
            Object.entries(groupedContracts)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([group, items]) => (
                <optgroup key={group} label={group}>
                  {items
                    .sort((a, b) => (a.symbol || '').localeCompare(b.symbol || ''))
                    .map((contract) => {
                      const symbol = contract.symbol || contract.name || String(contract.id)
                      const label = contract.description || contract.name || symbol
                      return (
                        <option key={`${group}-${symbol}`} value={symbol}>
                          {symbol} — {label}
                        </option>
                      )
                    })}
                </optgroup>
              ))}
        </select>
        {loading && (
          <span className="text-xs text-gray-400 animate-pulse">Loading…</span>
        )}
      </div>
    </div>
  )
}

