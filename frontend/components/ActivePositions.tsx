'use client'

interface Position {
  id: string
  symbol: string
  side: 'LONG' | 'SHORT'
  entry: number
  pnl: number
}

interface ActivePositionsProps {
  positions: Position[]
}

export default function ActivePositions({ positions }: ActivePositionsProps) {
  const openCount = positions.length

  return (
    <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
      <div className="flex justify-between items-center mb-4">
        <div className="text-lg font-semibold">ACTIVE POSITIONS</div>
        <div className="bg-success text-white px-3 py-1 rounded text-sm font-medium">
          {openCount} OPEN
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs text-dark-text-muted border-b border-dark-border">
              <th className="pb-2">ID</th>
              <th className="pb-2">SYMBOL</th>
              <th className="pb-2">SIDE</th>
              <th className="pb-2">ENTRY</th>
              <th className="pb-2 text-right">PNL</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-dark-text-muted">
                  No open positions
                </td>
              </tr>
            ) : (
              positions.map((position) => (
                <tr key={position.id} className="border-b border-dark-border">
                  <td className="py-3 text-sm">{position.id}</td>
                  <td className="py-3 text-sm">{position.symbol}</td>
                  <td className="py-3">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        position.side === 'LONG'
                          ? 'bg-success/20 text-success'
                          : 'bg-danger/20 text-danger'
                      }`}
                    >
                      {position.side}
                    </span>
                  </td>
                  <td className="py-3 text-sm">{position.entry.toFixed(2)}</td>
                  <td className={`py-3 text-sm text-right font-medium ${
                    position.pnl >= 0 ? 'text-success' : 'text-danger'
                  }`}>
                    {position.pnl >= 0 ? '+' : ''}{position.pnl.toFixed(2)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

