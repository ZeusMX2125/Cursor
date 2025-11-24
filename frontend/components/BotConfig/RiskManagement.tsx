'use client'

interface RiskManagementProps {
  config: any
  setConfig: (config: any) => void
}

export default function RiskManagement({ config, setConfig }: RiskManagementProps) {
  return (
    <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
      <div className="text-lg font-semibold mb-2">Risk Management</div>
      <div className="text-xs text-dark-text-muted mb-4">
        Hard stops and limits to protect capital.
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm mb-2">Max Daily Loss ($)</label>
          <input
            type="number"
            value={config.maxDailyLoss}
            onChange={(e) => setConfig({ ...config, maxDailyLoss: parseFloat(e.target.value) || 0 })}
            className="w-full bg-dark-bg border border-danger rounded px-3 py-2"
          />
          <div className="text-xs text-dark-text-muted mt-1">
            Bot will hard stop if this loss is reached.
          </div>
        </div>

        <div>
          <label className="block text-sm mb-2">Daily Profit Target ($)</label>
          <input
            type="number"
            value={config.dailyProfitTarget}
            onChange={(e) => setConfig({ ...config, dailyProfitTarget: parseFloat(e.target.value) || 0 })}
            className="w-full bg-dark-bg border border-success rounded px-3 py-2"
          />
          <div className="text-xs text-dark-text-muted mt-1">
            Bot will stop trading after hitting this target.
          </div>
        </div>

        <div>
          <label className="block text-sm mb-2">Max Drawdown %</label>
          <input
            type="number"
            step="0.1"
            value={config.maxDrawdown}
            onChange={(e) => setConfig({ ...config, maxDrawdown: parseFloat(e.target.value) || 0 })}
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm mb-2">Trailing Stop (ticks)</label>
          <input
            type="number"
            value={config.trailingStop}
            onChange={(e) => setConfig({ ...config, trailingStop: parseInt(e.target.value) || 0 })}
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
          />
        </div>
      </div>
    </div>
  )
}

