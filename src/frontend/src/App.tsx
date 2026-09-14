import { useState, useEffect } from 'react'
import { api } from './api'
import type { BottleneckListResponse, CombinedRiskResult } from './types'
import { BottleneckPanel } from './components/BottleneckPanel'
import { OutageSimulator } from './components/OutageSimulator'
import { SupplyRiskPanel } from './components/SupplyRiskPanel'
import { BobNarrationPanel } from './components/BobNarrationPanel'
import { CombinedRiskSummary } from './components/CombinedRiskSummary'
import { StatusBar } from './components/StatusBar'

const DEFAULT_TOOL = 'LITH-07'

export default function App() {
  const [bottleneckData, setBottleneckData] = useState<BottleneckListResponse | null>(null)
  const [selectedTool, setSelectedTool] = useState<string>(DEFAULT_TOOL)
  const [outageHours, setOutageHours] = useState<number>(8)
  const [combinedRisk, setCombinedRisk] = useState<CombinedRiskResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [runOutage, setRunOutage] = useState(false)

  // Load bottleneck scores on mount
  useEffect(() => {
    api.bottleneck.getAll()
      .then(setBottleneckData)
      .catch(err => setError(String(err)))
  }, [])

  // Auto-load combined risk when tool or outage changes
  useEffect(() => {
    setLoading(true)
    setError(null)
    api.impact.getCombined(selectedTool, runOutage ? outageHours : undefined)
      .then(data => {
        setCombinedRisk(data)
        setLoading(false)
      })
      .catch(err => {
        setError(String(err))
        setLoading(false)
      })
  }, [selectedTool, runOutage, outageHours])

  return (
    <div className="min-h-screen bg-surface text-gray-200">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="border-b border-border bg-panel px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          <span className="text-accent font-semibold tracking-wider text-sm uppercase">
            Fab Bottleneck &amp; Supply Chain Risk Advisor
          </span>
          <span className="text-muted text-xs border border-border rounded px-2 py-0.5">
            ⚠ DEMO / SYNTHETIC DATA
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted">
          <span>IBM Bob AI Integration</span>
          <span className={`w-2 h-2 rounded-full ${combinedRisk ? 'bg-success' : 'bg-warning'}`} />
        </div>
      </header>

      {/* ── Main Layout ────────────────────────────────────────────────────── */}
      <div className="max-w-screen-2xl mx-auto p-4 grid gap-4"
           style={{ gridTemplateColumns: '1fr 1fr 1fr', gridTemplateRows: 'auto auto auto' }}>

        {/* Row 1: Status bar full width */}
        <div className="col-span-3">
          <StatusBar
            criticalCount={bottleneckData?.critical_count ?? 0}
            mostCritical={bottleneckData?.most_critical_tool_id ?? null}
            combinedRisk={combinedRisk}
            loading={loading}
          />
          {error && (
            <div className="mt-2 p-2 bg-red-900/30 border border-red-700/60 rounded text-red-400 text-xs">
              ⚠ {error} — Running in demo mode with synthetic data.
            </div>
          )}
        </div>

        {/* Row 2 Col 1: Bottleneck Panel */}
        <div className="col-span-1 row-span-2">
          <BottleneckPanel
            data={bottleneckData}
            selectedTool={selectedTool}
            onSelectTool={setSelectedTool}
          />
        </div>

        {/* Row 2 Col 2: Outage Simulator */}
        <div className="col-span-1">
          <OutageSimulator
            selectedTool={selectedTool}
            outageHours={outageHours}
            outageResult={combinedRisk?.outage_simulation ?? null}
            onChangeHours={setOutageHours}
            onRunOutage={setRunOutage}
            isRunning={runOutage}
          />
        </div>

        {/* Row 2 Col 3: Supply Risk Panel */}
        <div className="col-span-1">
          <SupplyRiskPanel combinedRisk={combinedRisk} />
        </div>

        {/* Row 3 Col 2+3: Combined Risk Summary */}
        <div className="col-span-2">
          <CombinedRiskSummary combinedRisk={combinedRisk} loading={loading} />
        </div>

        {/* Row 3 full width: Bob Narration */}
        <div className="col-span-3">
          <BobNarrationPanel
            combinedRisk={combinedRisk}
            selectedTool={selectedTool}
            outageHours={runOutage ? outageHours : undefined}
          />
        </div>
      </div>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="text-center text-xs text-muted py-4 border-t border-border mt-4">
        Fab Bottleneck &amp; Supply Chain Risk Advisor · IBM Bob AI Innovation Hackathon · Team Alchemist
        · All data is synthetic demo data
      </footer>
    </div>
  )
}
