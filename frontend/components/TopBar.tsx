'use client'

import { useEffect, useState, useMemo } from 'react'
import type { ReactNode } from 'react'

// Helper function to format symbol for display (convert ES to MES for micro contracts)
function formatSymbolForDisplay(symbol: string): string {
  const upperSymbol = symbol.toUpperCase()
  // If symbol already starts with MES, return as is
  if (upperSymbol.startsWith('MES')) {
    return upperSymbol
  }
  // If symbol starts with ES and is a micro contract (typically has month code), show as MES
  if (upperSymbol.startsWith('ES') && upperSymbol.length >= 4) {
    // Check if it's likely a micro contract (has month/year codes like Z25, H26, etc.)
    const monthCode = upperSymbol.charAt(2)
    if (monthCode && /[FGHJKMNQUVXZ]/.test(monthCode)) {
      return 'M' + upperSymbol
    }
  }
  return upperSymbol
}

interface TopBarProps {
  symbol: string
  instrumentName?: string
  price?: number
  priceChange?: number
  priceChangePercent?: number
  wsConnected?: boolean
  mdConnected?: boolean
  ordConnected?: boolean
  simMode?: boolean
  onSymbolChange?: (symbol: string) => void
  instrumentSelector?: ReactNode
}

// Client-only status indicator to prevent hydration mismatch
function StatusIndicator({ connected, label, title }: { connected: boolean; label: string; title?: string }) {
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
  }, [])

  // Render neutral gray dot until mounted to match server-side default
  const cls = mounted && connected ? 'bg-green-500' : 'bg-gray-500'
  const animate = mounted && connected ? 'animate-pulse' : ''
  
  return (
    <div 
      className="flex items-center gap-2 cursor-help" 
      title={title}
    >
      <div className={`w-2 h-2 rounded-full ${cls} ${animate}`} />
      <span className="text-gray-400">{label}</span>
    </div>
  )
}

export default function TopBar({
  symbol,
  instrumentName,
  price,
  priceChange,
  priceChangePercent,
  wsConnected = true,
  mdConnected = true,
  ordConnected = true,
  simMode = true,
  onSymbolChange,
  instrumentSelector,
}: TopBarProps) {
  const displaySymbol = useMemo(() => formatSymbolForDisplay(symbol), [symbol])
  
  return (
    <div className="h-12 bg-[#0a0a0a] border-b border-[#1a1a1a] px-4 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <div className="text-xl font-bold text-white">ALGOX</div>
        {instrumentSelector ? (
          <div className="flex flex-col gap-1">
            {instrumentSelector}
            <div className="text-xs text-gray-500">
              {instrumentName || 'Select an instrument'}
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-300 font-medium">
            {displaySymbol} {instrumentName ? `- ${instrumentName}` : ''}
          </div>
        )}
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4 text-xs">
          <StatusIndicator 
            connected={wsConnected} 
            label="WS"
            title={wsConnected ? 'WebSocket Connected' : 'WebSocket Disconnected - Check backend is running on port 8000'}
          />
          <StatusIndicator connected={mdConnected} label="MD" />
          <StatusIndicator connected={ordConnected} label="ORD" />
        </div>

        {simMode && (
          <div className="px-3 py-1 bg-yellow-500/20 border border-yellow-500/50 rounded text-xs text-yellow-500 font-semibold">
            SIM
          </div>
        )}

        <div className="flex items-center gap-3">
          <button className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </button>
          <button className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          <button className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white">
            <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-bold">
              U
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}

