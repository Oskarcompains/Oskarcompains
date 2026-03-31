import { useState, useEffect } from 'react'
import clsx from 'clsx'
import { Zap } from 'lucide-react'

function timeAgo(ts) {
  if (!ts) return ''
  const diff = Math.floor(Date.now() / 1000 - ts)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

function OppRow({ opp, isNew }) {
  const [highlight, setHighlight] = useState(isNew)

  useEffect(() => {
    if (isNew) {
      const t = setTimeout(() => setHighlight(false), 2000)
      return () => clearTimeout(t)
    }
  }, [isNew])

  const sum = (opp.yes_ask + opp.no_ask).toFixed(4)
  const profit = (opp.net_profit * 100).toFixed(2)

  return (
    <div className={clsx(
      'flex items-center gap-3 px-4 py-3 border-b border-surface-700 last:border-0 transition-colors duration-700',
      highlight ? 'bg-brand-400/5' : 'hover:bg-surface-700/50'
    )}>
      <div className={clsx(
        'shrink-0 w-1.5 h-1.5 rounded-full',
        opp.executed ? 'bg-brand-400' : 'bg-yellow-400'
      )} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-200 truncate">{opp.question}</p>
        <p className="text-xs text-slate-500 mt-0.5 text-mono">
          YES {opp.yes_ask?.toFixed(4)} + NO {opp.no_ask?.toFixed(4)} = {sum}
        </p>
      </div>
      <div className="text-right shrink-0 ml-2">
        <p className="text-sm font-bold text-mono text-brand-400">+{profit}%</p>
        <p className="text-xs text-slate-600">{timeAgo(opp.timestamp)}</p>
      </div>
      {opp.executed && (
        <Zap size={12} className="text-brand-400 shrink-0" />
      )}
    </div>
  )
}

export function OpportunityFeed({ opportunities = [], newOpp = null }) {
  const [items, setItems] = useState(opportunities)
  const [newId, setNewId] = useState(null)

  useEffect(() => {
    setItems(opportunities)
  }, [opportunities])

  useEffect(() => {
    if (newOpp) {
      setItems(prev => [newOpp, ...prev].slice(0, 50))
      setNewId(newOpp.timestamp)
    }
  }, [newOpp])

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 gap-2">
        <div className="w-8 h-8 rounded-full border-2 border-surface-600 flex items-center justify-center">
          <Zap size={14} className="text-slate-600" />
        </div>
        <p className="text-sm text-slate-600">Scanning for opportunities…</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-surface-700">
      {items.slice(0, 20).map((opp, i) => (
        <OppRow
          key={`${opp.condition_id}-${opp.timestamp}-${i}`}
          opp={opp}
          isNew={opp.timestamp === newId}
        />
      ))}
    </div>
  )
}
