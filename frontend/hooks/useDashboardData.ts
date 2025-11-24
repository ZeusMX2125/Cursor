'use client'

import { useEffect, useState, useCallback } from 'react'
import api from '@/lib/api'
import type { DashboardState } from '@/types/dashboard'

interface UseDashboardDataOptions {
  pollInterval?: number
}

export function useDashboardData(options: UseDashboardDataOptions = {}) {
  const { pollInterval = 5000 } = options
  const [data, setData] = useState<DashboardState | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const response = await api.get<DashboardState>('/api/dashboard/state')
      setData(response.data)
    } catch (err: any) {
      console.error('Failed to fetch dashboard state', err)
      setError(err?.message ?? 'Unable to load dashboard data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, pollInterval)
    return () => clearInterval(interval)
  }, [fetchData, pollInterval])

  return { data, loading, error, refresh: fetchData }
}

