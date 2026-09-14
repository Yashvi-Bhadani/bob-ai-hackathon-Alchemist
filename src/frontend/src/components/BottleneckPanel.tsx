import type { BottleneckListResponse } from '../types'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell
} from 'recharts'

interface Props {
  data: BottleneckListResponse | null
  selectedTool: string
  onSelectTool: (id: string) => void
}

const SCORE_COLORS = (score: number) => {
  if (score >= 0.75) return '#f85149'
  if (score >= 0.55) return '#d29922'
  if (score >= 0.35) return '#58a6ff'
  return '#3fb950'
}

function ScoreBar({ value, label }: { value: number; label: string }) {
  const color = SCORE_COLORS(value)
  return (
    <div className="mb-1">
      <div className="flex justify-between text-xs text-muted mb-0.5">
        <span>{label}</span>
        <span style={{ color }}>{(value * 100).toFixed(1)}%</span>
      </div>
      <div className="score-bar-bg">
        <div
          className="score-bar-fill"
          style={{ width: `${value * 100}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

export function BottleneckPanel({ data, selectedTool, onSelectTool }: Props) {
  const tools = data?.tools ?? []
  const selected = tools.find(t => t.tool_id === selectedTool)

  const radarData = selected
    ? [
        { subject: 'Utilisation', value: selected.utilization_pct / 100 },
        { subject: 'WIP Pressure', value: selected.wip_pressure },
        { subject: 'Cap. Pressure', value: selected.capacity_pressure },
        { subject: 'Score', value: selected.bottleneck_score },
        { subject: 'Downtime', value: Math.min(selected.downtime_hrs / 8, 1) },
      ]
    : []

  const barData = tools.map(t => ({
    name: t.tool_id,
    score: t.bottleneck_score,
    fill: SCORE_COLORS(t.bottleneck_score),
  }))

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
              {t.is_critical && (
                <span className="text-red-400 text-xs">● CRITICAL</span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-muted">{t.process_step}</span>
              <span className="ml-auto" style={{ color: SCORE_COLORS(t.bottleneck_score) }}>
                {t.bottleneck_score.toFixed(3)}
              </span>
            </div>
            <div className="score-bar-bg mt-1">
              <div
                className="score-bar-fill"
                style={{
                  width: `${t.bottleneck_score * 100}%`,
                  backgroundColor: SCORE_COLORS(t.bottleneck_score)
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
            <div className="text-xs text-muted mb-2 uppercase tracking-wider">
              {selected.tool_id} — {selected.process_step}
            </div>
            <div className="grid grid-cols-2 gap-x-4 text-xs mb-3">
              <div className="text-muted">Utilisation</div>
              <div className="text-right font-mono" style={{ color: SCORE_COLORS(selected.utilization_pct / 100) }}>
                {selected.utilization_pct.toFixed(1)}%
              </div>
              <div className="text-muted">WIP Lots</div>
              <div className="text-right font-mono text-yellow-400">{selected.wip_lots}</div>
              <div className="text-muted">Downtime (shift)</div>
              <div className="text-right font-mono text-red-400">{selected.downtime_hrs.toFixed(1)}h</div>
            </div>
            <ScoreBar value={selected.wip_pressure} label="WIP Pressure" />
            <ScoreBar value={selected.capacity_pressure} label="Capacity Pressure" />
            <ScoreBar value={selected.bottleneck_score} label="Bottleneck Score" />
          </div>

          {/* Radar chart */}
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="#30363d" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#8b949e', fontSize: 10 }} />
                <Radar
                  dataKey="value"
                  stroke={SCORE_COLORS(selected.bottleneck_score)}
                  fill={SCORE_COLORS(selected.bottleneck_score)}
                  fillOpacity={0.25}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {/* All tools bar chart */}
      <div className="h-28 border-t border-border pt-2">
        <div className="text-xs text-muted mb-1">All Tools — Bottleneck Score</div>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={barData} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
            <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 9 }} />
            <YAxis domain={[0, 1]} tick={{ fill: '#8b949e', fontSize: 9 }} />
            <Tooltip
              contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }}
              formatter={(val: number) => val.toFixed(3)}
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
