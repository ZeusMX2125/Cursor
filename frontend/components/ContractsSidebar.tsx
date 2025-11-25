'use client'

import { useState, useMemo, MouseEvent } from 'react'
import { useContracts, type ProjectXContract } from '@/contexts/ContractsContext'
import { formatSymbolForDisplay } from '@/lib/contractUtils'

interface ContractsSidebarProps {
  selectedSymbol?: string
  onSelectContract: (symbol: string, contract: ProjectXContract) => void
}

export default function ContractsSidebar({ selectedSymbol, onSelectContract }: ContractsSidebarProps) {
  const { contracts, loading, error, refresh, favorites, toggleFavorite, isFavorite } = useContracts()
  const [searchQuery, setSearchQuery] = useState('')

  const filteredContracts = useMemo(() => {
    if (!searchQuery.trim()) return contracts
    
    const query = searchQuery.toUpperCase()
    return contracts.filter((contract) => {
      const symbol = (contract.symbol || '').toUpperCase()
      const name = (contract.name || '').toUpperCase()
      const description = (contract.description || '').toUpperCase()
      const baseSymbol = (contract.baseSymbol || '').toUpperCase()
      
      return symbol.includes(query) || 
             name.includes(query) || 
             description.includes(query) ||
             baseSymbol.includes(query)
    })
  }, [contracts, searchQuery])

  const favoriteSet = useMemo(() => new Set(favorites.map((fav) => fav.toUpperCase())), [favorites])

  const favoriteContracts = useMemo(() => {
    return filteredContracts.filter((contract) => {
      const symbol = (contract.symbol || contract.name || '').toUpperCase()
      return symbol && favoriteSet.has(symbol)
    })
  }, [filteredContracts, favoriteSet])

  const nonFavoriteContracts = useMemo(() => {
    return filteredContracts.filter((contract) => {
      const symbol = (contract.symbol || contract.name || '').toUpperCase()
      return !symbol || !favoriteSet.has(symbol)
    })
  }, [filteredContracts, favoriteSet])

  const groupedContracts = useMemo(() => {
    const groups: Record<string, ProjectXContract[]> = {}
    
    nonFavoriteContracts.forEach((contract) => {
      const base = (contract.baseSymbol || contract.symbol || 'OTHER').toUpperCase()
      if (!groups[base]) {
        groups[base] = []
      }
      groups[base].push(contract)
    })
    
    return groups
  }, [nonFavoriteContracts])

  const renderContractList = (items: ProjectXContract[]) =>
    items
      .sort((a, b) => (a.symbol || '').localeCompare(b.symbol || ''))
      .map((contract) => {
        const symbol = contract.symbol || contract.name || String(contract.id)
        const displaySymbol = formatSymbolForDisplay(symbol, contract)
        const isSelected = selectedSymbol?.toUpperCase() === symbol.toUpperCase()
        const favoriteActive = isFavorite(symbol)

        const handleFavoriteClick = (event: MouseEvent) => {
          event.stopPropagation()
          toggleFavorite(symbol)
        }

        return (
          <div
            key={`${symbol}-${contract.id ?? contract.baseSymbol ?? contract.symbol}`}
            onClick={() => onSelectContract(symbol, contract)}
            className={`px-3 py-2 cursor-pointer hover:bg-[#1a1a1a] transition-colors ${
              isSelected ? 'bg-blue-500/20 border-l-2 border-blue-500' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-1 gap-2">
              <div className="text-sm font-medium text-white truncate">{displaySymbol}</div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleFavoriteClick}
                  title={favoriteActive ? 'Remove from favorites' : 'Add to favorites'}
                  className={`text-xs ${favoriteActive ? 'text-yellow-400' : 'text-gray-500 hover:text-gray-300'}`}
                >
                  {favoriteActive ? '★' : '☆'}
                </button>
                <div className="text-xs text-gray-400">{contract.live ? 'US' : 'SIM'}</div>
              </div>
            </div>
            {contract.description && (
              <div className="text-xs text-gray-500 truncate">{contract.description}</div>
            )}
            <div className="flex items-center gap-2 mt-1">
              {contract.tickSize && (
                <span className="text-xs text-gray-400">Tick: {contract.tickSize}</span>
              )}
              {contract.tickValue && (
                <span className="text-xs text-gray-400">Value: ${contract.tickValue}</span>
              )}
            </div>
          </div>
        )
      })

  return (
    <div className="w-64 bg-[#0a0a0a] border-r border-[#1a1a1a] flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[#1a1a1a]">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">Contracts</h3>
          <button
            onClick={() => refresh()}
            className="text-xs text-gray-400 hover:text-white px-2 py-1 bg-[#1a1a1a] rounded"
            disabled={loading}
          >
            Refresh
          </button>
        </div>
        
        {/* Search input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Q Search contracts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
            >
              ×
            </button>
          )}
        </div>
        
        {/* Contract count */}
        <div className="mt-2 text-xs text-gray-400">
          {loading ? 'Loading...' : error ? `Error: ${error}` : `${filteredContracts.length} contracts`}
        </div>
      </div>

      {/* Contracts list */}
      <div className="flex-1 overflow-y-auto">
        {loading && contracts.length === 0 ? (
          <div className="p-4 text-center text-gray-400 text-sm">Loading contracts...</div>
        ) : error && contracts.length === 0 ? (
          <div className="p-4 text-center text-red-400 text-sm">
            <div className="mb-2">Unable to load contracts</div>
            <button
              onClick={() => refresh()}
              className="text-xs underline hover:text-red-300"
            >
              Retry
            </button>
          </div>
        ) : filteredContracts.length === 0 ? (
          <div className="p-4 text-center text-gray-400 text-sm">
            {searchQuery ? 'No contracts match your search' : 'No contracts available'}
          </div>
        ) : (
          <div className="divide-y divide-[#1a1a1a]">
            {favoriteContracts.length > 0 && (
              <div>
                <div className="px-3 py-2 bg-[#0f0f0f] border-b border-[#1a1a1a] flex items-center justify-between">
                  <div className="text-xs font-semibold text-yellow-400 uppercase flex items-center gap-2">
                    Favorites
                  </div>
                  <span className="text-[10px] text-gray-500">{favoriteContracts.length}</span>
                </div>
                {renderContractList(favoriteContracts)}
              </div>
            )}
            {Object.entries(groupedContracts)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([group, items]) => (
                <div key={group}>
                  <div className="px-3 py-2 bg-[#0f0f0f] border-b border-[#1a1a1a] flex items-center justify-between">
                    <div className="text-xs font-semibold text-gray-400 uppercase">{group}</div>
                    <span className="text-[10px] text-gray-500">{items.length}</span>
                  </div>
                  {renderContractList(items)}
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  )
}

