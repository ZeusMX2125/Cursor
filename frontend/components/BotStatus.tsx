'use client'

interface BotStatusProps {
  strategy: string
  riskLevel: string
  targetPerDay: number
  goalProgress: number
}

export default function BotStatus({
  strategy,
  riskLevel,
  targetPerDay,
  goalProgress,
}: BotStatusProps) {
  return (
    <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
      <div className="text-lg font-semibold mb-4">BOT STATUS</div>

      <div className="space-y-4">
        <div>
          <div className="text-xs text-dark-text-muted mb-1">Strategy</div>
          <div className="text-sm font-medium">{strategy}</div>
        </div>

        <div>
          <div className="text-xs text-dark-text-muted mb-1">Risk Level</div>
          <div className="text-sm font-medium">{riskLevel}</div>
        </div>

        <div>
          <div className="text-xs text-dark-text-muted mb-1">Target/Day</div>
          <div className="text-sm font-medium">${targetPerDay.toFixed(2)}</div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs text-dark-text-muted">Goal Progress</div>
            <div className="text-sm font-medium">{goalProgress}%</div>
          </div>
          <div className="w-full bg-dark-border rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all"
              style={{ width: `${goalProgress}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

