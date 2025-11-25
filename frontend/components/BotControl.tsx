'use client'

import { useState, useEffect, useRef } from 'react'
import api from '@/lib/api'
import type { AccountSnapshot } from '@/types/dashboard'

interface BotControlProps {
  account?: AccountSnapshot
  onStatusChange?: () => void
}

const STAGES = [
  { value: 'practice', label: 'Practice' },
  { value: 'combine', label: 'Combine' },
  { value: 'express_funded', label: 'Express Funded' },
]

const SIZES = [
  { value: '50k', label: '$50K' },
  { value: '100k', label: '$100K' },
  { value: '150k', label: '$150K' },
]

const STRATEGIES = [
  { value: 'ict_silver_bullet', label: 'ICT Silver Bullet' },
  { value: 'vwap_mean_reversion', label: 'VWAP Mean Reversion' },
  { value: 'opening_range_breakout', label: 'Opening Range Breakout' },
  { value: 'trend_following', label: 'Trend Following' },
]

const AI_AGENT_TYPES = [
  { value: 'rule_based', label: 'Rule Based' },
  { value: 'ml_confirmation', label: 'ML Confirmation' },
  { value: 'rl_agent', label: 'RL Agent' },
]

export default function BotControl({ account, onStatusChange }: BotControlProps) {
  const [botRunning, setBotRunning] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [activeStrategy, setActiveStrategy] = useState<string | null>(null)
  const [accountNotFound, setAccountNotFound] = useState(false)
  const [isBotManaged, setIsBotManaged] = useState<boolean | null>(null)
  const [botHealth, setBotHealth] = useState<any>(null)
  const [showActivity, setShowActivity] = useState(false)
  const [activity, setActivity] = useState<any[]>([])
  const [showConfigForm, setShowConfigForm] = useState(false)
  const [config, setConfig] = useState({
    account_id: '',
    name: '',
    stage: 'practice',
    size: '50k',
    username: '',
    api_key: '',
    enabled_strategies: [] as string[],
    ai_agent_type: 'rule_based',
    paper_trading: true,
    enabled: true,
  })
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const activityIntervalRef = useRef<NodeJS.Timeout | null>(null)
  
  const fetchActivity = async () => {
    if (!account?.account_id) return
    try {
      const response = await api.get(`/api/accounts/${account.account_id}/activity`, {
        params: { limit: 20 }
      })
      setActivity(response.data.activities || [])
    } catch (error) {
      console.error('Failed to fetch bot activity:', error)
    }
  }

  // Check bot status
  useEffect(() => {
    if (!account?.account_id) {
      setAccountNotFound(false)
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }
    
    // Reset accountNotFound when account changes
    setAccountNotFound(false)
    setIsBotManaged(null)
    
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    
    const checkStatus = async () => {
      try {
        const response = await api.get(`/api/accounts/${account.account_id}/status`)
        const data = response.data
        
        // Check if account is bot-managed
        if (data.bot_managed === false) {
          // This is a ProjectX account but not configured in bot manager
          setBotRunning(false)
          setActiveStrategy(null)
          setAccountNotFound(false) // Account exists, just not bot-managed
          setIsBotManaged(false)
          // Continue polling in case it gets added to bot manager
        } else {
          // Bot-managed account
          setBotRunning(data.running || false)
          setActiveStrategy(data.active_strategy || null)
          setAccountNotFound(false)
          setIsBotManaged(true)
          setBotHealth(data.bot_health || null)
          
          // Fetch activity if bot is running
          if (data.running && showActivity) {
            fetchActivity()
          }
        }
      } catch (error: any) {
        // If 404, account truly doesn't exist - stop polling
        if (error?.response?.status === 404) {
          setBotRunning(false)
          setActiveStrategy(null)
          setAccountNotFound(true)
          setIsBotManaged(null)
          // Stop polling by clearing interval
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
        } else {
          console.log('Status check failed:', error?.response?.data?.detail || error?.message)
        }
      }
    }
    
    checkStatus()
    
    // Set up polling interval
    intervalRef.current = setInterval(checkStatus, 5000)
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      if (activityIntervalRef.current) {
        clearInterval(activityIntervalRef.current)
        activityIntervalRef.current = null
      }
    }
  }, [account?.account_id])

  // Initialize config when account changes
  useEffect(() => {
    if (account && isBotManaged === false) {
      setConfig({
        account_id: account.account_id || '',
        name: account.accountName || account.name || `Account ${account.account_id}`,
        stage: 'practice',
        size: '50k',
        username: '', // Optional - will use global credentials if empty
        api_key: '', // Optional - will use global credentials if empty
        enabled_strategies: [],
        ai_agent_type: 'rule_based',
        paper_trading: account.paper_trading ?? true,
        enabled: true,
      })
    }
  }, [account, isBotManaged])

  const handleToggle = async () => {
    if (!account?.account_id) {
      setMessage('Select an account first')
      return
    }

    setLoading(true)
    setMessage(null)

    try {
      if (botRunning) {
        await api.post(`/api/accounts/${account.account_id}/stop`)
        setBotRunning(false)
        setMessage('Bot deactivated')
      } else {
        await api.post(`/api/accounts/${account.account_id}/start`)
        setBotRunning(true)
        setMessage('Bot activated')
      }
      onStatusChange?.()
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.message || 'Failed to toggle bot'
      setMessage(errorMsg)
      console.error('Bot toggle error:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleStrategy = (strategy: string) => {
    setConfig(prev => ({
      ...prev,
      enabled_strategies: prev.enabled_strategies.includes(strategy)
        ? prev.enabled_strategies.filter(s => s !== strategy)
        : [...prev.enabled_strategies, strategy]
    }))
  }

  const addAccountToBotManager = async () => {
    if (!config.account_id || !config.name) {
      setMessage('Please fill in account ID and name')
      return
    }

    setLoading(true)
    setMessage(null)

    try {
      const accountData: any = {
        account_id: config.account_id,
        name: config.name,
        stage: config.stage,
        size: config.size,
        enabled_strategies: config.enabled_strategies.length > 0 
          ? config.enabled_strategies 
          : ['ict_silver_bullet'],
        ai_agent_type: config.ai_agent_type,
        paper_trading: config.paper_trading,
        enabled: config.enabled,
      }

      // Only include username/api_key if provided
      if (config.username) {
        accountData.username = config.username
      }
      if (config.api_key) {
        accountData.api_key = config.api_key
      }

      const response = await api.post('/api/accounts/add', accountData)
      
      setMessage(response.data.message || 'Account added successfully!')
      setShowConfigForm(false)
      
      // Refresh status after a short delay
      setTimeout(() => {
        onStatusChange?.()
      }, 1000)
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.message || 'Failed to add account'
      setMessage(errorMsg)
      console.error('Error adding account:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-[#0a0a0a] border-b border-[#1a1a1a] p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-white mb-3">Bot Control</h3>
        
        {message && (
          <div className={`text-xs p-2 rounded mb-2 ${
            message.includes('activated') || message.includes('success')
              ? 'bg-green-500/20 text-green-400'
              : message.includes('deactivated')
              ? 'bg-yellow-500/20 text-yellow-400'
              : 'bg-red-500/20 text-red-400'
          }`}>
            {message}
          </div>
        )}

        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-xs text-gray-400">Status</div>
            <div className="flex items-center gap-2 mt-1">
              <div className={`w-2 h-2 rounded-full ${botRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
              <span className="text-sm font-semibold text-white">
                {botRunning ? 'RUNNING' : 'STOPPED'}
              </span>
            </div>
          </div>
          
          <button
            onClick={handleToggle}
            disabled={loading || !account?.account_id || isBotManaged === false}
            className={`px-4 py-2 rounded font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              botRunning
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
            title={
              !account?.account_id 
                ? 'Select an account in the Accounts panel above' 
                : isBotManaged === false
                ? 'Account not configured in bot manager'
                : ''
            }
          >
            {loading ? '...' : botRunning ? 'Deactivate Bot' : 'Activate Bot'}
          </button>
        </div>

        {isBotManaged === false && (
          <div className="mt-2 p-3 bg-yellow-500/20 border border-yellow-500/40 rounded">
            <div className="text-xs text-yellow-400 mb-2">
              This account is not configured in the bot manager. Configure it below to generate the YAML configuration.
            </div>
            <button
              onClick={() => setShowConfigForm(!showConfigForm)}
              className="text-xs px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors"
            >
              {showConfigForm ? 'Hide Configuration' : 'Configure Account'}
            </button>
            
            {showConfigForm && (
              <div className="mt-3 space-y-3">
                <div>
                  <label className="text-xs text-gray-300 block mb-1">Account ID</label>
                  <input
                    type="text"
                    value={config.account_id}
                    onChange={(e) => setConfig(prev => ({ ...prev, account_id: e.target.value }))}
                    className="w-full px-2 py-1.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm text-white"
                    placeholder="e.g., practice_50k_1"
                  />
                </div>
                
                <div>
                  <label className="text-xs text-gray-300 block mb-1">Account Name</label>
                  <input
                    type="text"
                    value={config.name}
                    onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-2 py-1.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm text-white"
                    placeholder="e.g., Practice $50K"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-gray-300 block mb-1">Stage</label>
                    <select
                      value={config.stage}
                      onChange={(e) => setConfig(prev => ({ ...prev, stage: e.target.value }))}
                      className="w-full px-2 py-1.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm text-white"
                    >
                      {STAGES.map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="text-xs text-gray-300 block mb-1">Size</label>
                    <select
                      value={config.size}
                      onChange={(e) => setConfig(prev => ({ ...prev, size: e.target.value }))}
                      className="w-full px-2 py-1.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm text-white"
                    >
                      {SIZES.map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                
                <div>
                  <label className="text-xs text-gray-300 block mb-1">
                    Username <span className="text-gray-500 text-[10px]">(optional - uses global credentials if empty)</span>
                  </label>
                  <input
                    type="text"
                    value={config.username}
                    onChange={(e) => setConfig(prev => ({ ...prev, username: e.target.value }))}
                    className="w-full px-2 py-1.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm text-white"
                    placeholder="Leave empty to use global credentials"
                  />
                </div>
                
                <div>
                  <label className="text-xs text-gray-300 block mb-1">
                    API Key <span className="text-gray-500 text-[10px]">(optional - uses global credentials if empty)</span>
                  </label>
                  <input
                    type="password"
                    value={config.api_key}
                    onChange={(e) => setConfig(prev => ({ ...prev, api_key: e.target.value }))}
                    className="w-full px-2 py-1.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm text-white"
                    placeholder="Leave empty to use global credentials"
                  />
                </div>
                
                <div>
                  <label className="text-xs text-gray-300 block mb-1">Strategies</label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {STRATEGIES.map(s => (
                      <label key={s.value} className="flex items-center gap-1.5 text-xs text-gray-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={config.enabled_strategies.includes(s.value)}
                          onChange={() => toggleStrategy(s.value)}
                          className="w-3 h-3 rounded"
                        />
                        <span>{s.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
                
                <div>
                  <label className="text-xs text-gray-300 block mb-1">AI Agent Type</label>
                  <select
                    value={config.ai_agent_type}
                    onChange={(e) => setConfig(prev => ({ ...prev, ai_agent_type: e.target.value }))}
                    className="w-full px-2 py-1.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm text-white"
                  >
                    {AI_AGENT_TYPES.map(a => (
                      <option key={a.value} value={a.value}>{a.label}</option>
                    ))}
                  </select>
                </div>
                
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.paper_trading}
                      onChange={(e) => setConfig(prev => ({ ...prev, paper_trading: e.target.checked }))}
                      className="w-3 h-3 rounded"
                    />
                    <span>Paper Trading</span>
                  </label>
                  
                  <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.enabled}
                      onChange={(e) => setConfig(prev => ({ ...prev, enabled: e.target.checked }))}
                      className="w-3 h-3 rounded"
                    />
                    <span>Enabled</span>
                  </label>
                </div>
                
                <button
                  onClick={addAccountToBotManager}
                  disabled={loading || !config.account_id || !config.name}
                  className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium rounded transition-colors"
                >
                  {loading ? 'Adding Account...' : 'Add Account to Bot Manager'}
                </button>
              </div>
            )}
          </div>
        )}

        {accountNotFound && (
          <div className="mt-2 p-2 bg-red-500/20 border border-red-500/40 rounded">
            <div className="text-xs text-red-400">
              Account not found. Status polling stopped.
            </div>
          </div>
        )}

        {activeStrategy && botRunning && (
          <div className="mt-2 p-2 bg-blue-500/20 border border-blue-500/40 rounded">
            <div className="text-xs text-blue-400">
              Active Strategy: <span className="font-semibold">{activeStrategy}</span>
            </div>
          </div>
        )}

        {botHealth && (
          <div className="mt-2 p-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-300">Bot Verification</span>
              <span className={`text-xs font-semibold ${botHealth.verified ? 'text-green-500' : 'text-yellow-500'}`}>
                {botHealth.verified ? '✓ VERIFIED' : '⚠ CHECKING'}
              </span>
            </div>
            {botHealth.components && (
              <div className="text-xs text-gray-400 space-y-0.5">
                <div>Components: {Object.values(botHealth.components).filter(Boolean).length}/{Object.keys(botHealth.components).length} active</div>
                {botHealth.recent_activity_count > 0 && (
                  <div>Recent activity: {botHealth.recent_activity_count} events</div>
                )}
              </div>
            )}
          </div>
        )}

        {botRunning && (
          <div className="mt-2">
            <button
              onClick={() => {
                setShowActivity(!showActivity)
                if (!showActivity) {
                  fetchActivity()
                  activityIntervalRef.current = setInterval(fetchActivity, 10000) // Refresh every 10s
                } else {
                  if (activityIntervalRef.current) {
                    clearInterval(activityIntervalRef.current)
                    activityIntervalRef.current = null
                  }
                }
              }}
              className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
            >
              {showActivity ? 'Hide' : 'Show'} Activity Log
            </button>
          </div>
        )}

        {showActivity && botRunning && (
          <div className="mt-2 p-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded max-h-48 overflow-y-auto">
            <div className="text-xs font-semibold text-gray-300 mb-2">Recent Activity</div>
            {activity.length === 0 ? (
              <div className="text-xs text-gray-500">No activity yet. Bot is monitoring markets...</div>
            ) : (
              <div className="space-y-1">
                {activity.map((item: any, idx: number) => (
                  <div key={idx} className="text-xs text-gray-400 border-b border-[#2a2a2a] pb-1">
                    <div className="flex items-center justify-between">
                      <span className={item.type === 'bot_started' ? 'text-green-400' : item.type === 'trade_executed' ? 'text-blue-400' : 'text-gray-400'}>
                        {item.type?.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <span className="text-gray-500">
                        {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : ''}
                      </span>
                    </div>
                    {item.message && <div className="text-gray-500 mt-0.5">{item.message}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {botRunning && (
          <div className="mt-2 text-xs text-gray-400">
            Bot is actively monitoring markets and executing trades based on active strategies.
          </div>
        )}
      </div>
    </div>
  )
}

