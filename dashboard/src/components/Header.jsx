import { useState } from 'react'
import { Activity, Settings, RefreshCw } from 'lucide-react'
import { StatusBadge } from './StatusBadge.jsx'
import { post } from '../hooks/useApi.js'
import clsx from 'clsx'

export function Header({ status, wsConnected, onRefresh }) {
  const [toggling, setToggling] = useState(false)

  async function toggleBot() {
    setToggling(true)
    try {
      if (status?.running) {
        await post('/api/bot/stop')
      } else {
        await post('/api/bot/start')
      }
      onRefresh?.()
    } finally {
      setToggling(false)
    }
  }

  function fmtUptime(sec) {
    if (!sec) return null
    const h = Math.floor(sec / 3600)
    const m = Math.floor((sec % 3600) / 60)
    const s = Math.floor(sec % 60)
    if (h > 0) return `${h}h ${m}m`
    if (m > 0) return `${m}m ${s}s`
    return `${s}s`
  }

  return (
    <header className="border-b border-surface-600 bg-surface-800/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-brand-400/10 border border-brand-400/20 flex items-center justify-center">
            <Activity size={14} className="text-brand-400" />
          </div>
          <div>
            <span className="font-semibold text-slate-100 text-sm">Polymarket</span>
            <span className="text-brand-400 font-semibold text-sm"> ARB</span>
          </div>
        </div>

        {/* Center stats */}
        <div className="hidden md:flex items-center gap-6 text-xs text-slate-500">
          {status?.markets_tracked > 0 && (
            <span className="text-mono">{status.markets_tracked} markets</span>
          )}
          {status?.scans_total > 0 && (
            <span className="text-mono">{status.scans_total.toLocaleString()} scans</span>
          )}
          {status?.uptime_sec > 0 && (
            <span className="text-mono">up {fmtUptime(status.uptime_sec)}</span>
          )}
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-3">
          {/* WS connection dot */}
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className={clsx(
              'w-1.5 h-1.5 rounded-full',
              wsConnected ? 'bg-brand-400 animate-pulse-slow' : 'bg-slate-600'
            )} />
            <span className="hidden sm:inline">{wsConnected ? 'live' : 'connecting'}</span>
          </div>

          <StatusBadge running={status?.running} />

          <button
            onClick={toggleBot}
            disabled={toggling}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200',
              status?.running
                ? 'bg-red-400/10 text-red-400 border border-red-400/20 hover:bg-red-400/20'
                : 'bg-brand-400/10 text-brand-400 border border-brand-400/20 hover:bg-brand-400/20',
              toggling && 'opacity-50 cursor-not-allowed'
            )}
          >
            {status?.running ? 'Stop' : 'Start'}
          </button>
        </div>
      </div>
    </header>
  )
}
