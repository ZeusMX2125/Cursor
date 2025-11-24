'use client'

import { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api from '@/lib/api'

interface Candle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface TradingChartProps {
  symbol: string
  timeframe: string
  onTimeframeChange: (tf: string) => void
}

const TIMEFRAMES = ['1m', '5m', '15m']

export default function TradingChart({ symbol, timeframe, onTimeframeChange }: TradingChartProps) {
  const [candles, setCandles] = useState<Candle[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [dataSource, setDataSource] = useState<'live' | 'mock' | 'unknown'>('unknown')

  const currentPrice = useMemo(() => {
    if (!candles.length) return 0
    return candles[candles.length - 1].close
  }, [candles])

  const loadCandles = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get('/api/market/candles', {
        params: { symbol, timeframe, bars: 200 },
      })
      const data: Candle[] = (response.data.candles || []).map((c: any) => ({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        volume: c.volume,
      }))
      setCandles(data)
      setDataSource((response.data.source as 'live' | 'mock') ?? 'unknown')
    } catch (err: any) {
      console.error('Unable to load candles', err)
      const backendMessage =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Unable to load chart data'
      setError(backendMessage)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCandles()
    const interval = setInterval(loadCandles, 60_000)
    return () => clearInterval(interval)
  }, [symbol, timeframe])

  return (
    <div className="flex-1 bg-dark-card border border-dark-border rounded-lg p-4 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 text-lg font-semibold">
            <span>{symbol}</span>
            <span
              className={`text-xs px-2 py-1 rounded ${
                dataSource === 'live'
                  ? 'text-success bg-success/20'
                  : 'text-primary bg-primary/20'
              }`}
            >
              {dataSource === 'live' ? 'LIVE' : dataSource === 'mock' ? 'SIM' : 'OFFLINE'}
            </span>
          </div>
          <div className="text-xs text-dark-text-muted">Micro futures feed via TopstepX</div>
        </div>
        <div className="flex items-center gap-2">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => onTimeframeChange(tf)}
              className={`px-3 py-1 text-xs rounded ${
                timeframe === tf ? 'bg-primary text-white' : 'bg-dark-border text-dark-text'
              }`}
            >
              {tf.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-[420px]">
        {loading && (
          <div className="flex items-center justify-center h-full text-dark-text-muted">Loading chart...</div>
        )}
        {!loading && error && (
          <div className="flex flex-col items-center justify-center h-full text-sm gap-2">
            <span className="text-danger text-center px-4">{error}</span>
            <button
              onClick={loadCandles}
              className="px-4 py-1 text-xs rounded bg-dark-border text-dark-text hover:bg-dark-border/80 transition"
            >
              Retry
            </button>
          </div>
        )}
        {!loading && !error && (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={candles}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#0f172a" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="time" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} domain={['dataMin - 5', 'dataMax + 5']} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #1f2937', color: '#f3f4f6' }}
                labelStyle={{ color: '#9ca3af' }}
              />
              <Area type="monotone" dataKey="close" stroke="#10b981" fillOpacity={1} fill="url(#priceGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mt-4">
        <div>
          <div className="text-xs text-dark-text-muted mb-1">Current Price</div>
          <div className="text-2xl font-bold text-success">
            {currentPrice ? currentPrice.toFixed(2) : '--'}
          </div>
        </div>
        <div className="h-16">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={candles.slice(-60)}>
              <XAxis dataKey="time" hide />
              <YAxis hide />
              <Bar dataKey="volume" fill="#2563eb" barSize={4} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
