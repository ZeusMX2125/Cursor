'use client'

import { type ChangeEvent, useEffect, useMemo } from 'react'
import { useContracts, type ProjectXContract } from '@/contexts/ContractsContext'
import { formatSymbolForDisplay } from '@/lib/contractUtils'

export type { ProjectXContract }

interface InstrumentSelectorProps {
  value?: string
  onChange?: (symbol: string) => void
  onContractChange?: (contract: ProjectXContract | null) => void
  className?: string
  disabled?: boolean
  showLabel?: boolean
}

export default function InstrumentSelector({
  value,
  onChange,
  onContractChange,
  className = '',
  disabled = false,
  showLabel = false,
}: InstrumentSelectorProps) {
  const { contracts, loading, error } = useContracts()

  const groupedContracts = useMemo(() => {
    if (!contracts.length) {
      return {}
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

  const displayValue = useMemo(() => {
    if (!value) return ''
    const contract = contractLookup[value]
    return formatSymbolForDisplay(value, contract || undefined)
  }, [value, contractLookup])

  // Don't render dropdown until contracts are loaded
  if (loading && contracts.length === 0) {
    return (
      <div className={`flex flex-col ${className}`}>
        {showLabel && (
          <label className="text-xs text-gray-400 mb-1 font-medium">
            Instrument
          </label>
        )}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 animate-pulse">Loading instruments…</span>
        </div>
      </div>
    )
  }

  // Show error state if contracts failed to load
  if (error && contracts.length === 0) {
    return (
      <div className={`flex flex-col ${className}`}>
        {showLabel && (
          <label className="text-xs text-gray-400 mb-1 font-medium">
            Instrument
          </label>
        )}
        <div className="flex items-center gap-2">
          <span className="text-xs text-red-400">Unable to load instruments</span>
        </div>
      </div>
    )
  }

  // Always show the dropdown, even if empty - this makes it visible
  return (
    <div className={`flex flex-col ${className}`}>
      {showLabel && (
        <label className="text-xs text-gray-400 mb-1 font-medium">
          Instrument
        </label>
      )}
      <select
        value={value ?? ''}
        onChange={handleChange}
        disabled={disabled || loading}
        className="bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-sm text-white min-w-[220px] hover:border-[#3a3a3a] focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer disabled:opacity-50"
      >
        {loading && contracts.length === 0 ? (
          <option value="" disabled>Loading instruments...</option>
        ) : contracts.length === 0 ? (
          <option value="" disabled>
            {error ? `Error: ${error}` : 'No instruments available'}
          </option>
        ) : (
          <>
            <option value="" disabled>Select an instrument</option>
            {Object.entries(groupedContracts)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([group, items]) => (
                <optgroup key={group} label={group}>
                  {items
                    .sort((a, b) => (a.symbol || '').localeCompare(b.symbol || ''))
                    .map((contract) => {
                      const symbol = contract.symbol || contract.name || String(contract.id)
                      const displaySymbol = formatSymbolForDisplay(symbol, contract)
                      const label = contract.description || contract.name || symbol
                      return (
                        <option key={`${group}-${symbol}`} value={symbol}>
                          {displaySymbol} — {label}
                        </option>
                      )
                    })}
                </optgroup>
              ))}
          </>
        )}
      </select>
      {error && contracts.length === 0 && (
        <span className="text-xs text-red-400 mt-1">
          {error}. <button onClick={() => window.location.reload()} className="underline">Refresh page</button>
        </span>
      )}
      {loading && contracts.length === 0 && !error && (
        <span className="text-xs text-gray-400 animate-pulse mt-1">Loading instruments…</span>
      )}
    </div>
  )
}

