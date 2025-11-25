'use client'

import { useState, useEffect } from 'react'
import api from '@/lib/api'
import InstrumentSelector from '@/components/InstrumentSelector'
import { useContracts } from '@/contexts/ContractsContext'

export default function BacktestPanel() {
  const { contracts, getFirstContract, loading: contractsLoading, isValidSymbol } = useContracts()
  const [symbol, setSymbol] = useState<string>('')

  // Initialize symbol from first available ProjectX contract
  useEffect(() => {
    if (!contractsLoading && contracts.length > 0 && !symbol) {
      const firstContract = getFirstContract()
      if (firstContract?.symbol) {
        setSymbol(firstContract.symbol)
      }
    }
  }, [contractsLoading, contracts, symbol, getFirstContract])
  const [strategy, setStrategy] = useState('ict_silver_bullet')
  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<any>(null)

  const runBacktest = async () => {
    if (!symbol || !isValidSymbol(symbol)) {
      alert('Please select a valid contract symbol')
      return
    }
    setLoading(true)
    try {
      const response = await api.post('/api/backtest/run', {
        symbol,
        strategy,
        days
      })
      setResults(response.data)
    } catch (error) {
      console.error('Backtest failed', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-dark-card border border-dark-border p-4 rounded-lg">
      <h2 className="text-xl font-bold mb-4 text-white">Backtesting & Optimization</h2>
      
      <div className="flex gap-4 mb-4">
        <div className="flex-1">
          <InstrumentSelector
            value={symbol}
            onChange={setSymbol}
            disabled={loading || contractsLoading}
            showLabel
          />
        </div>
        <select 
          value={strategy} 
          onChange={(e) => setStrategy(e.target.value)}
          className="bg-dark-bg border border-dark-border p-2 rounded text-white"
        >
          <option value="ict_silver_bullet">ICT Silver Bullet</option>
          <option value="vwap_mean_reversion">VWAP Mean Reversion</option>
          <option value="momentum">Momentum</option>
        </select>
        <input 
          type="number"
          value={days} 
          onChange={(e) => setDays(parseInt(e.target.value))} 
          className="bg-dark-bg border border-dark-border p-2 rounded text-white w-24"
          placeholder="Days"
        />
        <button 
          onClick={runBacktest}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {loading ? 'Running...' : 'Run Backtest'}
        </button>
      </div>

      {results && (
        <div className="mt-4 space-y-2 text-gray-300">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-dark-bg p-3 rounded border border-dark-border">
                <div className="text-sm text-gray-500">Total P&L</div>
                <div className={`text-xl font-mono ${results.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    ${results.total_pnl?.toFixed(2)}
                </div>
            </div>
            <div className="bg-dark-bg p-3 rounded border border-dark-border">
                <div className="text-sm text-gray-500">Total Trades</div>
                <div className="text-xl font-mono text-white">{results.total_trades}</div>
            </div>
            <div className="bg-dark-bg p-3 rounded border border-dark-border">
                <div className="text-sm text-gray-500">Win Rate</div>
                <div className="text-xl font-mono text-white">{(results.win_rate * 100)?.toFixed(1)}%</div>
            </div>
          </div>
          
          {/* Rule Compliance */}
          {results.rule_compliance && (
             <div className="mt-4 p-3 bg-dark-bg border border-dark-border rounded">
                <h3 className="font-bold mb-2">Rule Compliance</h3>
                <div className="flex gap-4">
                    <span className={results.rule_compliance.daily_loss_violation ? 'text-red-500' : 'text-green-500'}>
                        Daily Loss: {results.rule_compliance.daily_loss_violation ? 'Failed' : 'Passed'}
                    </span>
                    <span className={results.rule_compliance.drawdown_violation ? 'text-red-500' : 'text-green-500'}>
                        Max Drawdown: {results.rule_compliance.drawdown_violation ? 'Failed' : 'Passed'}
                    </span>
                </div>
             </div>
          )}
        </div>
      )}
    </div>
  )
}

