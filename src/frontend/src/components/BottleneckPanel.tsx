import type { BottleneckListResponse, BottleneckAssessment } from '../types'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  LineChart, Line, CartesianGrid,
} from 'recharts'

interface Props {
  data: BottleneckListResponse | null
  selectedTool: string
  onSelectTool: (id: string) => void
}

// Score is 0–100; color by severity tier
const SEVERITY_COLOR = (score: number) => {
  if (score >= 85) return '#f85149'   // CRITICAL
  if (score >= 70) return '#d29922'   // HIGH
  if (score >= 40) return '#58a6ff'   // MEDIUM
  return '#3fb950'                     // LOW
}

const SEVERITY_LABEL = (score: number) => {
  if (score >= 85) return 'CRITICAL'
  if (score >= 70) return 'HIGH'
  if (score >= 40) return 'MEDIUM'
  return 'LOW'
}

function ScoreBar({ value, label, max = 100 }: { value: number; label: string; max?: number }) {
  const pct = (value / max) * 100
  const color = SEVERITY_COLOR(pct)
  return (
    <div className="mb-1">
      <div className="flex justify-between text-xs text-muted mb-0.5">
        <span>{label}</span>
        <span style={{ color }}>{value.toFixed(1)}{max === 100 ? '' : ''}</span>
      </div>
      <div className="score-bar-bg">
        <div
          className="score-bar-fill"
          style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

export function BottleneckPanel({ data, selectedTool, onSelectTool }: Props) {
  const tools: BottleneckAssessment[] = data?.bottlenecks ?? []
  const selected = tools.find(t => t.tool_id === selectedTool)

  const radarData = selected
    ? [
        { subject: 'Utilisation', value: selected.utilization },
        { subject: 'WIP Pressure', value: selected.wip_pressure_normalized },
        { subject: 'Cap. Pressure', value: selected.capacity_pressure },
        { subject: 'Score', value: selected.bottleneck_score / 100 },
        { subject: 'Downtime', value: Math.min(selected.downtime_pct * 5, 1) },
      ]
    : []

  const barData = tools.map(t => ({
    name: t.tool_id,
    score: t.bottleneck_score,
    fill: SEVERITY_COLOR(t.bottleneck_score),
  }))

  // History line chart for selected tool (from snapshots)
  const histData = selected?.history?.slice(-8).map((h, i) => ({
    i,
    wip: h.wip_units ?? 0,
    util: Math.round((h.utilization ?? 0) * 100),
  })) ?? []

  return (
    <div className="bg-panel border border-border rounded-lg p-4 h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-accent text-xs font-semibold uppercase tracking-widest">
          Bottleneck Detection
        </h2>
        {data && (
          <span className="text-xs text-red-400 font-mono">
            {data.critical_count} CRITICAL
          </span>
        )}
      </div>

      {/* Tool selector list */}
      <div className="flex flex-col gap-1 overflow-y-auto max-h-52">
        {tools.map(t => (
          <button
            key={t.tool_id}
            onClick={() => onSelectTool(t.tool_id)}
            className={`text-left px-3 py-2 rounded border text-xs font-mono transition-colors
              ${t.tool_id === selectedTool
                ? 'border-accent bg-accent/10 text-accent'
                : 'border-border hover:border-gray-500 text-gray-400 hover:text-gray-200'
              }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold">{t.tool_id}</span>
              {t.severity === 'CRITICAL' && (
                <span className="text-red-400 text-xs">● CRITICAL</span>
              )}
              {t.severity === 'HIGH' && (
                <span className="text-yellow-400 text-xs">▲ HIGH</span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-muted">{t.process_name}</span>
              <span className="ml-auto" style={{ color: SEVERITY_COLOR(t.bottleneck_score) }}>
                {t.bottleneck_score.toFixed(1)}
              </span>
            </div>
            <div className="score-bar-bg mt-1">
              <div
                className="score-bar-fill"
                style={{
                  width: `${t.bottleneck_score}%`,
                  backgroundColor: SEVERITY_COLOR(t.bottleneck_score)
                }}
              />
            </div>
          </button>
        ))}
      </div>

      {/* Selected tool detail */}
      {selected && (
        <>
          <div className="border-t border-border pt-3">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-muted uppercase tracking-wider">
                {selected.tool_id} — {selected.process_name}
              </div>
              <span
                className="text-xs rounded px-1.5 py-0.5 border font-mono"
                style={{
                  color: SEVERITY_COLOR(selected.bottleneck_score),
                  borderColor: SEVERITY_COLOR(selected.bottleneck_score) + '60',
                  backgroundColor: SEVERITY_COLOR(selected.bottleneck_score) + '15',
                }}
              >
                {SEVERITY_LABEL(selected.bottleneck_score)}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-x-4 text-xs mb-3">
              <div className="text-muted">Utilisation</div>
              <div className="text-right font-mono" style={{ color: SEVERITY_COLOR(selected.utilization_pct) }}>
                {selected.utilization_pct.toFixed(1)}%
              </div>
              <div className="text-muted">WIP Units</div>
              <div className="text-right font-mono text-yellow-400">{selected.wip_units}</div>
              <div className="text-muted">Normal WIP</div>
              <div className="text-right font-mono text-muted">{selected.normal_wip}</div>
              <div className="text-muted">Downtime</div>
              <div className="text-right font-mono text-red-400">{selected.downtime_hours.toFixed(1)}h</div>
              <div className="text-muted">Trend</div>
              <div className={`text-right font-mono text-xs ${
                selected.wip_trend === 'RISING' ? 'text-red-400' :
                selected.wip_trend === 'FALLING' ? 'text-green-400' :
                'text-muted'
              }`}>{selected.wip_trend}</div>
            </div>
            <ScoreBar value={selected.wip_pressure_normalized * 100} label="WIP Pressure" />
            <ScoreBar value={selected.capacity_pressure * 100} label="Capacity Pressure" />
            <ScoreBar value={selected.bottleneck_score} label="Bottleneck Score" />
          </div>

          {/* Radar chart */}
          <div className="h-36">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="#30363d" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#8b949e', fontSize: 9 }} />
                <Radar
                  dataKey="value"
                  stroke={SEVERITY_COLOR(selected.bottleneck_score)}
                  fill={SEVERITY_COLOR(selected.bottleneck_score)}
                  fillOpacity={0.25}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* WIP trend history */}
          {histData.length > 1 && (
            <div className="border-t border-border pt-2">
              <div className="text-xs text-muted mb-1">WIP Trend ({histData.length} snapshots)</div>
              <div className="h-20">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={histData} margin={{ top: 0, right: 0, bottom: 0, left: -25 }}>
                    <CartesianGrid stroke="#30363d" strokeDasharray="3 3" />
                    <XAxis dataKey="i" hide />
                    <YAxis tick={{ fill: '#8b949e', fontSize: 9 }} />
                    <Tooltip
                      contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 10 }}
                      formatter={(val: number) => [`${val}`, 'WIP']}
                    />
                    <Line
                      type="monotone"
                      dataKey="wip"
                      stroke={SEVERITY_COLOR(selected.bottleneck_score)}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}

      {/* All tools bar chart */}
      <div className="h-28 border-t border-border pt-2">
        <div className="text-xs text-muted mb-1">All Tools — Score (0–100)</div>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={barData} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
            <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 9 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#8b949e', fontSize: 9 }} />
            <Tooltip
              contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }}
              formatter={(val: number) => [val.toFixed(1), 'Score']}
            />
            <Bar dataKey="score" radius={[2, 2, 0, 0]}>
              {barData.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
