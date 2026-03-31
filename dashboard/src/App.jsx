import { useState, useEffect } from 'react'
import {
  DollarSign, BarChart2, Zap, Layers,
  AlertTriangle, Clock, TrendingUp, Search
} from 'lucide-react'

import { Header } from './components/Header.jsx'
import { MetricCard } from './components/MetricCard.jsx'
import { PnlChart } from './components/PnlChart.jsx'
import { OpportunityFeed } from './components/OpportunityFeed.jsx'
import { PositionsTable } from './components/PositionsTable.jsx'
import { useWebSocket } from './hooks/useWebSocket.js'
import { useApi } from './hooks/useApi.js'

function SectionHeader({ children }) {
  return (
    <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
      {children}
    </h2>
  )
}

export default function App() {
  const { connected: wsConnected, lastMessage } = useWebSocket()

  // Polling fallback (every 10s)
  const { data: statusData, refetch: refetchStatus } = useApi('/api/status', 10000)
  const { data: pnlData, refetch: refetchPnl } = useApi('/api/pnl', 15000)
  const { data: positionsData, refetch: refetchPositions } = useApi('/api/positions', 10000)
  const { data: oppsData } = useApi('/api/opportunities', 0)

  const [status, setStatus] = useState(null)
  const [pnl, setPnl] = useState(null)
  const [positions, setPositions] = useState([])
  const [opportunities, setOpportunities] = useState([])
  const [newOpp, setNewOpp] = useState(null)

  // Merge REST data
  useEffect(() => { if (statusData) setStatus(statusData) }, [statusData])
  useEffect(() => { if (pnlData) setPnl(pnlData) }, [pnlData])
  useEffect(() => { if (positionsData) setPositions(positionsData.positions ?? []) }, [positionsData])
  useEffect(() => { if (oppsData) setOpportunities(oppsData.opportunities ?? []) }, [oppsData])

  // Merge WebSocket data (real-time override)
  useEffect(() => {
    if (!lastMessage) return
    const { type, data } = lastMessage
    if (type === 'init') {
      if (data.status) setStatus(data.status)
      if (data.pnl) setPnl(data.pnl)
      if (data.positions) setPositions(data.positions)
      if (data.opportunities) setOpportunities(data.opportunities)
    } else if (type === 'heartbeat') {
      setStatus(data)
    } else if (type === 'opportunity') {
      setNewOpp(data)
    }
  }, [lastMessage])

  function refetchAll() {
    refetchStatus()
    refetchPnl()
    refetchPositions()
  }

  const pnlValue = pnl?.total ?? 0
  const pnlColor = pnlValue >= 0 ? 'green' : 'red'
  const pnlSign = pnlValue >= 0 ? '+' : ''

  return (
    <div className="min-h-screen bg-surface-900 text-slate-200">
      <Header status={status} wsConnected={wsConnected} onRefresh={refetchAll} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

        {/* ── Metric cards ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Total P&L"
            value={`${pnlSign}$${pnlValue.toFixed(4)}`}
            sub={`Realized: $${(pnl?.realized ?? 0).toFixed(4)}`}
            icon={DollarSign}
            color={pnlColor}
          />
          <MetricCard
            label="Open Positions"
            value={positions.length}
            sub={`$${(pnl?.total_exposure ?? 0).toFixed(2)} deployed`}
            icon={Layers}
            color="blue"
          />
          <MetricCard
            label="Opportunities"
            value={status?.opportunities_found ?? 0}
            sub={`${status?.scans_total ?? 0} total scans`}
            icon={Zap}
            color="yellow"
          />
          <MetricCard
            label="Trades Closed"
            value={pnl?.total_trades ?? 0}
            sub={status?.markets_tracked ? `${status.markets_tracked} markets monitored` : 'Waiting for bot…'}
            icon={BarChart2}
            color="purple"
          />
        </div>

        {/* ── P&L Chart + secondary metrics ── */}
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
              <p className="text-xs text-slate-500 mt-1">Across {positions.length} position{positions.length !== 1 ? 's' : ''}</p>
            </div>

            <div className="card">
              <SectionHeader>Bot Status</SectionHeader>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">State</span>
                  <span className={status?.running ? 'text-brand-400' : 'text-slate-500'}>
                    {status?.running ? 'Running' : 'Stopped'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Markets</span>
                  <span className="text-mono text-slate-300">{status?.markets_tracked ?? '—'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Errors</span>
                  <span className={`text-mono ${(status?.errors ?? 0) > 0 ? 'text-yellow-400' : 'text-slate-300'}`}>
                    {status?.errors ?? 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Last scan</span>
                  <span className="text-mono text-slate-300 text-xs">
                    {status?.last_scan_at
                      ? new Date(status.last_scan_at * 1000).toLocaleTimeString()
                      : '—'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Opportunities feed + Positions ── */}
        <div className="grid lg:grid-cols-2 gap-4">
          <div className="card overflow-hidden">
            <div className="flex items-center justify-between mb-1">
              <SectionHeader>Live Opportunities</SectionHeader>
              <div className="flex items-center gap-1.5 text-xs text-slate-600 mb-3">
                <Search size={10} />
                <span>{opportunities.length} detected</span>
              </div>
            </div>
            <OpportunityFeed opportunities={opportunities} newOpp={newOpp} />
          </div>

          <div className="card overflow-hidden">
            <div className="flex items-center justify-between mb-1">
              <SectionHeader>Open Positions</SectionHeader>
              {positions.length > 0 && (
                <span className="text-xs text-slate-600 mb-3">{positions.length} active</span>
              )}
            </div>
            <PositionsTable positions={positions} />
          </div>
        </div>

        {/* ── Footer ── */}
        <footer className="text-center text-xs text-slate-700 pb-4">
          Polymarket Arb Bot &mdash; {new Date().getFullYear()}
          {!wsConnected && (
            <span className="ml-3 text-yellow-600">
              <AlertTriangle size={10} className="inline mr-1" />
              WebSocket disconnected — using polling
            </span>
          )}
        </footer>
      </main>
    </div>
  )
}
