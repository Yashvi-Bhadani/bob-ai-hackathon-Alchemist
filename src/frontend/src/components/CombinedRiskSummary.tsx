import type { CombinedRiskResult } from '../types'
import {
  RadialBarChart, RadialBar, ResponsiveContainer, Tooltip,
} from 'recharts'

interface Props {
  combinedRisk: CombinedRiskResult | null
  loading: boolean
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

const FEASIBILITY_BADGE: Record<string, string> = {
  HIGH: 'text-green-400 border-green-700/60 bg-green-900/20',
  MEDIUM: 'text-yellow-400 border-yellow-700/60 bg-yellow-900/20',
  LOW: 'text-red-400 border-red-700/60 bg-red-900/20',
}

export function CombinedRiskSummary({ combinedRisk, loading }: Props) {
  if (loading) {
    return (
      <div className="bg-panel border border-border rounded-lg p-4 flex items-center justify-center h-48">
        <div className="text-muted text-xs animate-pulse">Computing risk assessment…</div>
      </div>
    )
  }

  if (!combinedRisk) return null

  const tierColor = TIER_COLORS[combinedRisk.risk_tier] ?? '#58a6ff'

  const radialData = [
    { name: 'Manufacturing Risk', value: Math.round(combinedRisk.manufacturing_risk_score * 100), fill: '#f85149' },
    { name: 'Supply Chain Risk', value: Math.round(combinedRisk.supply_chain_risk_score * 100), fill: '#d29922' },
    { name: 'Combined Risk', value: Math.round(combinedRisk.combined_risk_score * 100), fill: tierColor },
  ]

  return (
    <div className="bg-panel border border-border rounded-lg p-4 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-accent text-xs font-semibold uppercase tracking-widest">
          Combined Risk Assessment
        </h2>
        <div className="flex items-center gap-2">
          <span
            className="text-sm font-mono font-bold"
            style={{ color: tierColor }}
          >
            {combinedRisk.combined_risk_score.toFixed(3)}
          </span>
          <span
            className="text-xs font-semibold rounded px-2 py-0.5 border"
            style={{
              color: tierColor,
              borderColor: tierColor + '60',
              backgroundColor: tierColor + '15',
            }}
          >
            {combinedRisk.risk_tier_label}
          </span>
          <span className="text-xs text-muted">
            Confidence: {combinedRisk.confidence_pct}%
          </span>
        </div>
      </div>

      <div className="flex gap-4">
        {/* Radial chart */}
        <div className="w-44 h-40 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart
              innerRadius={20}
              outerRadius={70}
              data={radialData}
              startAngle={90}
              endAngle={-270}
            >
              <RadialBar dataKey="value" cornerRadius={4} />
              <Tooltip
                contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }}
                formatter={(val: number) => [`${val}%`, '']}
              />
            </RadialBarChart>
          </ResponsiveContainer>
        </div>

        {/* Score breakdown */}
        <div className="flex-1 flex flex-col gap-2 justify-center">
          {[
            { label: 'Manufacturing Risk', score: combinedRisk.manufacturing_risk_score, color: '#f85149' },
            { label: 'Supply Chain Risk',  score: combinedRisk.supply_chain_risk_score,  color: '#d29922' },
            { label: 'Combined Score',     score: combinedRisk.combined_risk_score,       color: tierColor },
          ].map(item => (
            <div key={item.label}>
              <div className="flex justify-between text-xs mb-0.5">
                <span className="text-muted">{item.label}</span>
                <span className="font-mono" style={{ color: item.color }}>
                  {(item.score * 100).toFixed(1)}%
                </span>
              </div>
              <div className="score-bar-bg">
                <div
                  className="score-bar-fill"
                  style={{ width: `${item.score * 100}%`, backgroundColor: item.color }}
                />
              </div>
            </div>
          ))}
          <div className="text-xs text-muted mt-1">
            Tool: <span className="text-gray-300 font-mono">{combinedRisk.tool_id}</span>
            {' · '}{combinedRisk.process_step}
            {combinedRisk.primary_material_id && (
              <> · Material: <span className="font-mono">{combinedRisk.primary_material_id}</span></>
            )}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      {combinedRisk.recommendations.length > 0 && (
        <div className="border-t border-border pt-3">
          <div className="text-xs text-muted mb-2 uppercase tracking-wider">
            Mitigation Recommendations ({combinedRisk.recommendations.length})
          </div>
          <div className="flex flex-col gap-2">
            {combinedRisk.recommendations.map((rec, i) => (
              <div
                key={i}
                className="bg-surface rounded border border-border p-3 flex gap-3"
              >
                <div className="text-lg leading-none mt-0.5">
                  {CAT_ICONS[rec.category] ?? '💡'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-mono text-muted">#{rec.priority}</span>
                    <span className="text-xs font-semibold text-gray-300">{rec.category}</span>
                    <span
                      className={`text-xs rounded px-1.5 py-0.5 border font-mono ${FEASIBILITY_BADGE[rec.feasibility]}`}
                    >
                      {rec.feasibility}
                    </span>
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
    </div>
  )
}
