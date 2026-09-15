/**
 * /bottlenecks/:toolId — Full bottleneck detail for a single fab tool.
 *
 * Shows:
 * - Bottleneck score with severity badge
 * - All score components (utilization, WIP pressure, capacity pressure, downtime)
 * - Confidence range and trend
 * - WIP trend history chart
 * - Combined risk from impact service
 * - Mitigation recommendations
 * - Link to supply risk for primary material
 */
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from 'recharts'
import { api } from '../api'
import { NavBar } from '../components/NavBar'
import type { BottleneckAssessment, CombinedRiskResult } from '../types'

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: '#f85149',
  HIGH: '#d29922',
  MEDIUM: '#58a6ff',
  LOW: '#3fb950',
}

const TIER_COLORS: Record<string, string> = {
  GREEN: '#3fb950',
  AMBER: '#d29922',
  RED: '#f85149',
  CRITICAL: '#f85149',
}

const CAT_ICONS: Record<string, string> = {
  TOOL: '🔧',
  SCHEDULE: '📅',
  INVENTORY: '📦',
  SUPPLIER: '🏭',
  OTHER: '💡',
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-surface rounded border border-border p-3">
      <div className="text-xs text-muted mb-0.5">{label}</div>
      <div className="font-mono text-sm font-bold" style={{ color: color ?? '#e6edf3' }}>{value}</div>
    </div>
  )
}

function ScoreGauge({ score, severity }: { score: number; severity: string }) {
  const color = SEVERITY_COLOR[severity] ?? '#58a6ff'
  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className="text-4xl font-mono font-black"
        style={{ color }}
      >
        {score.toFixed(1)}
      </div>
      <div className="text-xs text-muted">/ 100</div>
      <span
        className="text-xs px-2 py-0.5 rounded border font-mono font-semibold"
        style={{ color, borderColor: color + '60', backgroundColor: color + '15' }}
      >
        {severity}
      </span>
    </div>
  )
}

