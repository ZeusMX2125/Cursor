'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

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

  return (
    <div className="w-64 bg-dark-card border-r border-dark-border flex flex-col">
      <div className="p-6 border-b border-dark-border">
        <div className="flex items-center gap-2">
          <div className="text-2xl font-bold">ALGOX</div>
          <div className="text-xl">⚡</div>
        </div>
      </div>

      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const isActive = pathname === item.path || 
              (item.path === '/' && pathname === '/')
            return (
              <li key={item.name}>
                <Link
                  href={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary text-white'
                      : 'text-dark-text-muted hover:bg-dark-border'
                  }`}
                >
                  <span>{item.icon}</span>
                  <span>{item.name}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="p-4 border-t border-dark-border">
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
      </div>
    </div>
  )
}

