import clsx from 'clsx'

export function MetricCard({ label, value, sub, icon: Icon, trend, color = 'green', large = false }) {
  const colors = {
    green:  { text: 'text-brand-400', bg: 'bg-brand-400/10', border: 'border-brand-400/20' },
    red:    { text: 'text-red-400',   bg: 'bg-red-400/10',   border: 'border-red-400/20'   },
    blue:   { text: 'text-blue-400',  bg: 'bg-blue-400/10',  border: 'border-blue-400/20'  },
    yellow: { text: 'text-yellow-400',bg: 'bg-yellow-400/10',border: 'border-yellow-400/20'},
    purple: { text: 'text-purple-400',bg: 'bg-purple-400/10',border: 'border-purple-400/20'},
  }
  const c = colors[color] ?? colors.green

  return (
    <div className={clsx('card border animate-fade-in', c.border, large && 'col-span-2 sm:col-span-1')}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">{label}</p>
          <p className={clsx('text-2xl font-bold text-mono', c.text)}>{value ?? '—'}</p>
          {sub && <p className="text-xs text-slate-500 mt-1 truncate">{sub}</p>}
        </div>
        {Icon && (
          <div className={clsx('p-2.5 rounded-lg ml-3 shrink-0', c.bg)}>
            <Icon size={18} className={c.text} />
          </div>
        )}
      </div>
      {trend !== undefined && (
        <div className={clsx(
          'mt-3 pt-3 border-t border-surface-600 text-xs font-medium',
          trend >= 0 ? 'text-brand-400' : 'text-red-400'
        )}>
          {trend >= 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(2)}% vs yesterday
        </div>
      )}
    </div>
  )
}
