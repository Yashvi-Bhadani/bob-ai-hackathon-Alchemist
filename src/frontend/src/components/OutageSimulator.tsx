import { useState } from 'react'
import type { OutageSimulationResult } from '../types'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'

interface Props {
  selectedTool: string
  outageHours: number
  outageResult: OutageSimulationResult | null
  onChangeHours: (h: number) => void
  onRunOutage: (run: boolean) => void
  isRunning: boolean
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls = {
    CRITICAL: 'badge-critical',
    HIGH: 'badge-red',
    MEDIUM: 'badge-amber',
    LOW: 'badge-green',
  }[severity] ?? 'badge-amber'
  return (
    <span className={`text-xs rounded px-1.5 py-0.5 font-mono ${cls}`}>
      {severity}
    </span>
  )
}

export function OutageSimulator({
  selectedTool,
  outageHours,
  outageResult,
  onChangeHours,
  onRunOutage,
  isRunning,
}: Props) {
  // Build simple backlog progression for chart
  const chartData = outageResult
    ? (() => {
        const points: Array<{ t: string; backlog: number }> = []
        const steps = 12
        // Phase 1: backlog builds during outage
        for (let i = 0; i <= steps / 2; i++) {
          const t = (i / (steps / 2)) * outageHours
          const b = Math.round((outageResult.outage_backlog_lots / (steps / 2)) * i)
          points.push({ t: `+${t.toFixed(0)}h`, backlog: b + (i === 0 ? 0 : 0) })
        }
        // Phase 2: recovery (if recoverable)
        if (outageResult.is_recoverable && outageResult.recovery_hours) {
          const rec = outageResult.recovery_hours
          for (let i = 1; i <= steps / 2; i++) {
            const t = outageHours + (i / (steps / 2)) * rec
            const remaining = Math.max(
              0,
              outageResult.total_backlog_lots * (1 - i / (steps / 2))
            )
            points.push({ t: `+${t.toFixed(0)}h`, backlog: Math.round(remaining) })
          }
        }
        return points
      })()
    : []

  return (
    <div className="bg-panel border border-border rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-accent text-xs font-semibold uppercase tracking-widest">
          Outage Simulator
        </h2>
        <span className="text-muted text-xs font-mono">{selectedTool}</span>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        <label className="text-xs text-muted whitespace-nowrap">Outage duration</label>
        <input
          type="range"
          min={1}
          max={48}
          step={1}
          value={outageHours}
          onChange={e => onChangeHours(Number(e.target.value))}
          className="flex-1 accent-accent"
        />
        <span className="text-xs font-mono text-yellow-400 w-12 text-right">{outageHours}h</span>
        <button
          onClick={() => onRunOutage(!isRunning)}
          className={`text-xs px-3 py-1.5 rounded border font-mono transition-colors
            ${isRunning
              ? 'border-red-500 bg-red-900/30 text-red-400 hover:bg-red-900/50'
              : 'border-accent bg-accent/10 text-accent hover:bg-accent/20'
            }`}
        >
          {isRunning ? '■ CLEAR' : '▶ RUN'}
        </button>
      </div>

      {/* Results */}
      {outageResult && isRunning ? (
        <>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Outage Backlog', value: `${outageResult.outage_backlog_lots} lots`, color: 'text-red-400' },
              { label: 'Total Backlog', value: `${outageResult.total_backlog_lots} lots`, color: 'text-red-400' },
              { label: 'Backlog Wafers', value: `${outageResult.backlog_wafers.toLocaleString()}`, color: 'text-yellow-400' },
              {
                label: 'Recovery Time',
                value: outageResult.recovery_hours != null
                  ? `${outageResult.recovery_hours.toFixed(1)}h`
                  : 'IMPOSSIBLE',
                color: outageResult.is_recoverable ? 'text-green-400' : 'text-red-400',
              },
            ].map(item => (
              <div key={item.label} className="bg-surface rounded border border-border p-2">
                <div className="text-muted text-xs">{item.label}</div>
                <div className={`font-mono text-sm font-semibold ${item.color}`}>{item.value}</div>
              </div>
            ))}
          </div>

          {/* Recovery status badge */}
          <div className={`text-xs px-3 py-1.5 rounded border text-center font-mono
            ${outageResult.is_recoverable
              ? 'border-green-700/60 bg-green-900/20 text-green-400'
              : 'border-red-700/60 bg-red-900/20 text-red-400'}`}>
            {outageResult.is_recoverable
              ? `✓ Recoverable within ${outageResult.recovery_hours?.toFixed(1)}h`
              : '✗ Recovery impossible — arrival rate ≥ max capacity'}
          </div>

          {/* Backlog chart */}
          {chartData.length > 0 && (
            <div className="h-28">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
                  <defs>
                    <linearGradient id="backlogGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f85149" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#f85149" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="t" tick={{ fill: '#8b949e', fontSize: 9 }} interval={2} />
                  <YAxis tick={{ fill: '#8b949e', fontSize: 9 }} />
                  <Tooltip
                    contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }}
                    formatter={(val: number) => [`${val} lots`, 'Backlog']}
                  />
                  <ReferenceLine
                    x={`+${outageHours}h`}
                    stroke="#d29922"
                    strokeDasharray="3 3"
                    label={{ value: 'RESTORE', fill: '#d29922', fontSize: 9 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="backlog"
                    stroke="#f85149"
                    fill="url(#backlogGrad)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Downstream impact */}
          {outageResult.downstream_impact.length > 0 && (
            <div className="border-t border-border pt-2">
              <div className="text-xs text-muted mb-1 uppercase tracking-wider">Downstream Impact</div>
              <div className="flex flex-col gap-1">
                {outageResult.downstream_impact.slice(0, 4).map((d, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-gray-400 truncate max-w-32">{d.affected_step}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-muted font-mono">+{d.delay_hours.toFixed(1)}h</span>
                      <SeverityBadge severity={d.impact_severity} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center text-muted text-xs py-6 border border-dashed border-border rounded">
          Set outage duration and click ▶ RUN to simulate
        </div>
      )}
    </div>
  )
}
