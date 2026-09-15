/**
 * /simulator — What-if Outage Simulator
 *
 * Full-screen simulator that lets the user:
 * 1. Select a tool
 * 2. Set outage duration (hours)
 * 3. Run simulation → calls POST /api/v1/impact/{tool_id}?outage_hours=N
 * 4. Display complete result including:
 *    - Backlog added + recovery time
 *    - Affected lots + wafers
 *    - Downstream impact steps
 *    - Combined risk score
 *    - Supply risk for primary material
 *    - Mitigation recommendations
 *    - IBM Bob decision brief
 */
import { useState, useEffect } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
  BarChart, Bar, Cell, CartesianGrid,
} from 'recharts'
import { api } from '../api'
import { NavBar } from '../components/NavBar'
import type { BottleneckAssessment, CombinedRiskResult, NarrationResponse } from '../types'

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: '#f85149', HIGH: '#d29922', MEDIUM: '#58a6ff', LOW: '#3fb950',
}
const TIER_COLORS: Record<string, string> = {
  GREEN: '#3fb950', AMBER: '#d29922', RED: '#f85149', CRITICAL: '#f85149',
}
const CAT_ICONS: Record<string, string> = {
  TOOL: '🔧', SCHEDULE: '📅', INVENTORY: '📦', SUPPLIER: '🏭', OTHER: '💡',
}

function SeverityBadge({ severity }: { severity: string }) {
  const color = SEVERITY_COLOR[severity] ?? '#58a6ff'
  return (
    <span
      className="text-xs rounded px-1.5 py-0.5 border font-mono"
      style={{ color, borderColor: color + '60', backgroundColor: color + '15' }}
    >
      {severity}
    </span>
  )
}