export function BottleneckDetailPage() {
  const { toolId } = useParams<{ toolId: string }>()
  const [tool, setTool] = useState<BottleneckAssessment | null>(null)
  const [combined, setCombined] = useState<CombinedRiskResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!toolId) return
    setLoading(true)
    setError(null)
    Promise.all([
      api.bottleneck.getTool(toolId),
      api.impact.getCombined(toolId),
    ])
      .then(([t, c]) => {
        setTool(t)
        setCombined(c)
        setLoading(false)
      })
      .catch(err => {
        setError(String(err))
        setLoading(false)
      })
  }, [toolId])

  const histData = tool?.history?.map((h, i) => ({
    i,
    wip: h.wip_units ?? 0,
    util: Math.round((h.utilization ?? 0) * 100),
  })) ?? []

  const radarData = tool ? [
    { subject: 'Utilisation', value: tool.utilization },
    { subject: 'WIP Pressure', value: tool.wip_pressure_normalized },
    { subject: 'Capacity Pressure', value: tool.capacity_pressure },
    { subject: 'Downtime', value: Math.min(tool.downtime_pct * 10, 1) },
  ] : []

  const severityColor = tool ? SEVERITY_COLOR[tool.severity] ?? '#58a6ff' : '#58a6ff'
  const tierColor = combined ? TIER_COLORS[combined.risk_tier] ?? '#58a6ff' : '#58a6ff'

  if (loading) {
    return (
      <div className="min-h-screen bg-surface">
        <NavBar />
        <div className="flex items-center justify-center h-64">
          <span className="text-muted text-sm animate-pulse">Loading {toolId} assessment…</span>
        </div>
      </div>
    )
  }

  if (error || !tool) {
    return (
      <div className="min-h-screen bg-surface">
        <NavBar />
        <div className="max-w-4xl mx-auto p-6">
          <div className="bg-red-900/20 border border-red-700/60 rounded p-4 text-red-400 text-sm">
            {error ?? `Tool '${toolId}' not found.`}
          </div>
          <Link to="/" className="text-accent text-sm mt-4 inline-block hover:underline">← Back to Dashboard</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface text-gray-200">
      <NavBar />
      <div className="max-w-screen-xl mx-auto p-6 flex flex-col gap-6">

        {/* ── Breadcrumb ── */}
        <div className="flex items-center gap-2 text-xs text-muted">
          <Link to="/" className="text-accent hover:underline">Dashboard</Link>
          <span>/</span>
          <span className="text-gray-300 font-mono">{tool.tool_id}</span>
        </div>

        {/* ── Hero row ── */}
        <div className="bg-panel border border-border rounded-lg p-6 flex gap-8">
          <ScoreGauge score={tool.bottleneck_score} severity={tool.severity} />
          <div className="flex-1">
            <h1 className="text-lg font-semibold text-gray-100 mb-1">
              {tool.tool_id} — {tool.tool_name}
            </h1>
            <div className="flex items-center gap-3 text-xs text-muted mb-3">
              <span className="font-mono">{tool.tool_type}</span>
              <span>·</span>
              <span>{tool.process_name} (Step {tool.process_id})</span>
              <span>·</span>
              <span className={tool.status === 'ACTIVE' ? 'text-green-400' : 'text-yellow-400'}>
                {tool.status}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-3">
              <Metric
                label="Utilisation"
                value={`${tool.utilization_pct.toFixed(1)}%`}
                color={tool.utilization_pct >= 90 ? '#f85149' : tool.utilization_pct >= 75 ? '#d29922' : undefined}
              />
              <Metric
                label="WIP Units"
                value={`${tool.wip_units}`}
                color={tool.wip_units > tool.normal_wip * 1.5 ? '#f85149' : tool.wip_units > tool.normal_wip ? '#d29922' : undefined}
              />
              <Metric
                label="WIP Normal"
                value={`${tool.normal_wip}`}
              />
              <Metric
                label="Downtime"
                value={`${tool.downtime_hours.toFixed(1)}h`}
                color={tool.downtime_hours > 2 ? '#f85149' : tool.downtime_hours > 0 ? '#d29922' : undefined}
              />
            </div>
          </div>

          {/* Confidence block */}
          <div className="flex flex-col items-end gap-2 text-right">
            <div className="text-xs text-muted uppercase tracking-wider">Confidence</div>
            <div className="text-sm font-mono" style={{ color: tool.low_confidence ? '#d29922' : '#3fb950' }}>
              {tool.low_confidence ? '⚠ LOW' : '✓ HIGH'}
            </div>
            <div className="text-xs text-muted">{(tool.confidence * 100).toFixed(0)}% · {tool.snapshot_count} snapshots</div>
            <div className={`text-xs font-mono px-2 py-0.5 rounded border ${
              tool.wip_trend === 'RISING' ? 'text-red-400 border-red-700/60 bg-red-900/20' :
              tool.wip_trend === 'FALLING' ? 'text-green-400 border-green-700/60 bg-green-900/20' :
              'text-muted border-border'
            }`}>
              WIP {tool.wip_trend}
            </div>
          </div>
        </div>

        {/* ── Score components + Radar ── */}
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 bg-panel border border-border rounded-lg p-4 flex flex-col gap-3">
            <h2 className="text-accent text-xs font-semibold uppercase tracking-widest">Score Components</h2>
            {[
              { label: 'Utilisation', value: tool.utilization_pct, max: 100, note: `${tool.utilization_pct.toFixed(1)}%` },
              { label: 'WIP Pressure (normalized)', value: tool.wip_pressure_normalized * 100, max: 100, note: `raw: ${tool.wip_pressure_raw.toFixed(2)}` },
              { label: 'Capacity Pressure', value: tool.capacity_pressure * 100, max: 100, note: `${(tool.capacity_pressure * 100).toFixed(1)}%` },
              { label: 'Downtime %', value: tool.downtime_pct * 100, max: 100, note: `${(tool.downtime_pct * 100).toFixed(1)}%` },
              { label: 'Bottleneck Score', value: tool.bottleneck_score, max: 100, note: tool.severity, highlight: true },
            ].map(item => {
              const color = item.highlight ? (SEVERITY_COLOR[tool.severity] ?? '#58a6ff') : SEVERITY_COLOR[
                item.value >= 85 ? 'CRITICAL' : item.value >= 70 ? 'HIGH' : item.value >= 40 ? 'MEDIUM' : 'LOW'
              ]
              return (
                <div key={item.label}>
                  <div className="flex justify-between text-xs mb-0.5">
                    <span className="text-muted">{item.label}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-muted text-xs">{item.note}</span>
                      <span className="font-mono font-semibold" style={{ color }}>{item.value.toFixed(1)}</span>
                    </div>
                  </div>
                  <div className="bg-gray-800 rounded-full h-2 w-full">
                    <div
                      className="h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(item.value, 100)}%`, backgroundColor: color }}
                    />
                  </div>
                </div>
              )
            })}

            <div className="text-xs text-muted border-t border-border pt-2">
              Score = 0.30 × Utilisation + 0.30 × Capacity Pressure + 0.25 × WIP Pressure + 0.15 × Downtime
            </div>
          </div>

          <div className="bg-panel border border-border rounded-lg p-4">
            <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">Risk Profile</h2>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#30363d" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#8b949e', fontSize: 9 }} />
                  <Radar dataKey="value" stroke={severityColor} fill={severityColor} fillOpacity={0.3} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* ── WIP History Chart ── */}
        {histData.length > 1 && (
          <div className="bg-panel border border-border rounded-lg p-4">
            <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">
              WIP History ({histData.length} snapshots)
            </h2>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={histData} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="#30363d" strokeDasharray="3 3" />
                  <XAxis dataKey="i" tick={{ fill: '#8b949e', fontSize: 9 }} label={{ value: 'Snapshot (oldest→newest)', fill: '#8b949e', fontSize: 9, position: 'insideBottomRight', offset: -5 }} />
                  <YAxis tick={{ fill: '#8b949e', fontSize: 9 }} />
                  <Tooltip
                    contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }}
                    formatter={(val: number, name: string) => [val, name === 'wip' ? 'WIP Units' : 'Util %']}
                  />
                  <Line type="monotone" dataKey="wip" name="wip" stroke={severityColor} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="util" name="util" stroke="#58a6ff" strokeWidth={1} strokeDasharray="4 4" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* ── Combined Risk ── */}
        {combined && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-panel border border-border rounded-lg p-4">
              <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">Combined Risk</h2>
              <div className="flex items-center gap-4 mb-4">
                <div className="text-3xl font-mono font-black" style={{ color: tierColor }}>
                  {(combined.combined_risk_score * 100).toFixed(1)}%
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: tierColor }}>{combined.risk_tier_label}</div>
                  <div className="text-xs text-muted">Confidence: {combined.confidence_pct}%</div>
                </div>
              </div>
              {[
                { label: 'Manufacturing Risk', value: combined.manufacturing_risk_score, color: '#f85149' },
                { label: 'Supply Chain Risk', value: combined.supply_chain_risk_score, color: '#d29922' },
                { label: 'Combined', value: combined.combined_risk_score, color: tierColor },
              ].map(item => (
                <div key={item.label} className="mb-2">
                  <div className="flex justify-between text-xs mb-0.5">
                    <span className="text-muted">{item.label}</span>
                    <span className="font-mono" style={{ color: item.color }}>{(item.value * 100).toFixed(1)}%</span>
                  </div>
                  <div className="bg-gray-800 rounded-full h-1.5">
                    <div className="h-1.5 rounded-full" style={{ width: `${item.value * 100}%`, backgroundColor: item.color }} />
                  </div>
                </div>
              ))}
              <div className="text-xs text-muted mt-2">
                Formula: 0.55 × manufacturing + 0.45 × supply chain
              </div>
              {combined.primary_material_id && (
                <div className="mt-3 text-xs">
                  <span className="text-muted">Primary material: </span>
                  <Link
                    to={`/supply-risk/${combined.primary_material_id}`}
                    className="text-accent hover:underline font-mono"
                  >
                    {combined.primary_material_id} →
                  </Link>
                </div>
              )}
            </div>

            <div className="bg-panel border border-border rounded-lg p-4">
              <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">
                Recommendations ({combined.recommendations.length})
              </h2>
              <div className="flex flex-col gap-2 overflow-y-auto max-h-64">
                {combined.recommendations.map((rec, i) => (
                  <div key={i} className="bg-surface rounded border border-border p-2.5 flex gap-2">
                    <span className="text-base leading-none mt-0.5 flex-shrink-0">{CAT_ICONS[rec.category] ?? '💡'}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="text-xs text-muted font-mono">#{rec.priority}</span>
                        <span className="text-xs font-semibold text-gray-300">{rec.category}</span>
                        <span className={`text-xs rounded px-1 border font-mono ${
                          rec.feasibility === 'HIGH' ? 'text-green-400 border-green-700/60 bg-green-900/20' :
                          rec.feasibility === 'MEDIUM' ? 'text-yellow-400 border-yellow-700/60 bg-yellow-900/20' :
                          'text-red-400 border-red-700/60 bg-red-900/20'
                        }`}>{rec.feasibility}</span>
                      </div>
                      <p className="text-xs text-gray-300 leading-relaxed">{rec.recommendation}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Compatible products ── */}
        {tool.compatible_products.length > 0 && (
          <div className="bg-panel border border-border rounded-lg p-4">
            <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-2">Compatible Products</h2>
            <div className="flex gap-2 flex-wrap">
              {tool.compatible_products.map(p => (
                <span key={p} className="text-xs font-mono border border-border rounded px-2 py-0.5 text-gray-300">{p}</span>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
