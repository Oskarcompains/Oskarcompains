import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine
} from 'recharts'

function fmt(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{fmt(d.time)}</p>
      <p className="text-mono font-bold" style={{ color: d.pnl >= 0 ? '#4ade80' : '#f87171' }}>
        {d.pnl >= 0 ? '+' : ''}{d.pnl.toFixed(4)} USDC
      </p>
      {d.question && <p className="text-slate-500 mt-1 max-w-[200px] truncate">{d.question}</p>}
    </div>
  )
}

export function PnlChart({ history = [] }) {
  const isEmpty = history.length === 0

  if (isEmpty) {
    return (
      <div className="h-48 flex items-center justify-center">
        <p className="text-slate-600 text-sm">No trade history yet</p>
      </div>
    )
  }

  const lastPnl = history[history.length - 1]?.pnl ?? 0
  const color = lastPnl >= 0 ? '#22c55e' : '#ef4444'

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={history} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.2} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#22223a" vertical={false} />
        <XAxis
          dataKey="time"
          tickFormatter={fmt}
          tick={{ fill: '#475569', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#475569', fontSize: 10, fontFamily: 'JetBrains Mono' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={v => `$${v.toFixed(2)}`}
          width={56}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="#334155" strokeDasharray="4 4" />
        <Area
          type="monotone"
          dataKey="pnl"
          stroke={color}
          strokeWidth={2}
          fill="url(#pnlGrad)"
          dot={false}
          activeDot={{ r: 4, fill: color, stroke: '#0a0a0f', strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
