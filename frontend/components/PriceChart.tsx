'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface PriceChartProps {
  symbol: string
}

// Mock data - replace with real data from WebSocket
const mockData = [
  { time: '09:30', price: 4115 },
  { time: '09:35', price: 4120 },
  { time: '09:40', price: 4125 },
  { time: '09:45', price: 4130 },
  { time: '09:50', price: 4135 },
  { time: '09:55', price: 4140 },
  { time: '10:00', price: 4145 },
  { time: '10:05', price: 4150 },
  { time: '10:10', price: 4155 },
  { time: '10:15', price: 4160 },
  { time: '10:20', price: 4165 },
]

export default function PriceChart({ symbol }: PriceChartProps) {
  return (
    <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
      <div className="flex justify-between items-center mb-4">
        <div>
          <div className="text-lg font-semibold">{symbol}</div>
          <div className="text-xs text-dark-text-muted">S&P 500 E-Mini</div>
        </div>
        <div className="flex gap-2">
          {['1m', '5m', '15m', '1h'].map((tf) => (
            <button
              key={tf}
              className={`px-3 py-1 rounded text-sm ${
                tf === '5m'
                  ? 'bg-primary text-white'
                  : 'bg-dark-border text-dark-text-muted hover:bg-dark-border/80'
              }`}
            >
              {tf}
            </button>
          ))}
          <button className="px-3 py-1 rounded text-sm bg-dark-border text-dark-text-muted hover:bg-dark-border/80">
            ⛶
          </button>
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={mockData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
            <XAxis dataKey="time" stroke="#a0a0a0" />
            <YAxis stroke="#a0a0a0" domain={[4110, 4170]} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1a1a1a',
                border: '1px solid #2a2a2a',
                color: '#e0e0e0',
              }}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

