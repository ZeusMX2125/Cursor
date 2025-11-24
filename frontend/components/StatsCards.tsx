'use client'

interface StatsCardsProps {
  dailyPnl: number
  winRate: number
  drawdown: number
  tradesToday: number
}

export default function StatsCards({
  dailyPnl,
  winRate,
  drawdown,
  tradesToday,
}: StatsCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-4">
      <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
        <div className="flex justify-between items-start mb-2">
          <div className="text-xs text-dark-text-muted">Daily P&L</div>
          <span className="text-lg">$</span>
        </div>
        <div className={`text-2xl font-bold ${dailyPnl >= 0 ? 'text-success' : 'text-danger'}`}>
          {dailyPnl >= 0 ? '+' : ''}${dailyPnl.toFixed(2)}
        </div>
      </div>

      <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
        <div className="flex justify-between items-start mb-2">
          <div className="text-xs text-dark-text-muted">Win Rate</div>
          <span className="text-lg">%</span>
        </div>
        <div className="text-2xl font-bold text-dark-text">{winRate.toFixed(1)}%</div>
      </div>

      <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
        <div className="flex justify-between items-start mb-2">
          <div className="text-xs text-dark-text-muted">Drawdown</div>
          <span className="text-lg">↓</span>
        </div>
        <div className="text-2xl font-bold text-danger">${Math.abs(drawdown).toFixed(2)}</div>
      </div>

      <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
        <div className="flex justify-between items-start mb-2">
          <div className="text-xs text-dark-text-muted">Trades Today</div>
          <span className="text-lg">↑</span>
        </div>
        <div className="text-2xl font-bold text-dark-text">{tradesToday} Active</div>
      </div>
    </div>
  )
}

