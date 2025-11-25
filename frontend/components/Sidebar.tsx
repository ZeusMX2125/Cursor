'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'

const menuItems = [
  { name: 'Dashboard', path: '/', icon: '📊' },
  { name: 'Trading', path: '/trading', icon: '📈' },
  { name: 'Active Trades', path: '/', icon: '💹' },
  { name: 'Bot Config', path: '/bot-config', icon: '⚙️' },
  { name: 'Analytics', path: '/analytics', icon: '📉' },
  { name: 'Settings', path: '/settings', icon: '🔧' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div
      className={`${collapsed ? 'w-20' : 'w-64'} bg-dark-card border-r border-dark-border flex flex-col transition-all duration-200`}
    >
      <div className="p-6 border-b border-dark-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-2xl font-bold">{collapsed ? 'A' : 'ALGOX'}</div>
          {!collapsed && <div className="text-xl">⚡</div>}
        </div>
        <button
          onClick={() => setCollapsed((prev) => !prev)}
          aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          className="w-7 h-7 rounded-full border border-dark-border text-dark-text-muted hover:text-white flex items-center justify-center"
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const isActive =
              pathname === item.path || (item.path === '/' && pathname === '/')
            return (
              <li key={item.name}>
                <Link
                  href={item.path}
                  className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'} px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary text-white'
                      : 'text-dark-text-muted hover:bg-dark-border'
                  }`}
                >
                  <span>{item.icon}</span>
                  {!collapsed && <span>{item.name}</span>}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="p-4 border-t border-dark-border">
        {collapsed ? (
          <div className="flex flex-col items-center gap-1 text-[10px] text-dark-text-muted">
            <div className="w-2 h-2 bg-success rounded-full"></div>
            <span>ON</span>
          </div>
        ) : (
          <>
            <div className="mb-2">
              <div className="text-xs text-dark-text-muted mb-1">STATUS</div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-success rounded-full"></div>
                <span className="text-sm font-medium">CONNECTED</span>
              </div>
            </div>
            <div className="text-xs text-dark-text-muted mb-2">TopstepX API</div>
            <button className="text-xs text-dark-text-muted hover:text-dark-text flex items-center gap-1">
              Disconnect <span>→</span>
            </button>
          </>
        )}
      </div>
    </div>
  )
}