export function SimulatorPage() {
  const [tools, setTools] = useState<BottleneckAssessment[]>([])
  const [selectedTool, setSelectedTool] = useState<string>('LITH-07')
  const [outageHours, setOutageHours] = useState<number>(8)
  const [result, setResult] = useState<CombinedRiskResult | null>(null)
  const [narration, setNarration] = useState<NarrationResponse | null>(null)
  const [simLoading, setSimLoading] = useState(false)
  const [bobLoading, setBobLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasRun, setHasRun] = useState(false)

  // Load tools for selector
  useEffect(() => {
    api.bottleneck.getAll()
      .then(data => setTools(data.bottlenecks))
      .catch(() => setTools([]))
  }, [])

  const runSimulation = async () => {
    setSimLoading(true)
    setError(null)
    setResult(null)
    setNarration(null)
    setHasRun(true)
    try {
      const r = await api.impact.getCombined(selectedTool, outageHours)
      setResult(r)

      // Auto-request Bob narration
      setBobLoading(true)
      try {
        const contextData = {
          tool_id: r.tool_id,
          process_step: r.process_step,
          manufacturing_risk_score: r.manufacturing_risk_score,
          supply_chain_risk_score: r.supply_chain_risk_score,
          combined_risk_score: r.combined_risk_score,
          risk_tier: r.risk_tier,
          risk_tier_label: r.risk_tier_label,
          confidence_pct: r.confidence_pct,
          recommendations: r.recommendations,
          outage_simulation: r.outage_simulation,
        }
        const n = await api.narration.explain('COMBINED', contextData)
        setNarration(n)
      } catch {
        // Bob failed — app still functional, result still shown
      } finally {
        setBobLoading(false)
      }
    } catch (err) {
      setError(String(err))
    } finally {
      setSimLoading(false)
    }
  }

  // Build backlog chart
  const sim = result?.outage_simulation ?? null
  const chartData = sim ? (() => {
    const pts: Array<{ t: string; backlog: number }> = []
    const steps = 14
    for (let i = 0; i <= steps / 2; i++) {
      const t = (i / (steps / 2)) * outageHours
      const b = Math.round((sim.outage_backlog_lots / (steps / 2)) * i)
      pts.push({ t: `+${t.toFixed(0)}h`, backlog: b })
    }
    if (sim.is_recoverable && sim.recovery_hours) {
      for (let i = 1; i <= steps / 2; i++) {
        const t = outageHours + (i / (steps / 2)) * sim.recovery_hours
        const remaining = Math.max(0, sim.total_backlog_lots * (1 - i / (steps / 2)))
        pts.push({ t: `+${t.toFixed(0)}h`, backlog: Math.round(remaining) })
      }
    }
    return pts
  })() : []

  const downstreamBarData = sim?.downstream_impact.map(d => ({
    name: d.affected_step.substring(0, 10),
    delay: d.delay_hours,
    fill: SEVERITY_COLOR[d.impact_severity] ?? '#58a6ff',
  })) ?? []

  const tierColor = result ? TIER_COLORS[result.risk_tier] ?? '#58a6ff' : '#58a6ff'

  return (
    <div className="min-h-screen bg-surface text-gray-200">
      <NavBar />
      <div className="max-w-screen-xl mx-auto p-6 flex flex-col gap-6">

        {/* Page header */}
        <div>
          <h1 className="text-lg font-semibold text-gray-100 mb-1">What-if Outage Simulator</h1>
          <p className="text-xs text-muted">
            Simulate a tool outage and see its full operational and supply chain impact.
            All calculations are deterministic — results come from the backend, not this UI.
          </p>
        </div>

        {/* ── Controls ── */}
        <div className="bg-panel border border-border rounded-lg p-5">
          <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-4">Simulation Parameters</h2>
          <div className="flex items-end gap-6">
            {/* Tool selector */}
            <div className="flex-1">
              <label className="text-xs text-muted block mb-1">Tool</label>
              <select
                value={selectedTool}
                onChange={e => setSelectedTool(e.target.value)}
                className="w-full bg-surface border border-border rounded px-3 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-accent"
              >
                {tools.length > 0
                  ? tools.map(t => (
                      <option key={t.tool_id} value={t.tool_id}>
                        {t.tool_id} — {t.tool_name} ({t.severity})
                      </option>
                    ))
                  : <option value="LITH-07">LITH-07 — EUV Scanner Unit 7</option>
                }
              </select>
            </div>

            {/* Duration */}
            <div className="w-64">
              <label className="text-xs text-muted block mb-1">Outage Duration: <span className="text-yellow-400 font-mono">{outageHours}h</span></label>
              <input
                type="range"
                min={1}
                max={168}
                step={1}
                value={outageHours}
                onChange={e => setOutageHours(Number(e.target.value))}
                className="w-full accent-accent"
              />
              <div className="flex justify-between text-xs text-muted mt-0.5">
                <span>1h</span><span>1 week</span>
              </div>
            </div>

            {/* Run button */}
            <button
              onClick={runSimulation}
              disabled={simLoading}
              className="px-6 py-2.5 rounded border border-accent bg-accent/10 text-accent font-mono text-sm
                         hover:bg-accent/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {simLoading ? '⟳ SIMULATING…' : '▶ RUN SIMULATION'}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-900/20 border border-red-700/60 rounded p-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Loading state */}
        {simLoading && (
          <div className="bg-panel border border-border rounded-lg p-8 flex items-center justify-center gap-3">
            <div className="w-2 h-2 rounded-full bg-accent animate-bounce" />
            <div className="w-2 h-2 rounded-full bg-accent animate-bounce delay-75" />
            <div className="w-2 h-2 rounded-full bg-accent animate-bounce delay-150" />
            <span className="text-muted text-sm">Computing outage impact for {selectedTool} · {outageHours}h…</span>
          </div>
        )}

        {/* Initial empty state */}
        {!hasRun && !simLoading && (
          <div className="bg-panel border border-dashed border-border rounded-lg p-12 text-center">
            <div className="text-muted text-sm mb-2">Configure parameters above and click ▶ RUN SIMULATION</div>
            <div className="text-xs text-muted">
              Default: LITH-07 · 8-hour outage — the critical bottleneck scenario
            </div>
          </div>
        )}

        {/* Results */}
        {result && !simLoading && (
          <>
            {/* Combined Risk Banner */}
            <div className="bg-panel border rounded-lg p-5" style={{ borderColor: tierColor + '60' }}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h2 className="text-gray-100 font-semibold">{result.tool_id} — {result.tool_name}</h2>
                    <SeverityBadge severity={result.risk_tier} />
                  </div>
                  <div className="text-xs text-muted">
                    {result.process_step} · {outageHours}h simulated outage
                    {result.primary_material_id && (
                      <> · Material: <span className="font-mono text-gray-300">{result.primary_material_id}</span></>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-mono font-black" style={{ color: tierColor }}>
                    {(result.combined_risk_score * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-muted">{result.risk_tier_label} · {result.confidence_pct}% confidence</div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 mt-4">
                {[
                  { label: 'Manufacturing Risk', value: `${(result.manufacturing_risk_score * 100).toFixed(1)}%`, color: '#f85149' },
                  { label: 'Supply Chain Risk', value: `${(result.supply_chain_risk_score * 100).toFixed(1)}%`, color: '#d29922' },
                  { label: 'Combined Risk (0.55/0.45)', value: `${(result.combined_risk_score * 100).toFixed(1)}%`, color: tierColor },
                ].map(item => (
                  <div key={item.label} className="bg-surface rounded border border-border p-2">
                    <div className="text-xs text-muted mb-1">{item.label}</div>
                    <div className="font-mono font-bold" style={{ color: item.color }}>{item.value}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Outage simulation details */}
            {sim && (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-panel border border-border rounded-lg p-4">
                  <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">Outage Impact</h2>
                  <div className="grid grid-cols-2 gap-2 mb-4">
                    {[
                      { label: 'Outage Backlog', value: `${sim.outage_backlog_lots} lots`, color: 'text-red-400' },
                      { label: 'Total Backlog', value: `${sim.total_backlog_lots} lots`, color: 'text-red-400' },
                      { label: 'Affected Wafers', value: `${sim.backlog_wafers.toLocaleString()}`, color: 'text-yellow-400' },
                      {
                        label: 'Recovery Time',
                        value: sim.recovery_hours != null ? `${sim.recovery_hours.toFixed(1)}h (${(sim.recovery_hours / 24).toFixed(1)}d)` : 'NOT RECOVERABLE',
                        color: sim.is_recoverable ? 'text-green-400' : 'text-red-400',
                      },
                    ].map(item => (
                      <div key={item.label} className="bg-surface rounded border border-border p-2">
                        <div className="text-xs text-muted">{item.label}</div>
                        <div className={`font-mono text-sm font-bold ${item.color}`}>{item.value}</div>
                      </div>
                    ))}
                  </div>
                  <div className={`text-xs px-3 py-2 rounded border text-center font-mono mb-3 ${
                    sim.is_recoverable
                      ? 'border-green-700/60 bg-green-900/20 text-green-400'
                      : 'border-red-700/60 bg-red-900/20 text-red-400'
                  }`}>
                    {sim.is_recoverable
                      ? `✓ Recoverable within ${sim.recovery_hours?.toFixed(1)}h after tool restoration`
                      : '✗ Recovery impossible at current capacity — arrival rate ≥ max processing rate'}
                  </div>
                  {sim.simulation_note && (
                    <div className="text-xs text-muted border border-border rounded p-2">{sim.simulation_note}</div>
                  )}
                </div>

                {/* Backlog chart */}
                <div className="bg-panel border border-border rounded-lg p-4">
                  <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">
                    Backlog Progression
                  </h2>
                  {chartData.length > 0 ? (
                    <div className="h-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
                          <defs>
                            <linearGradient id="blGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#f85149" stopOpacity={0.4} />
                              <stop offset="95%" stopColor="#f85149" stopOpacity={0.05} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid stroke="#30363d" strokeDasharray="3 3" />
                          <XAxis dataKey="t" tick={{ fill: '#8b949e', fontSize: 9 }} interval={3} />
                          <YAxis tick={{ fill: '#8b949e', fontSize: 9 }} />
                          <Tooltip
                            contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }}
                            formatter={(val: number) => [`${val} lots`, 'Backlog']}
                          />
                          <ReferenceLine x={`+${outageHours}h`} stroke="#d29922" strokeDasharray="3 3" />
                          <Area type="monotone" dataKey="backlog" stroke="#f85149" fill="url(#blGrad)" strokeWidth={2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-48 flex items-center justify-center text-muted text-xs">
                      Not recoverable — backlog grows indefinitely
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Downstream impact */}
            {sim && sim.downstream_impact.length > 0 && (
              <div className="bg-panel border border-border rounded-lg p-4">
                <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">
                  Downstream Process Impact ({sim.downstream_impact.length} steps)
                </h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-surface border-b border-border">
                          <th className="text-left px-2 py-1.5 text-muted font-normal">Process Step</th>
                          <th className="text-right px-2 py-1.5 text-muted font-normal">Delay</th>
                          <th className="text-right px-2 py-1.5 text-muted font-normal">Lots</th>
                          <th className="text-right px-2 py-1.5 text-muted font-normal">Severity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sim.downstream_impact.map((d, i) => (
                          <tr key={i} className={i < sim.downstream_impact.length - 1 ? 'border-b border-border' : ''}>
                            <td className="px-2 py-1.5 text-gray-300">{d.affected_step}</td>
                            <td className="px-2 py-1.5 text-right font-mono text-yellow-400">+{d.delay_hours.toFixed(1)}h</td>
                            <td className="px-2 py-1.5 text-right font-mono text-muted">{d.affected_lots}</td>
                            <td className="px-2 py-1.5 text-right"><SeverityBadge severity={d.impact_severity} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {downstreamBarData.length > 0 && (
                    <div className="h-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={downstreamBarData} margin={{ top: 0, right: 0, bottom: 0, left: -15 }}>
                          <CartesianGrid stroke="#30363d" strokeDasharray="3 3" />
                          <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 9 }} />
                          <YAxis tick={{ fill: '#8b949e', fontSize: 9 }} />
                          <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }} formatter={(v: number) => [`${v.toFixed(1)}h`, 'Delay']} />
                          <Bar dataKey="delay" radius={[2, 2, 0, 0]}>
                            {downstreamBarData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Supply risk summary */}
            {result.supply_risk && (
              <div className="bg-panel border border-border rounded-lg p-4">
                <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">
                  Supply Chain Risk — {result.supply_risk.material_name}
                </h2>
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: 'Combined Supply Risk', value: `${(result.supply_risk.combined_supply_risk * 100).toFixed(1)}%`, tier: result.supply_risk.risk_tier },
                    { label: 'HHI Concentration', value: result.supply_risk.hhi_value?.toFixed(0) ?? 'N/A', tier: result.supply_risk.hhi_value && result.supply_risk.hhi_value > 2500 ? 'RED' : result.supply_risk.hhi_value && result.supply_risk.hhi_value > 1500 ? 'AMBER' : 'GREEN' },
                    { label: 'Inventory Coverage', value: result.supply_risk.inventory_coverage_days != null ? `${result.supply_risk.inventory_coverage_days.toFixed(1)}d` : '—', tier: result.supply_risk.inventory_risk_tier === 'CRITICAL' || result.supply_risk.inventory_risk_tier === 'HIGH' ? 'RED' : result.supply_risk.inventory_risk_tier === 'MEDIUM' ? 'AMBER' : 'GREEN' },
                    { label: 'SPOF', value: result.supply_risk.has_spof ? '⚠ YES' : '✓ NO', tier: result.supply_risk.has_spof ? 'RED' : 'GREEN' },
                  ].map(item => (
                    <div key={item.label} className="bg-surface rounded border border-border p-3">
                      <div className="text-xs text-muted mb-1">{item.label}</div>
                      <div className="font-mono font-bold" style={{ color: TIER_COLORS[item.tier] ?? '#58a6ff' }}>{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {result.recommendations.length > 0 && (
              <div className="bg-panel border border-border rounded-lg p-4">
                <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">
                  Mitigation Recommendations ({result.recommendations.length})
                </h2>
                <div className="flex flex-col gap-2">
                  {result.recommendations.map((rec, i) => (
                    <div key={i} className="bg-surface rounded border border-border p-3 flex gap-3">
                      <div className="text-lg leading-none mt-0.5 flex-shrink-0">{CAT_ICONS[rec.category] ?? '💡'}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-xs text-muted font-mono">#{rec.priority}</span>
                          <span className="text-xs font-semibold text-gray-300">{rec.category}</span>
                          <span className={`text-xs rounded px-1 border font-mono ${
                            rec.feasibility === 'HIGH' ? 'text-green-400 border-green-700/60 bg-green-900/20' :
                            rec.feasibility === 'MEDIUM' ? 'text-yellow-400 border-yellow-700/60 bg-yellow-900/20' :
                            'text-red-400 border-red-700/60 bg-red-900/20'
                          }`}>{rec.feasibility}</span>
                        </div>
                        <p className="text-xs text-gray-300 leading-relaxed">{rec.recommendation}</p>
                        {rec.expected_impact && (
                          <p className="text-xs text-muted mt-1 italic">{rec.expected_impact}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* IBM Bob narration */}
            <div className="bg-panel border border-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                  <h2 className="text-purple-400 text-xs font-semibold uppercase tracking-widest">
                    IBM Bob — Decision Brief
                  </h2>
                  {narration?.is_fallback && (
                    <span className="text-xs border border-yellow-700/60 bg-yellow-900/20 text-yellow-400 rounded px-1.5 py-0.5">
                      TEMPLATE FALLBACK
                    </span>
                  )}
                  {narration && !narration.is_fallback && (
                    <span className="text-xs border border-purple-700/60 bg-purple-900/20 text-purple-400 rounded px-1.5 py-0.5">
                      {narration.model_used}
                    </span>
                  )}
                </div>
              </div>

              {bobLoading ? (
                <div className="flex items-center gap-2 p-4 bg-surface rounded border border-border">
                  <div className="w-1 h-1 rounded-full bg-purple-400 animate-bounce" />
                  <div className="w-1 h-1 rounded-full bg-purple-400 animate-bounce delay-75" />
                  <div className="w-1 h-1 rounded-full bg-purple-400 animate-bounce delay-150" />
                  <span className="text-muted text-xs ml-2">Bob is analysing the simulation results…</span>
                </div>
              ) : narration ? (
                <div className="bg-surface rounded border border-border p-4 text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                  {narration.narration_text}
                </div>
              ) : (
                <div className="text-center text-muted text-xs py-4 border border-dashed border-border rounded">
                  Bob narration will appear after simulation completes
                </div>
              )}

              {narration && (
                <div className="text-xs text-muted border-t border-border pt-2 mt-2">
                  {narration.is_fallback
                    ? '⚠ Bob unavailable — deterministic template narration active. Application fully functional.'
                    : '✓ Powered by IBM Bob (watsonx.ai)'}
                </div>
              )}
            </div>
          </>
        )}

      </div>
    </div>
  )
}
