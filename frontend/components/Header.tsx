'use client'

import { useEffect, useState } from 'react'

interface HeaderProps {
  accountBalance: number
}

export default function Header({ accountBalance }: HeaderProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // During SSR and initial render, show 0.00 to match server
  // After mount, show the actual balance to avoid hydration mismatch
  const displayBalance = mounted ? accountBalance : 0

  return (
    <header className="bg-dark-card border-b border-dark-border px-6 py-4 flex justify-between items-center">
      <div></div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <div className="text-xs text-dark-text-muted">ACCOUNT BALANCE</div>
          <div className="text-xl font-bold">${displayBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        </div>
        <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center text-white font-bold">
          TR
        </div>
      </div>
    </header>
  )
}

