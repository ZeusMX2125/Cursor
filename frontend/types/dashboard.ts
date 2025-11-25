export interface Position {
  id?: string | number
  position_id?: string
  contract_id?: string
  symbol: string
  side: string
  quantity: number
  entry_price: number
  current_price?: number
  unrealized_pnl?: number
  realized_pnl?: number
  entry_value?: number
  current_value?: number
  pnl_percent?: number
  tick_size?: number
  tick_value?: number
  point_value?: number
  account_id?: string
  entry_time?: string
}

export interface PendingOrder {
  order_id: string
  symbol: string
  side: string
  order_type: string
  quantity: number
  price?: number
  stop_price?: number
  status: string
  created_at?: string
}

export interface ManualOrder extends PendingOrder {
  time_in_force?: string
  take_profit?: number
  timestamp?: string
}

export interface AccountMetrics {
  daily_pnl: number
  win_rate: number
  profit_factor: number
  trades_today: number
  total_trades: number
}

export interface AccountSnapshot {
  account_id: string
  name: string
  stage: string
  size: string
  running: boolean
  paper_trading: boolean
  enabled: boolean
  account_size: number
  daily_loss_limit: number
  profit_target: number
  balance: number
  buying_power: number
  metrics: AccountMetrics
  positions: Position[]
  pending_orders: PendingOrder[]
  manual_orders: ManualOrder[]
  strategies: {
    configured: string[]
    active?: string | null
    agent: string
  }
}

export interface ProjectXAccount {
  id: number | string
  name: string
  balance: number
  canTrade?: boolean
  simulated?: boolean
  isVisible?: boolean
}

export interface ProjectXOrder {
  orderId?: number
  id?: number
  accountId?: number
  contractId?: string
  symbolId?: string
  status?: number
  type?: number
  side?: number
  size?: number
  limitPrice?: number
  stopPrice?: number
  creationTimestamp?: string
  updateTimestamp?: string
}

export interface ProjectXTrade {
  id?: number
  accountId?: number
  contractId?: string
  price?: number
  profitAndLoss?: number
  fees?: number
  side?: number
  size?: number
  creationTimestamp?: string
}

export interface ProjectXOrders {
  open: ProjectXOrder[]
  recent: ProjectXOrder[]
}

export interface ProjectXState {
  accounts: ProjectXAccount[]
  positions: Position[]
  orders: ProjectXOrders
  trades: ProjectXTrade[]
}

export interface DashboardMetricsSummary {
  dailyPnl: number
  winRate: number
  drawdown: number
  tradesToday: number
  openPositions: number
  pendingOrders: number
  runningAccounts: number
}

export interface DashboardState {
  accounts: AccountSnapshot[]
  projectx: ProjectXState
  metrics: DashboardMetricsSummary
  timestamp: string
}

