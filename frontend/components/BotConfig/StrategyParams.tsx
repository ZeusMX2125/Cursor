'use client'

interface StrategyParamsProps {
  config: any
  setConfig: (config: any) => void
}

export default function StrategyParams({ config, setConfig }: StrategyParamsProps) {
  return (
    <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
      <div className="text-lg font-semibold mb-2">Strategy Parameters</div>
      <div className="text-xs text-dark-text-muted mb-4">
        Define how the bot enters and exits trades.
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm mb-2">Strategy Type</label>
          <select
            value={config.strategyType}
            onChange={(e) => setConfig({ ...config, strategyType: e.target.value })}
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
          >
            <option value="momentum_scalp">Momentum Scalp (ES/NQ)</option>
            <option value="vwap_mean_reversion">VWAP Mean Reversion</option>
            <option value="opening_range_breakout">Opening Range Breakout</option>
            <option value="trend_following">Trend Following</option>
            <option value="ict_silver_bullet">ICT Silver Bullet</option>
          </select>
        </div>

        <div>
          <label className="block text-sm mb-2">Timeframe</label>
          <select
            value={config.timeframe}
            onChange={(e) => setConfig({ ...config, timeframe: e.target.value })}
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
          >
            <option value="1m">1 Minute</option>
            <option value="5m">5 Minute</option>
            <option value="15m">15 Minute</option>
            <option value="1h">1 Hour</option>
          </select>
        </div>

        <div>
          <label className="block text-sm mb-2">Contracts</label>
          <input
            type="number"
            value={config.contracts}
            onChange={(e) => setConfig({ ...config, contracts: parseInt(e.target.value) || 1 })}
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2"
            min={1}
            max={5}
          />
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-dark-border">
          <label className="text-sm">Take buy signals</label>
          <button
            onClick={() => setConfig({ ...config, longEntries: !config.longEntries })}
            className={`w-12 h-6 rounded-full transition-colors ${
              config.longEntries ? 'bg-primary' : 'bg-dark-border'
            }`}
          >
            <div
              className={`w-5 h-5 bg-white rounded-full transition-transform ${
                config.longEntries ? 'translate-x-6' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between">
          <label className="text-sm">Take sell signals</label>
          <button
            onClick={() => setConfig({ ...config, shortEntries: !config.shortEntries })}
            className={`w-12 h-6 rounded-full transition-colors ${
              config.shortEntries ? 'bg-primary' : 'bg-dark-border'
            }`}
          >
            <div
              className={`w-5 h-5 bg-white rounded-full transition-transform ${
                config.shortEntries ? 'translate-x-6' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>
      </div>
    </div>
  )
}

