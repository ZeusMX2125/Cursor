'use client'

import { useEffect, useMemo, useState, useRef, useCallback } from 'react'
import { ComposedChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'
import api from '@/lib/api'
import { subscribeToWebSocketMessages } from '@/lib/websocket'
import type { Position } from '@/types/dashboard'
import { useContracts } from '@/contexts/ContractsContext'
import { quoteMatchesChartSymbol } from '@/lib/contractUtils'

interface Candle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface CandlestickChartProps {
  symbol: string
  timeframe: string
  onTimeframeChange: (tf: string) => void
  onPriceUpdate?: (price: number, change: number, changePercent: number) => void
  positions?: Position[]
}

const TIMEFRAMES = ['1m', '5m', '15m']

// Custom shape for candlesticks
// Creates a render function that has access to the price domain
const createCandlestickRenderer = (priceDomain: [number, number]) => {
  return (props: any) => {
    const { x, y, width, payload, yAxis } = props
    if (!payload) return <g /> // Return empty group instead of null
    
    const isUp = payload.close >= payload.open
    const color = isUp ? '#10b981' : '#ef4444'
    
    // Get the chart height from props or use a default
    const chartHeight = props.height || 500
    
    // Calculate price range and pixel per price
    const [minPrice, maxPrice] = priceDomain
    const priceRange = maxPrice - minPrice
    
    if (priceRange === 0) {
      // Single price point - render a small rectangle
      return (
        <rect
          x={x + width * 0.15}
          y={y - 2}
          width={width * 0.7}
          height={4}
          fill={color}
          stroke={color}
        />
      )
    }
    
    const pixelPerPrice = chartHeight / priceRange
    
    // Calculate Y positions relative to the close price (which is at y)
    // In Recharts, y is the position for the value (close price)
    // We need to calculate offsets from this position
    const closePrice = payload.close
    const highOffset = (closePrice - payload.high) * pixelPerPrice
    const lowOffset = (payload.low - closePrice) * pixelPerPrice
    const openOffset = (closePrice - payload.open) * pixelPerPrice
    
    const highY = y + highOffset
    const lowY = y + lowOffset
    const openY = y + openOffset
    const bodyTopY = Math.min(y, openY)
    const bodyBottomY = Math.max(y, openY)
    const bodyHeight = Math.max(Math.abs(openY - y), 2)
    
    return (
      <g>
        {/* Wick (high to low line) */}
        <line
          x1={x + width / 2}
          y1={highY}
          x2={x + width / 2}
          y2={lowY}
          stroke={color}
          strokeWidth={1.5}
        />
        {/* Body (open to close rectangle) */}
        <rect
          x={x + width * 0.15}
          y={bodyTopY}
          width={width * 0.7}
          height={bodyHeight}
          fill={color}
          stroke={color}
        />
      </g>
    )
  }
}

export default function CandlestickChart({ symbol, timeframe, onTimeframeChange, onPriceUpdate, positions = [] }: CandlestickChartProps) {
  const { contracts } = useContracts()
  const [candles, setCandles] = useState<Candle[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [liveMode, setLiveMode] = useState(true)
  const [livePrice, setLivePrice] = useState<number | null>(null)
  const lastMessageRef = useRef<MessageEvent | null>(null)

  // Use live price when available, otherwise fall back to last candle close
  const currentPrice = useMemo(() => {
    if (livePrice && livePrice > 0) return livePrice
    if (!candles.length) return 0
    return candles[candles.length - 1].close
  }, [candles, livePrice])

  // Calculate price change from previous candle's close (not current candle)
  const priceChange = useMemo(() => {
    if (candles.length < 1) return 0
    // Compare current live/latest price against the previous candle's close
    const previousClose = candles.length >= 2 
      ? candles[candles.length - 2].close 
      : candles[candles.length - 1].open // Use open if only one candle
    return currentPrice - previousClose
  }, [candles, currentPrice])

  const priceChangePercent = useMemo(() => {
    if (candles.length < 1) return 0
    const previousClose = candles.length >= 2 
      ? candles[candles.length - 2].close 
      : candles[candles.length - 1].open
    if (previousClose === 0) return 0
    return (priceChange / previousClose) * 100
  }, [candles, priceChange])

  // Call onPriceUpdate when price changes (for initial load and candle updates)
  // Live WebSocket updates also call onPriceUpdate directly for immediate response
  useEffect(() => {
    if (onPriceUpdate && currentPrice > 0) {
      onPriceUpdate(currentPrice, priceChange, priceChangePercent)
    }
  }, [currentPrice, priceChange, priceChangePercent, onPriceUpdate])

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
    } catch (err: any) {
      console.error('Unable to load candles', err)
      const errorMessage = err?.response?.data?.detail || err?.message || 'Unable to load chart data'
      setError(errorMessage)
      // If it's a network error, provide more helpful message
      if (err?.code === 'ECONNREFUSED' || err?.message?.includes('Network Error')) {
        setError('Cannot connect to backend. Is the server running on http://localhost:8000?')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCandles()
    const interval = setInterval(loadCandles, 60000)
    return () => clearInterval(interval)
  }, [symbol, timeframe])

  useEffect(() => {
    setLivePrice(null)
  }, [symbol, timeframe])

  const chartData = useMemo(() => {
    return candles.map((candle) => ({
      time: new Date(candle.time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
      volume: candle.volume,
      isUp: candle.close >= candle.open,
      // For candlestick rendering
      value: candle.close, // Use close for positioning
    }))
  }, [candles])

  const priceDomain = useMemo(() => {
    if (!candles.length) return [0, 100] as [number, number]
    const prices = candles.flatMap((c) => [c.high, c.low])
    const min = Math.min(...prices)
    const max = Math.max(...prices)
    const padding = (max - min) * 0.1
    return [min - padding, max + padding] as [number, number]
  }, [candles])

  // Create the candlestick renderer with access to price domain
  const renderCandlestick = useMemo(() => {
    return createCandlestickRenderer(priceDomain)
  }, [priceDomain])

  // Enhanced symbol matching to handle various formats (MES vs MESZ5, F.US.MES, etc.)
  const matchesSymbol = useCallback((quoteSymbol: string, chartSymbol: string): boolean => {
    if (!quoteSymbol || !chartSymbol) return false
    
    // Normalize: uppercase and remove non-alphanumeric characters
    const normalize = (s: string) => s.toUpperCase().replace(/[^A-Z0-9]/g, '')
    const quoteNorm = normalize(quoteSymbol)
    const chartNorm = normalize(chartSymbol)
    
    // Direct match
    if (quoteNorm === chartNorm) return true
    
    // Extract base symbol (letters only) for fuzzy matching
    const quoteBase = quoteNorm.replace(/[0-9]/g, '')
    const chartBase = chartNorm.replace(/[0-9]/g, '')
    
    // Quote is base of chart symbol (MES matches MESZ5)
    if (chartNorm.startsWith(quoteBase) && quoteBase.length >= 2) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[CandlestickChart] Symbol match: quote "${quoteSymbol}" (base: ${quoteBase}) matches chart "${chartSymbol}"`)
      }
      return true
    }
    
    // Chart is base of quote symbol (MESZ5 chart matches MES quote)
    if (quoteNorm.startsWith(chartBase) && chartBase.length >= 2) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[CandlestickChart] Symbol match: quote "${quoteSymbol}" matches chart "${chartSymbol}" (base: ${chartBase})`)
      }
      return true
    }
    
    // Base symbols match (MES == MES from MESZ5)
    if (quoteBase === chartBase && quoteBase.length >= 2) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[CandlestickChart] Symbol match: quote "${quoteSymbol}" and chart "${chartSymbol}" share base "${quoteBase}"`)
      }
      return true
    }
    
    // Try using contractUtils as fallback if contracts are available
    if (contracts.length > 0) {
      return quoteMatchesChartSymbol(quoteSymbol, chartSymbol, contracts)
    }
    
    return false
  }, [contracts])

  const resolveQuoteSymbol = (payload: any) => {
    if (!payload) return undefined
    // Backend normalizes the payload and adds a 'symbol' field
    if (payload.symbol) return String(payload.symbol).toUpperCase()
    if (payload.symbolId) return String(payload.symbolId).toUpperCase()
    if (payload.contractId) {
      const parts = String(payload.contractId).split('.')
      if (parts.length >= 4) {
        return parts[3].toUpperCase()
      }
      return String(payload.contractId).toUpperCase()
    }
    return undefined
  }

  // Subscribe to WebSocket messages
  useEffect(() => {
    if (!liveMode) return
    
    const unsubscribe = subscribeToWebSocketMessages((event) => {
      lastMessageRef.current = event
      
      try {
        const parsed = JSON.parse(event.data)
        if (parsed?.type !== 'quote_update') return
        
        const payload = parsed.payload || parsed
        const messageSymbol = resolveQuoteSymbol(payload)
        
        // Debug: Log all quote updates to see what we're receiving
        if (process.env.NODE_ENV === 'development') {
          console.log(`[CandlestickChart] Received quote_update:`, {
            messageSymbol,
            chartSymbol: symbol,
            payload: {
              symbol: payload?.symbol,
              symbolId: payload?.symbolId,
              contractId: payload?.contractId,
              price: payload?.price,
              lastPrice: payload?.lastPrice,
            }
          })
        }
        
        // Use fuzzy symbol matching instead of exact match
        if (!messageSymbol || !matchesSymbol(messageSymbol, symbol)) {
          if (process.env.NODE_ENV === 'development') {
            console.debug(`[CandlestickChart] Quote symbol ${messageSymbol} does not match chart symbol ${symbol}`)
          }
          return
        }

        if (process.env.NODE_ENV === 'development') {
          console.log(`[CandlestickChart] ✓ Quote matched! ${messageSymbol} matches ${symbol}`)
        }

        const price =
          payload?.lastPrice ??
          payload?.price ??
          payload?.close ??
          payload?.bid ??
          payload?.ask

        if (typeof price === 'number' && price > 0) {
          // Validate price is reasonable compared to last candle
          if (candles.length > 0) {
            const lastClose = candles[candles.length - 1].close
            const priceDiff = Math.abs(price - lastClose)
            const priceDiffPercent = (priceDiff / lastClose) * 100
            // Reject prices that are more than 5% away from last candle (likely wrong contract)
            if (priceDiffPercent > 5) {
              console.warn(`[CandlestickChart] Rejecting quote price ${price} for ${messageSymbol} - too far from last candle close ${lastClose} (${priceDiffPercent.toFixed(2)}% difference)`)
              return
            }
          }
          
          // Calculate price change BEFORE updating state (use current candles)
          const previousClose = candles.length >= 2 
            ? candles[candles.length - 2].close 
            : candles.length >= 1 
              ? candles[candles.length - 1].open 
              : price
          const change = price - previousClose
          const changePercent = previousClose > 0 ? (change / previousClose) * 100 : 0
          
          // Update live price FIRST - this will trigger currentPrice memo update
          setLivePrice(price)
          
          // Immediately notify parent of price update with correct values
          if (onPriceUpdate) {
            onPriceUpdate(price, change, changePercent)
            if (process.env.NODE_ENV === 'development') {
              console.log(`[CandlestickChart] Updated price: ${price.toFixed(2)}, change: ${change.toFixed(2)}, change%: ${changePercent.toFixed(2)}%`)
            }
          }
          
          // Update candles to reflect new price
          setCandles((prev) => {
            if (!prev.length) return prev
            const updated = [...prev]
            const lastIndex = updated.length - 1
            const lastCandle = { ...updated[lastIndex] }
            
            lastCandle.close = price
            lastCandle.high = Math.max(lastCandle.high, price)
            lastCandle.low = Math.min(lastCandle.low, price)
            updated[lastIndex] = lastCandle
            return updated
          })
        } else {
          if (process.env.NODE_ENV === 'development') {
            console.warn(`[CandlestickChart] Invalid price from quote:`, { price, payload })
          }
        }
      } catch (err) {
        // Silently ignore parsing errors for non-JSON messages
        if (err instanceof SyntaxError) {
          return
        }
        console.error('Error processing live quote', err)
      }
    })
    
    return unsubscribe
  }, [liveMode, symbol, onPriceUpdate, matchesSymbol, candles])

  return (
    <div className="flex-1 bg-[#0a0a0a] flex flex-col border-b border-[#1a1a1a]">
      {/* Timeframe selector */}
      <div className="h-10 px-4 flex items-center gap-2 border-b border-[#1a1a1a]">
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf}
            onClick={() => onTimeframeChange(tf)}
            className={`px-3 py-1 text-xs font-medium rounded ${
              timeframe === tf
                ? 'bg-blue-600 text-white'
                : 'bg-[#1a1a1a] text-gray-400 hover:text-white'
            }`}
          >
            {tf}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-gray-400 uppercase tracking-wide">Mode</span>
          <div className="flex rounded overflow-hidden border border-[#1f2937]">
            <button
              className={`px-3 py-1 text-xs font-semibold ${
                liveMode ? 'bg-green-600 text-white' : 'bg-[#111827] text-gray-400'
              }`}
              onClick={() => setLiveMode(true)}
            >
              Live
            </button>
            <button
              className={`px-3 py-1 text-xs font-semibold ${
                !liveMode ? 'bg-blue-600 text-white' : 'bg-[#111827] text-gray-400'
              }`}
              onClick={() => setLiveMode(false)}
            >
              Candles
            </button>
          </div>
        </div>
      </div>

      {/* Chart area */}
      <div className="flex-1 relative min-h-[500px]">
        {liveMode && livePrice && (
          <div className="absolute top-4 right-4 z-20 px-2 py-1 bg-green-600/20 border border-green-500/60 text-green-200 text-xs rounded">
            Live {livePrice.toFixed(2)}
          </div>
        )}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500">
            Loading chart...
          </div>
        )}
        {!loading && error && (
          <div className="absolute inset-0 flex items-center justify-center text-red-500 text-sm">
            {error}
          </div>
        )}
        {!loading && !error && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 10, right: 30, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
              <XAxis
                dataKey="time"
                tick={{ fill: '#6b7280', fontSize: 11 }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={priceDomain}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                orientation="right"
                width={60}
              />
              <Tooltip
                contentStyle={{
                  background: '#111827',
                  border: '1px solid #1f2937',
                  color: '#f3f4f6',
                  borderRadius: '4px',
                }}
                labelStyle={{ color: '#9ca3af' }}
                formatter={(value: any, name: string) => {
                  if (name === 'volume') return [value, 'Volume']
                  return [typeof value === 'number' ? value.toFixed(2) : value, name]
                }}
              />
              {/* Simplified candlesticks using bars with custom shapes */}
              <Bar
                dataKey="value"
                fill="transparent"
                shape={renderCandlestick}
              />
              {/* Current price line */}
              {livePrice && livePrice > 0 && (
                <ReferenceLine
                  y={livePrice}
                  stroke="#3b82f6"
                  strokeWidth={1.5}
                  strokeDasharray="3 3"
                  label={{
                    value: `Current: ${livePrice.toFixed(2)}`,
                    position: 'right',
                    fill: '#3b82f6',
                    fontSize: 10,
                  }}
                />
              )}
              
              {/* Position entry markers with P/L zones */}
              {positions.map((position, idx) => {
                if (!position.entry_price || position.symbol?.toUpperCase() !== symbol.toUpperCase()) {
                  return null
                }
                const color = position.side === 'LONG' ? '#10b981' : '#ef4444'
                const currentPrice = position.current_price || livePrice || position.entry_price
                const unrealizedPnl = position.unrealized_pnl || 0
                const isProfit = unrealizedPnl >= 0
                
                return (
                  <g key={`position-${position.position_id || idx}`}>
                    {/* Entry price line */}
                    <ReferenceLine
                      y={position.entry_price}
                      stroke={color}
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      label={{
                        value: `ENTRY ${position.side} ${position.quantity} @ ${position.entry_price.toFixed(2)}`,
                        position: position.side === 'LONG' ? 'top' : 'bottom',
                        fill: color,
                        fontSize: 10,
                        fontWeight: 'bold',
                      }}
                    />
                    
                    {/* P/L visualization - colored zone between entry and current */}
                    {currentPrice !== position.entry_price && (
                      <ReferenceLine
                        y={currentPrice}
                        stroke={isProfit ? '#10b981' : '#ef4444'}
                        strokeWidth={1}
                        strokeDasharray="2 2"
                        label={{
                          value: `P&L: ${unrealizedPnl >= 0 ? '+' : ''}${unrealizedPnl.toFixed(2)} (${position.pnl_percent ? (position.pnl_percent >= 0 ? '+' : '') + position.pnl_percent.toFixed(2) + '%' : '--'})`,
                          position: position.side === 'LONG' ? (currentPrice > position.entry_price ? 'top' : 'bottom') : (currentPrice < position.entry_price ? 'top' : 'bottom'),
                          fill: isProfit ? '#10b981' : '#ef4444',
                          fontSize: 9,
                        }}
                      />
                    )}
                  </g>
                )
              })}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Volume bars */}
      <div className="h-20 border-t border-[#1a1a1a]">
        {!loading && !error && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 5, right: 30, bottom: 5, left: 10 }}>
              <XAxis dataKey="time" hide />
              <YAxis hide />
              <Bar dataKey="volume" radius={[2, 2, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.isUp ? '#10b981' : '#ef4444'} />
                ))}
              </Bar>
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
