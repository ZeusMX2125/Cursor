'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
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

const FAVORITES_STORAGE_KEY = 'algox_contract_favorites'

interface ContractsContextType {
  contracts: ProjectXContract[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  getContractBySymbol: (symbol: string) => ProjectXContract | null
  isValidSymbol: (symbol: string) => boolean
  getFirstContract: () => ProjectXContract | null
  getContractsByBaseSymbol: (baseSymbol: string) => ProjectXContract[]
  favorites: string[]
  toggleFavorite: (symbol: string) => void
  isFavorite: (symbol: string) => boolean
}

const ContractsContext = createContext<ContractsContextType | undefined>(undefined)

export function ContractsProvider({ children }: { children: ReactNode }) {
  const [contracts, setContracts] = useState<ProjectXContract[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [favorites, setFavorites] = useState<string[]>([])

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const stored = window.localStorage.getItem(FAVORITES_STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed)) {
          setFavorites(parsed)
        }
      }
    } catch (loadError) {
      console.warn('[ContractsContext] Failed to load favorites from storage:', loadError)
    }
  }, [])

  const persistFavorites = (next: string[]) => {
    setFavorites(next)
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(next))
      } catch (storageError) {
        console.warn('[ContractsContext] Failed to persist favorites:', storageError)
      }
    }
  }

  const toggleFavorite = (symbol: string) => {
    if (!symbol) return
    const normalized = symbol.toUpperCase()
    persistFavorites(
      favorites.includes(normalized)
        ? favorites.filter((fav) => fav !== normalized)
        : [...favorites, normalized]
    )
  }

  const isFavorite = (symbol: string) => {
    if (!symbol) return false
    return favorites.includes(symbol.toUpperCase())
  }

  const fetchContracts = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log('[ContractsContext] Fetching contracts from /api/market/contracts?live=true')
      
      // Try with live=true first
      let response
      try {
        response = await api.get('/api/market/contracts', {
          params: { live: true },
        })
      } catch (liveError: any) {
        // If live=true fails, try without the live parameter
        console.warn('[ContractsContext] Failed with live=true, trying without live parameter:', liveError?.message)
        response = await api.get('/api/market/contracts', {
          params: { live: false },
        })
      }
      
      console.log('[ContractsContext] Response received:', {
        status: response.status,
        data: response.data,
        contractsCount: response.data?.contracts?.length ?? 0
      })
      
      const payload: ProjectXContract[] = response.data?.contracts ?? []
      if (payload.length === 0) {
        console.warn('[ContractsContext] No contracts returned from API. Response:', response.data)
        setError('No contracts available. The backend may not be connected to ProjectX API.')
      } else {
        console.log(`[ContractsContext] Successfully loaded ${payload.length} contracts`)
        setError(null)
      }
      setContracts(payload)
    } catch (err: any) {
      console.error('[ContractsContext] Error loading contracts:', {
        message: err?.message,
        response: err?.response?.data,
        status: err?.response?.status,
        url: err?.config?.url,
        fullError: err
      })
      const errorMessage = err?.response?.data?.detail || err?.message || 'Unable to load contracts. Check backend connection.'
      setError(errorMessage)
      setContracts([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchContracts()
    // Refresh contracts every 5 minutes
    const interval = setInterval(fetchContracts, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const getContractBySymbol = (symbol: string): ProjectXContract | null => {
    if (!symbol) return null
    const upperSymbol = symbol.toUpperCase()
    return contracts.find(
      (c) =>
        (c.symbol || '').toUpperCase() === upperSymbol ||
        (c.name || '').toUpperCase() === upperSymbol
    ) || null
  }

  const isValidSymbol = (symbol: string): boolean => {
    return getContractBySymbol(symbol) !== null
  }

  const getFirstContract = (): ProjectXContract | null => {
    return contracts.length > 0 ? contracts[0] : null
  }

  const getContractsByBaseSymbol = (baseSymbol: string): ProjectXContract[] => {
    if (!baseSymbol) return []
    const upperBase = baseSymbol.toUpperCase()
    return contracts.filter(
      (c) => (c.baseSymbol || c.symbol || '').toUpperCase() === upperBase
    )
  }

  return (
    <ContractsContext.Provider
      value={{
        contracts,
        loading,
        error,
        refresh: fetchContracts,
        getContractBySymbol,
        isValidSymbol,
        getFirstContract,
        getContractsByBaseSymbol,
        favorites,
        toggleFavorite,
        isFavorite,
      }}
    >
      {children}
    </ContractsContext.Provider>
  )
}

export function useContracts() {
  const context = useContext(ContractsContext)
  if (context === undefined) {
    throw new Error('useContracts must be used within a ContractsProvider')
  }
  return context
}

