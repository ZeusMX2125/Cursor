'use client'

import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { createChart, IChartApi, CandlestickData, Time, ColorType, LineWidth } from 'lightweight-charts'
import api from '@/lib/api'
import { subscribeToWebSocketMessages } from '@/lib/websocket'
import type { Position } from '@/types/dashboard'
import { useContracts } from '@/contexts/ContractsContext'
import { quoteMatchesChartSymbol, formatSymbolForDisplay } from '@/lib/contractUtils'

interface ProfessionalChartProps {
  symbol: string
  timeframe: string
  onTimeframeChange: (tf: string) => void
  onPriceUpdate?: (price: number, change: number, changePercent: number) => void
  positions?: Position[]
}

// Professional timeframe options - only allowed timeframes
const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '30m', label: '30m' },
  { value: '1h', label: '1h' },
  { value: '60m', label: '60m' },
  { value: '4h', label: '4h' },
  { value: '1d', label: '1D' },
]

interface Candle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export default function ProfessionalChart({
  symbol,
  timeframe,
  onTimeframeChange,
  onPriceUpdate,
  positions = []
}: ProfessionalChartProps) {
  const { contracts, getContractBySymbol } = useContracts()
  
  // Get contract for current symbol
  const chartContract = useMemo(() => {
    return getContractBySymbol(symbol)
  }, [symbol, getContractBySymbol])
  
  // Create lookup map for efficient matching
  const contractLookupMap = useMemo(() => {
    const map = new Map<string, typeof contracts[0]>()
    contracts.forEach(c => {
      if (c.symbol) {
        map.set(c.symbol.toUpperCase(), c)
      }
      if (c.baseSymbol) {
        map.set(c.baseSymbol.toUpperCase(), c)
      }
    })
    return map
  }, [contracts])
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const entryLinesRef = useRef<Map<string, any>>(new Map())
  const currentPriceLineRef = useRef<any>(null)
  const isInitialLoadRef = useRef(true)
  const lastBarTimeRef = useRef<Time | null>(null)
  const lastUpdateTimeRef = useRef<number>(0)
  const pendingPriceRef = useRef<number | null>(null)
  const updateIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const previousBarCloseRef = useRef<number>(0) // Store previous bar's close for price change calculation
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [priceChange, setPriceChange] = useState<number>(0)
  const [priceChangePercent, setPriceChangePercent] = useState<number>(0)
  const [isLive, setIsLive] = useState(false)

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current || chartRef.current) return

    const container = chartContainerRef.current
    
    // Wait for container to have dimensions
    const initChart = () => {
      if (!container || chartRef.current) return
      
      const width = container.clientWidth || 800
      const height = container.clientHeight || 500
      
      if (width === 0 || height === 0) {
        // Retry on next frame
        requestAnimationFrame(initChart)
        return
      }

      const chart = createChart(container, {
        layout: {
          background: { type: ColorType.Solid, color: '#0a0a0a' },
          textColor: '#9ca3af',
        },
        grid: {
          vertLines: { 
            color: '#1a1a1a',
            style: 0, // Solid
          },
          horzLines: { 
            color: '#1a1a1a',
            style: 0, // Solid
          },
        },
        width: width,
        height: height,
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderColor: '#1a1a1a',
        },
        rightPriceScale: {
          borderColor: '#1a1a1a',
          scaleMargins: {
            top: 0.1,
            bottom: 0.1,
          },
        },
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true,
          horzTouchDrag: true,
          vertTouchDrag: true,
        },
        handleScale: {
          axisPressedMouseMove: {
            time: true,
            price: true,
          },
          axisDoubleClickReset: true,
          mouseWheel: true,
          pinch: true,
        },
        crosshair: {
          mode: 1, // Normal mode
          vertLine: {
            color: '#3b82f6',
            width: 1,
            style: 2, // Dashed
            labelBackgroundColor: '#3b82f6',
          },
          horzLine: {
            color: '#3b82f6',
            width: 1,
            style: 2, // Dashed
            labelBackgroundColor: '#3b82f6',
          },
        },
      })

      // Add candlestick series (v4 API)
      const candlestickSeries = (chart as any).addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      })

      chartRef.current = chart
      candlestickSeriesRef.current = candlestickSeries

      // Handle resize
      const resizeObserver = new ResizeObserver(entries => {
        if (entries.length === 0 || !chartRef.current) return
        const { width, height } = entries[0].contentRect
        chartRef.current.applyOptions({ width, height })
      })
      resizeObserver.observe(container)
    }
    
    initChart()
    
    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
        candlestickSeriesRef.current = null
      }
    }
  }, [])

  // Load historical data
  const loadCandles = useCallback(async () => {
    if (!chartRef.current || !candlestickSeriesRef.current) return
    
    // Don't fetch if symbol is empty or invalid
    if (!symbol || !symbol.trim()) {
      setError('Please select a symbol')
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const response = await api.get('/api/market/candles', {
        params: {
          symbol,
          timeframe,
          bars: 1000, // Load more history for navigation
        }
      })

      const candles: Candle[] = (response.data.candles || []).map((c: any) => ({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        volume: 0, // Not used, but kept for interface compatibility
      }))

      if (candles.length === 0) {
        setError('No data available')
        return
      }

      // Convert to Lightweight Charts format and sort by time (ascending)
      const chartData: CandlestickData<Time>[] = candles
        .map(c => ({
          time: (new Date(c.time).getTime() / 1000) as Time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }))
        .sort((a, b) => (a.time as number) - (b.time as number))

      // Set data
      candlestickSeriesRef.current.setData(chartData)

      // Store the last bar time for new bar detection
      if (chartData.length > 0) {
        lastBarTimeRef.current = chartData[chartData.length - 1].time
      }

      // Calculate price change and initialize current price from last bar
      if (candles.length > 0) {
        const latest = candles[candles.length - 1]
        const previous = candles.length > 1 ? candles[candles.length - 2] : latest
        const change = latest.close - previous.close
        const changePercent = previous.close !== 0 ? (change / previous.close) * 100 : 0

        // Store previous bar close for accurate price change calculations on live updates
        previousBarCloseRef.current = previous.close

        // Initialize current price from last bar close - this ensures we start with correct price
        setCurrentPrice(latest.close)
        setPriceChange(change)
        setPriceChangePercent(changePercent)
        onPriceUpdate?.(latest.close, change, changePercent)
        
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Chart] Loaded ${candles.length} candles for ${symbol}, last bar close: ${latest.close.toFixed(2)}, previous close: ${previous.close.toFixed(2)}`)
        }
      }

      // Only fit content on initial load, preserve zoom/pan state on subsequent loads
      if (isInitialLoadRef.current) {
        chartRef.current.timeScale().fitContent()
        isInitialLoadRef.current = false
      }

      setLoading(false)
    } catch (err: any) {
      console.error('Error loading candles:', err)
      setError(err?.response?.data?.detail || err?.message || 'Failed to load chart data')
      setLoading(false)
    }
  }, [symbol, timeframe, onPriceUpdate])

  // Helper to check if position symbol matches chart symbol
  const positionMatchesSymbol = (posSymbol: string | undefined, chartSymbol: string): boolean => {
    if (!posSymbol) return false
    const pos = posSymbol.toUpperCase().replace(/[^A-Z0-9]/g, '')
    const chart = chartSymbol.toUpperCase().replace(/[^A-Z0-9]/g, '')
    
    // Direct match
    if (pos === chart) return true
    
    // Check if position symbol is contained in chart symbol or vice versa
    // e.g., "MES" matches "MESZ25" or "MES" matches "MES"
    if (chart.includes(pos) || pos.includes(chart)) return true
    
    // Check common futures symbol patterns (MES, MNQ, etc.)
    const posBase = pos.replace(/[0-9]/g, '')
    const chartBase = chart.replace(/[0-9]/g, '')
    if (posBase === chartBase && posBase.length >= 2) return true
    
    return false
  }

  // Update position markers
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return

    // Clear existing entry lines
    entryLinesRef.current.forEach(line => {
      candlestickSeriesRef.current.removePriceLine(line)
    })
    entryLinesRef.current.clear()

    // Add entry price lines for positions
    positions.forEach((position) => {
      // Check symbol match with improved logic
      if (!positionMatchesSymbol(position.symbol, symbol)) {
        return
      }

      // Use entry_price field
      const entryPrice = position.entry_price
      if (!entryPrice) {
        console.warn('Position missing entry_price:', position)
        return
      }

      const color = position.side === 'LONG' ? '#22c55e' : '#ef4444'
      
      // Calculate P&L if not provided
      const currentPriceForPnl = position.current_price || currentPrice
      const unrealizedPnl = position.unrealized_pnl ?? 
        (currentPriceForPnl && entryPrice ? 
          (position.side === 'LONG' ? (currentPriceForPnl - entryPrice) : (entryPrice - currentPriceForPnl)) * (position.quantity || 1) : 
          0)
      const pnlPercent = entryPrice && currentPriceForPnl ? 
        ((position.side === 'LONG' ? (currentPriceForPnl - entryPrice) : (entryPrice - currentPriceForPnl)) / entryPrice) * 100 : 
        0

      // Always show entry line
      const entryLine = candlestickSeriesRef.current.createPriceLine({
        price: entryPrice,
        color: color,
        lineWidth: 2 as LineWidth,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: `ENTRY ${position.side} ${position.quantity || 1} @ ${entryPrice.toFixed(2)}`,
      })
      entryLinesRef.current.set(`entry-${position.position_id || entryPrice}`, entryLine)

      // Show current price line with P&L info if we have current price
      if (currentPriceForPnl && Math.abs(currentPriceForPnl - entryPrice) > 0.01) {
        const pnlColor = unrealizedPnl >= 0 ? '#22c55e' : '#ef4444'
        const pnlLine = candlestickSeriesRef.current.createPriceLine({
          price: currentPriceForPnl,
          color: pnlColor,
          lineWidth: 1 as LineWidth,
          lineStyle: 1, // Dotted
          axisLabelVisible: true,
          title: `P&L: ${unrealizedPnl >= 0 ? '+' : ''}${unrealizedPnl.toFixed(2)} (${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%)`,
        })
        entryLinesRef.current.set(`pnl-${position.position_id || 'current'}`, pnlLine)
      }
    })
  }, [positions, symbol, candlestickSeriesRef.current, currentPrice])

  // Update current price line - ALWAYS show when we have real-time price data
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current || !currentPrice || currentPrice === 0) {
      // Remove line if no price
      if (currentPriceLineRef.current) {
        candlestickSeriesRef.current?.removePriceLine(currentPriceLineRef.current)
        currentPriceLineRef.current = null
      }
      return
    }

    const currentData = candlestickSeriesRef.current.data()
    if (!currentData || currentData.length === 0) return

    const lastBar = currentData[currentData.length - 1]
    if (!('close' in lastBar)) return

    // Always show the current price line when we have real-time data
    // Use previous bar's close for color determination (not the updating current bar)
    const prevBarClose = previousBarCloseRef.current || lastBar.close
    const priceColor = currentPrice >= prevBarClose ? '#22c55e' : '#ef4444'
    
    // Remove old current price line
    if (currentPriceLineRef.current) {
      candlestickSeriesRef.current.removePriceLine(currentPriceLineRef.current)
    }

    // Add/update current price line - always visible for real-time data
    currentPriceLineRef.current = candlestickSeriesRef.current.createPriceLine({
      price: currentPrice,
      color: priceColor,
      lineWidth: 2 as LineWidth, // Make it more visible
      lineStyle: 2, // Dashed
      axisLabelVisible: true,
      title: `LIVE: ${currentPrice.toFixed(2)}`,
    })
  }, [currentPrice, candlestickSeriesRef.current])

  // Helper to get timeframe duration in seconds
  const getTimeframeSeconds = (tf: string): number => {
    const multipliers: Record<string, number> = {
      '1m': 60,
      '5m': 300,
      '15m': 900,
      '30m': 1800,
      '1h': 3600,
      '60m': 3600, // Same as 1h
      '4h': 14400,
      '1d': 86400,
    }
    return multipliers[tf] || 60
  }

  // Function to update the chart bar with current price
  const updateChartBar = useCallback((price: number, forceUpdate: boolean = false) => {
    if (!candlestickSeriesRef.current) return

    const currentData = candlestickSeriesRef.current.data()
    if (!currentData || currentData.length === 0) return

    const lastBar = currentData[currentData.length - 1]
    if (!('open' in lastBar && 'high' in lastBar && 'low' in lastBar)) return

    const now = Math.floor(Date.now() / 1000)
    const timeframeSeconds = getTimeframeSeconds(timeframe)
    const lastBarTime = (lastBar.time as number)
    const currentBarStart = Math.floor(now / timeframeSeconds) * timeframeSeconds

    // Check if we need to create a new bar (new timeframe period)
    if (currentBarStart > lastBarTime) {
      // Create new bar
      const newBar: CandlestickData<Time> = {
        time: currentBarStart as Time,
        open: price,
        high: price,
        low: price,
        close: price,
      }
      candlestickSeriesRef.current.update(newBar)
      lastBarTimeRef.current = currentBarStart as Time
      setIsLive(true)
      lastUpdateTimeRef.current = Date.now()
    } else {
      // Update existing last bar - always update if forced, or if price changed
      const priceChanged = Math.abs(price - lastBar.close) > 0.01
      if (forceUpdate || priceChanged) {
        candlestickSeriesRef.current.update({
          time: lastBar.time,
          open: lastBar.open,
          high: Math.max(lastBar.high, price),
          low: Math.min(lastBar.low, price),
          close: price,
        })
        setIsLive(true)
        lastUpdateTimeRef.current = Date.now()
      }
    }
  }, [timeframe])

  // Periodic update interval (every 5 seconds)
  useEffect(() => {
    if (!candlestickSeriesRef.current || currentPrice === 0) {
      return
    }

    // Clear any existing interval
    if (updateIntervalRef.current) {
      clearInterval(updateIntervalRef.current)
    }

    // Update chart every 2 seconds with latest price for smooth real-time updates
    updateIntervalRef.current = setInterval(() => {
      if (pendingPriceRef.current !== null) {
        updateChartBar(pendingPriceRef.current, true)
        pendingPriceRef.current = null
      } else if (currentPrice > 0) {
        updateChartBar(currentPrice, true)
      }
    }, 2000) // 2 seconds for more responsive updates

    return () => {
      if (updateIntervalRef.current) {
        clearInterval(updateIntervalRef.current)
        updateIntervalRef.current = null
      }
    }
  }, [currentPrice, updateChartBar])

  // Enhanced symbol matching to handle various formats (MES vs MESZ25, F.US.MES, etc.)
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
    
    // Quote is base of chart symbol (MES matches MESZ25)
    if (chartNorm.startsWith(quoteBase) && quoteBase.length >= 2) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Chart] Symbol match: quote "${quoteSymbol}" (base: ${quoteBase}) matches chart "${chartSymbol}"`)
      }
      return true
    }
    
    // Chart is base of quote symbol (MESZ25 chart matches MES quote)
    if (quoteNorm.startsWith(chartBase) && chartBase.length >= 2) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Chart] Symbol match: quote "${quoteSymbol}" matches chart "${chartSymbol}" (base: ${chartBase})`)
      }
      return true
    }
    
    // Base symbols match (MES == MES from MESZ25)
    if (quoteBase === chartBase && quoteBase.length >= 2) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Chart] Symbol match: quote "${quoteSymbol}" and chart "${chartSymbol}" share base "${quoteBase}"`)
      }
      return true
    }
    
    // Try using contractUtils as fallback if contracts are available
    if (contracts.length > 0) {
      return quoteMatchesChartSymbol(quoteSymbol, chartSymbol, contracts)
    }
    
    return false
  }, [contracts])

  // Subscribe to real-time updates
  useEffect(() => {
    if (!candlestickSeriesRef.current) return

    const unsubscribe = subscribeToWebSocketMessages((event: MessageEvent) => {
      try {
        // Parse WebSocket message
        const message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data
        
        if (message?.type === 'quote_update') {
          const quote = message.payload || message
          const quoteSymbol = quote.symbol || quote.instrument || quote.instrumentSymbol || quote.symbolId
          
          // Check if this quote is for our symbol using improved matching
          if (quoteSymbol && !matchesSymbol(quoteSymbol, symbol)) {
            if (process.env.NODE_ENV === 'development') {
              console.debug(`[Chart] Quote symbol ${quoteSymbol} does not match chart symbol ${symbol}`)
            }
            return
          }
          
          if (process.env.NODE_ENV === 'development' && quoteSymbol) {
            console.log(`[Chart] Received quote for ${quoteSymbol} matching ${symbol}`)
          }

          const price = quote.lastPrice || quote.price || quote.close || quote.bid || quote.ask

          if (typeof price === 'number' && price > 0) {
            // Validate price is reasonable compared to last bar
            const currentData = candlestickSeriesRef.current.data()
            if (currentData && currentData.length > 0) {
              const lastBar = currentData[currentData.length - 1]
              if ('close' in lastBar) {
                const lastClose = lastBar.close as number
                // Reject prices that are more than 5% away from last bar (likely wrong contract)
                const priceDiff = Math.abs(price - lastClose)
                const priceDiffPercent = (priceDiff / lastClose) * 100
                if (priceDiffPercent > 5) {
                  console.warn(`[Chart] Rejecting quote price ${price} for ${quoteSymbol} - too far from last bar close ${lastClose} (${priceDiffPercent.toFixed(2)}% difference)`)
                  return // Skip this update - likely wrong contract
                }
              }
            }
            
            // ALWAYS update current price immediately for display - no throttling
            setCurrentPrice(price)
            
            // Update price change calculations using previous bar's close (not stale currentPrice state)
            const prevBarClose = previousBarCloseRef.current || price
            const change = price - prevBarClose
            const changePercent = prevBarClose > 0 ? (change / prevBarClose) * 100 : 0
            setPriceChange(change)
            setPriceChangePercent(changePercent)
            onPriceUpdate?.(price, change, changePercent)
            
            // Store pending price for periodic bar updates
            pendingPriceRef.current = price

            // Update bar immediately - more aggressive updates for real-time feel
            const priceChanged = Math.abs(price - (currentPrice || price)) > 0.01
            const timeSinceUpdate = Date.now() - lastUpdateTimeRef.current
            const shouldUpdateNow = priceChanged || timeSinceUpdate > 2000 // Update every 2 seconds or on any price change

            if (shouldUpdateNow) {
              updateChartBar(price, true)
              pendingPriceRef.current = null
            }
          }
        }
      } catch (err) {
        // Silently ignore parsing errors for non-JSON messages
        if (err instanceof SyntaxError) {
          return
        }
        console.error('Error processing WebSocket message:', err)
      }
    })

    return unsubscribe
  }, [symbol, timeframe, matchesSymbol, updateChartBar, onPriceUpdate])

  // Load data when symbol or timeframe changes
  useEffect(() => {
    isInitialLoadRef.current = true // Reset on symbol/timeframe change
    loadCandles()
  }, [symbol, timeframe])

  const displaySymbol = useMemo(() => formatSymbolForDisplay(symbol, chartContract || undefined), [symbol, chartContract])

  return (
    <div className="flex-1 bg-[#0a0a0a] flex flex-col border-b border-[#1a1a1a]">
      {/* Timeframe selector - Professional style */}
      <div className="h-12 px-4 flex items-center justify-between gap-4 border-b border-[#1a1a1a] bg-[#0f0f0f]">
        {/* Timeframes on the left */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.value}
              onClick={() => onTimeframeChange(tf.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                timeframe === tf.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-[#1a1a1a] text-gray-400 hover:text-white hover:bg-[#2a2a2a]'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
        
        {/* Price display on the right - with proper spacing to avoid overlap */}
        <div className="flex items-center gap-4 flex-shrink-0 ml-4">
          {currentPrice > 0 && (
            <div className="flex items-center gap-2">
              <div className="text-sm font-semibold whitespace-nowrap">
                <span className="text-white">{displaySymbol}</span>{' '}
                <span className={priceChange >= 0 ? 'text-green-500' : 'text-red-500'}>
                  {currentPrice.toFixed(2)}
                </span>
                {priceChangePercent !== 0 && (
                  <span className={`ml-2 text-xs ${priceChangePercent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} ({priceChangePercent >= 0 ? '+' : ''}{priceChangePercent.toFixed(2)}%)
                  </span>
                )}
              </div>
              {isLive && (
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" title="Live data streaming" />
                  <span className="text-xs text-gray-400">LIVE</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Chart area */}
      <div className="flex-1 relative min-h-[500px]" ref={chartContainerRef}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500 z-10 bg-[#0a0a0a]">
            Loading chart...
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-red-500 text-sm z-10 bg-[#0a0a0a]">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
