import { useState, useEffect } from 'react'
import {
  DollarSign, BarChart2, Zap, Layers,
} from 'lucide-react'

import { Header } from './components/Header.jsx'
import { MetricCard } from './components/MetricCard.jsx'
import { PnlChart } from './components/PnlChart.jsx'
import { OpportunityFeed } from './components/OpportunityFeed.jsx'
import { PositionsTable } from './components/PositionsTable.jsx'
import { InstallPrompt } from './components/InstallPrompt.jsx'
import { useWebSocket } from './hooks/useWebSocket.js'
import { useApi } from './hooks/useApi.js'

// ── Bottom nav tabs (mobile) ──────────────────────────────────────────────
const TABS = [
  { id: 'overview',      label: 'Overview',       icon: BarChart2  },
  { id: 'opportunities', label: 'Signals',         icon: Zap        },
  { id: 'positions',     label: 'Positions',       icon: Layers     },
  { id: 'pnl',           label: 'P&L',             icon: DollarSign },
]

function BottomNav({ active, onChange }) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-surface-800/95 backdrop-blur border-t border-surface-600 md:hidden safe-area-bottom">
      <div className="flex">
        {TABS.map(t => {
          const Icon = t.icon
          const isActive = active === t.id
          return (
            <button
              key={t.id}
              onClick={() => onChange(t.id)}
              className={`flex-1 flex flex-col items-center gap-1 py-3 text-xs transition-colors ${
                isActive ? 'text-brand-400' : 'text-slate-500'
              }`}
            >
              <Icon size={18} strokeWidth={isActive ? 2.5 : 1.5} />
              <span className="font-medium">{t.label}</span>
              {isActive && (
                <span className="absolute bottom-0 w-6 h-0.5 bg-brand-400 rounded-full" />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}

function SectionHeader({ children }) {
  return (
    <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
      {children}
    </h2>
  )
}

export default function App() {
  const { connected: wsConnected, lastMessage } = useWebSocket()
  const [activeTab, setActiveTab] = useState('overview')

  const { data: statusData, refetch: refetchStatus } = useApi('/api/status', 10000)
  const { data: pnlData,    refetch: refetchPnl     } = useApi('/api/pnl',    15000)
  const { data: posData,    refetch: refetchPos      } = useApi('/api/positions', 10000)
  const { data: oppsData  }                            = useApi('/api/opportunities', 0)

  const [status, setStatus]             = useState(null)
  const [pnl, setPnl]                   = useState(null)
  const [positions, setPositions]       = useState([])
  const [opportunities, setOpps]        = useState([])
  const [newOpp, setNewOpp]             = useState(null)

  useEffect(() => { if (statusData) setStatus(statusData) }, [statusData])
  useEffect(() => { if (pnlData)    setPnl(pnlData)       }, [pnlData])
  useEffect(() => { if (posData)    setPositions(posData.positions ?? []) }, [posData])
  useEffect(() => { if (oppsData)   setOpps(oppsData.opportunities ?? []) }, [oppsData])

  useEffect(() => {
    if (!lastMessage) return
    const { type, data } = lastMessage
    if (type === 'init') {
      if (data.status)       setStatus(data.status)
      if (data.pnl)          setPnl(data.pnl)
      if (data.positions)    setPositions(data.positions)
      if (data.opportunities) setOpps(data.opportunities)
    } else if (type === 'heartbeat') {
      setStatus(data)
    } else if (type === 'opportunity') {
      setNewOpp(data)
    }
  }, [lastMessage])

  function refetchAll() { refetchStatus(); refetchPnl(); refetchPos() }

  const pnlValue = pnl?.total ?? 0
  const pnlColor = pnlValue >= 0 ? 'green' : 'red'
  const pnlSign  = pnlValue >= 0 ? '+' : ''

  // ── Sections ──────────────────────────────────────────────────────────

  const metricsSection = (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
      <MetricCard
        label="Total P&L"
        value={`${pnlSign}$${pnlValue.toFixed(4)}`}
        sub={`Realized: $${(pnl?.realized ?? 0).toFixed(4)}`}
        icon={DollarSign}
        color={pnlColor}
      />
      <MetricCard
        label="Positions"
        value={positions.length}
        sub={`$${(pnl?.total_exposure ?? 0).toFixed(2)} deployed`}
        icon={Layers}
        color="blue"
      />
      <MetricCard
        label="Signals"
        value={status?.opportunities_found ?? 0}
        sub={`${status?.scans_total ?? 0} scans`}
        icon={Zap}
        color="yellow"
      />
      <MetricCard
        label="Trades"
        value={pnl?.total_trades ?? 0}
        sub={status?.markets_tracked ? `${status.markets_tracked} markets` : '—'}
        icon={BarChart2}
        color="purple"
      />
    </div>
  )

  const pnlSection = (
    <div className="grid lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 card">
        <SectionHeader>P&L over time</SectionHeader>
        <PnlChart history={pnl?.history ?? []} />
      </div>
      <div className="space-y-4">
        <div className="card">
          <SectionHeader>Unrealized P&L</SectionHeader>
          <p className={`text-2xl font-bold text-mono ${(pnl?.unrealized ?? 0) >= 0 ? 'text-brand-400' : 'text-red-400'}`}>
            {(pnl?.unrealized ?? 0) >= 0 ? '+' : ''}${(pnl?.unrealized ?? 0).toFixed(4)}
          </p>
          <p className="text-xs text-slate-500 mt-1">{positions.length} position{positions.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="card">
          <SectionHeader>Bot Status</SectionHeader>
          <div className="space-y-2 text-sm">
            {[
              ['State',    status?.running ? 'Running' : 'Stopped', status?.running ? 'text-brand-400' : 'text-slate-500'],
              ['Markets',  status?.markets_tracked ?? '—', 'text-slate-300'],
              ['Errors',   status?.errors ?? 0, (status?.errors ?? 0) > 0 ? 'text-yellow-400' : 'text-slate-300'],
              ['Last scan', status?.last_scan_at ? new Date(status.last_scan_at * 1000).toLocaleTimeString() : '—', 'text-slate-300'],
            ].map(([label, val, cls]) => (
              <div key={label} className="flex justify-between">
                <span className="text-slate-500">{label}</span>
                <span className={`text-mono text-xs ${cls}`}>{val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )

  const oppsSection = (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between mb-1">
        <SectionHeader>Live Opportunities</SectionHeader>
        <span className="text-xs text-slate-600 mb-3">{opportunities.length} detected</span>
      </div>
      <OpportunityFeed opportunities={opportunities} newOpp={newOpp} />
    </div>
  )

  const posSection = (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between mb-1">
        <SectionHeader>Open Positions</SectionHeader>
        {positions.length > 0 && (
          <span className="text-xs text-slate-600 mb-3">{positions.length} active</span>
        )}
      </div>
      <PositionsTable positions={positions} />
    </div>
  )

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-surface-900 text-slate-200">
      <Header status={status} wsConnected={wsConnected} onRefresh={refetchAll} />

      {/* Desktop layout */}
      <main className="hidden md:block max-w-7xl mx-auto px-6 py-6 space-y-6">
        {metricsSection}
        {pnlSection}
        <div className="grid lg:grid-cols-2 gap-4">
          {oppsSection}
          {posSection}
        </div>
        <footer className="text-center text-xs text-slate-700 pb-4">
          Polymarket Arb Bot &mdash; {new Date().getFullYear()}
        </footer>
      </main>

      {/* Mobile layout — tab-based */}
      <main className="md:hidden pb-20">
        <div className="px-4 pt-4 space-y-4">
          {activeTab === 'overview' && (
            <>
              {metricsSection}
              <div className="card">
                <SectionHeader>Bot Status</SectionHeader>
                <div className="space-y-2 text-sm">
                  {[
                    ['State',    status?.running ? 'Running' : 'Stopped', status?.running ? 'text-brand-400' : 'text-slate-500'],
                    ['Markets',  status?.markets_tracked ?? '—', 'text-slate-300'],
                    ['Scans',    (status?.scans_total ?? 0).toLocaleString(), 'text-slate-300'],
                    ['Errors',   status?.errors ?? 0, (status?.errors ?? 0) > 0 ? 'text-yellow-400' : 'text-slate-300'],
                  ].map(([label, val, cls]) => (
                    <div key={label} className="flex justify-between">
                      <span className="text-slate-500">{label}</span>
                      <span className={`text-mono text-xs ${cls}`}>{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {activeTab === 'pnl' && (
            <>
              <div className="card">
                <SectionHeader>P&L Overview</SectionHeader>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Total</p>
                    <p className={`text-xl font-bold text-mono ${pnlValue >= 0 ? 'text-brand-400' : 'text-red-400'}`}>
                      {pnlSign}${pnlValue.toFixed(4)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Unrealized</p>
                    <p className={`text-xl font-bold text-mono ${(pnl?.unrealized ?? 0) >= 0 ? 'text-brand-400' : 'text-red-400'}`}>
                      {(pnl?.unrealized ?? 0) >= 0 ? '+' : ''}${(pnl?.unrealized ?? 0).toFixed(4)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Realized</p>
                    <p className="text-xl font-bold text-mono text-slate-200">${(pnl?.realized ?? 0).toFixed(4)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Trades</p>
                    <p className="text-xl font-bold text-mono text-slate-200">{pnl?.total_trades ?? 0}</p>
                  </div>
                </div>
                <PnlChart history={pnl?.history ?? []} />
              </div>
            </>
          )}

          {activeTab === 'opportunities' && oppsSection}
          {activeTab === 'positions'     && posSection}
        </div>
      </main>

      <BottomNav active={activeTab} onChange={setActiveTab} />
      <InstallPrompt />
    </div>
  )
}
