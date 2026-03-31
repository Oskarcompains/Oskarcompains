import clsx from 'clsx'

export function StatusBadge({ running }) {
  return (
    <span className={clsx(
      'badge',
      running
        ? 'bg-brand-400/10 text-brand-400 border border-brand-400/30'
        : 'bg-slate-500/10 text-slate-400 border border-slate-500/30'
    )}>
      <span className={clsx(
        'w-1.5 h-1.5 rounded-full',
        running ? 'bg-brand-400 animate-pulse' : 'bg-slate-500'
      )} />
      {running ? 'LIVE' : 'OFFLINE'}
    </span>
  )
}
