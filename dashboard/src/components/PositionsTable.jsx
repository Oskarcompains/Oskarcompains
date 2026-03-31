import clsx from 'clsx'
import { TrendingUp, TrendingDown } from 'lucide-react'

function fmt(ts) {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

export function PositionsTable({ positions = [] }) {
  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-32">
        <p className="text-sm text-slate-600">No open positions</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-slate-500 uppercase tracking-wider">
            <th className="text-left pb-3 pr-4 font-medium">Market</th>
            <th className="text-right pb-3 pr-4 font-medium">YES</th>
            <th className="text-right pb-3 pr-4 font-medium">NO</th>
            <th className="text-right pb-3 pr-4 font-medium">Cost</th>
            <th className="text-right pb-3 pr-4 font-medium">Payout</th>
            <th className="text-right pb-3 font-medium">P&L</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-700">
          {positions.map((p, i) => {
            const pnl = p.unrealized_pnl ?? 0
            const isPos = pnl >= 0
            return (
              <tr key={i} className="hover:bg-surface-700/40 transition-colors">
                <td className="py-3 pr-4">
                  <p className="text-slate-200 truncate max-w-[220px]">{p.question}</p>
                  <p className="text-xs text-slate-600 text-mono mt-0.5">{p.condition_id}</p>
                </td>
                <td className="py-3 pr-4 text-right text-mono text-slate-400">
                  {p.yes_price?.toFixed(4)}
                </td>
                <td className="py-3 pr-4 text-right text-mono text-slate-400">
                  {p.no_price?.toFixed(4)}
                </td>
                <td className="py-3 pr-4 text-right text-mono text-slate-300">
                  ${p.cost?.toFixed(4)}
                </td>
                <td className="py-3 pr-4 text-right text-mono text-slate-300">
                  ${p.expected_payout?.toFixed(4)}
                </td>
                <td className="py-3 text-right">
                  <div className={clsx(
                    'inline-flex items-center gap-1 text-mono font-medium',
                    isPos ? 'text-brand-400' : 'text-red-400'
                  )}>
                    {isPos
                      ? <TrendingUp size={12} />
                      : <TrendingDown size={12} />
                    }
                    {isPos ? '+' : ''}{pnl.toFixed(4)}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
