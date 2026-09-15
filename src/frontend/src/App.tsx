import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from './api'
import type { BottleneckListResponse, CombinedRiskResult } from './types'
import { BottleneckPanel } from './components/BottleneckPanel'
import { OutageSimulator } from './components/OutageSimulator'
import { SupplyRiskPanel } from './components/SupplyRiskPanel'
import { BobNarrationPanel } from './components/BobNarrationPanel'
import { CombinedRiskSummary } from './components/CombinedRiskSummary'
import { StatusBar } from './components/StatusBar'
import { NavBar } from './components/NavBar'

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
      <NavBar />

      {/* ── Main Layout ────────────────────────────────────────────────────── */}
      <div className="max-w-screen-2xl mx-auto p-4 flex flex-col gap-4">

        {/* Status bar */}
        <StatusBar
          criticalCount={bottleneckData?.critical_count ?? 0}
          mostCritical={bottleneckData?.most_critical_tool_id ?? null}
          combinedRisk={combinedRisk}
          bottleneckData={bottleneckData}
          loading={loading}
        />

        {error && (
          <div className="p-2 bg-red-900/30 border border-red-700/60 rounded text-red-400 text-xs">
            ⚠ {error} — Running in demo mode with synthetic data.
          </div>
        )}

        {/* Quick-access action bar */}
        <div className="flex items-center gap-3 text-xs">
          <span className="text-muted">Quick actions:</span>
          <Link
            to="/simulator"
            className="border border-accent bg-accent/10 text-accent rounded px-3 py-1 hover:bg-accent/20 transition-colors font-mono"
          >
            ▶ Open Simulator
          </Link>
          {selectedTool && (
            <Link
              to={`/bottlenecks/${selectedTool}`}
              className="border border-border text-muted rounded px-3 py-1 hover:border-gray-500 hover:text-gray-300 transition-colors font-mono"
            >
              📊 Detail: {selectedTool}
            </Link>
          )}
          {combinedRisk?.primary_material_id && (
            <Link
              to={`/supply-risk/${combinedRisk.primary_material_id}`}
              className="border border-border text-muted rounded px-3 py-1 hover:border-gray-500 hover:text-gray-300 transition-colors font-mono"
            >
              🏭 Supply: {combinedRisk.primary_material_id}
            </Link>
          )}
        </div>

        {/* Main 3-column grid */}
        <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>

          {/* Col 1 (rows 1–2): Bottleneck Panel */}
          <div className="row-span-2">
            <BottleneckPanel
              data={bottleneckData}
              selectedTool={selectedTool}
              onSelectTool={setSelectedTool}
            />
          </div>

          {/* Col 2 Row 1: Outage Simulator */}
          <div>
            <OutageSimulator
              selectedTool={selectedTool}
              outageHours={outageHours}
              outageResult={combinedRisk?.outage_simulation ?? null}
              onChangeHours={setOutageHours}
              onRunOutage={setRunOutage}
              isRunning={runOutage}
            />
          </div>

          {/* Col 3 Row 1: Supply Risk Panel */}
          <div>
            <SupplyRiskPanel combinedRisk={combinedRisk} />
          </div>

          {/* Col 2+3 Row 2: Combined Risk Summary */}
          <div className="col-span-2">
            <CombinedRiskSummary combinedRisk={combinedRisk} loading={loading} />
          </div>

          {/* Col 1-3 Row 3: Bob Narration */}
          <div className="col-span-3">
            <BobNarrationPanel
              combinedRisk={combinedRisk}
              selectedTool={selectedTool}
              outageHours={runOutage ? outageHours : undefined}
            />
          </div>
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
