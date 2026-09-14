import type { CombinedRiskResult } from '../types'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

interface Props {
  combinedRisk: CombinedRiskResult | null
}

const RISK_COLORS: Record<string, string> = {
  CRITICAL: '#f85149',
  HIGH: '#f85149',
  RED: '#f85149',
  MEDIUM: '#d29922',
  AMBER: '#d29922',
  LOW: '#58a6ff',
  MODERATE: '#58a6ff',
  GREEN: '#3fb950',
  MONOPOLY: '#f85149',
}

const HHI_MAX = 10000
const PIE_COLORS = ['#f85149', '#d29922', '#58a6ff', '#3fb950', '#a371f7']

export function SupplyRiskPanel({ combinedRisk }: Props) {
  const supply = combinedRisk?.supply_risk ?? null

  // Build HHI pie using supply chain risk attributes we have
  const hhi = supply?.hhi_value ?? null
  const hhiPieData = hhi != null
    ? [
        { name: 'Concentration', value: hhi },
        { name: 'Remaining', value: Math.max(0, HHI_MAX - hhi) },
      ]
    : []

  const geopoliticalColor = RISK_COLORS[supply?.risk_tier ?? 'LOW']

  return (
    <div className="bg-panel border border-border rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-accent text-xs font-semibold uppercase tracking-widest">
          Supply Chain Risk
        </h2>
        {supply && (
          <span
            className="text-xs font-mono rounded px-2 py-0.5 border"
            style={{
              color: RISK_COLORS[supply.risk_tier],
              borderColor: RISK_COLORS[supply.risk_tier] + '60',
              backgroundColor: RISK_COLORS[supply.risk_tier] + '15',
            }}
          >
            {supply.risk_tier}
          </span>
        )}
      </div>

      {supply ? (
        <>
          {/* Material */}
          <div className="text-xs text-muted">
            Material: <span className="text-gray-300 font-mono">{supply.material_id}</span>
            {' — '}{supply.material_name}
          </div>

          {/* Key metrics grid */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            {/* HHI */}
            <div className="bg-surface rounded border border-border p-2 col-span-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-muted">Supplier Concentration (HHI)</span>
                <span
                  className="font-mono font-semibold"
                  style={{ color: supply.hhi_value && supply.hhi_value > 2500 ? '#f85149' : supply.hhi_value && supply.hhi_value > 1500 ? '#d29922' : '#3fb950' }}
                >
                  {supply.hhi_value?.toFixed(0) ?? 'N/A'}
                </span>
              </div>
              {hhi != null && (
                <div className="flex gap-2 items-center">
                  <div className="score-bar-bg flex-1">
                    <div
                      className="score-bar-fill"
                      style={{
                        width: `${Math.min(100, (hhi / HHI_MAX) * 100)}%`,
                        backgroundColor: hhi > 2500 ? '#f85149' : hhi > 1500 ? '#d29922' : '#3fb950',
                      }}
                    />
                  </div>
                  <span className="text-muted text-xs w-16 text-right">/ 10,000</span>
                </div>
              )}
            </div>

            {/* Inventory Coverage */}
            <div className="bg-surface rounded border border-border p-2">
              <div className="text-muted mb-0.5">Inventory Coverage</div>
              <div
                className="font-mono font-semibold text-sm"
                style={{ color: RISK_COLORS[supply.inventory_risk_tier] }}
              >
                {supply.inventory_coverage_days?.toFixed(1) ?? '—'} days
              </div>
              <div style={{ color: RISK_COLORS[supply.inventory_risk_tier] }} className="text-xs">
                {supply.inventory_risk_tier}
              </div>
            </div>

            {/* SPOF */}
            <div className={`bg-surface rounded border p-2 ${supply.has_spof ? 'border-red-700/60' : 'border-border'}`}>
              <div className="text-muted mb-0.5">SPOF Detected</div>
              <div className={`font-mono font-semibold text-sm ${supply.has_spof ? 'text-red-400' : 'text-green-400'}`}>
                {supply.has_spof ? '⚠ YES' : '✓ NO'}
              </div>
              <div className="text-muted text-xs">Single Point of Failure</div>
            </div>

            {/* Geopolitical risk */}
            <div className="bg-surface rounded border border-border p-2 col-span-2">
              <div className="flex items-center justify-between">
                <span className="text-muted">Geopolitical Risk Score</span>
                <span
                  className="font-mono font-semibold"
                  style={{ color: supply.geopolitical_risk_score > 0.5 ? '#f85149' : supply.geopolitical_risk_score > 0.3 ? '#d29922' : '#3fb950' }}
                >
                  {(supply.geopolitical_risk_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="score-bar-bg mt-1">
                <div
                  className="score-bar-fill"
                  style={{
                    width: `${supply.geopolitical_risk_score * 100}%`,
                    backgroundColor: geopoliticalColor,
                  }}
                />
              </div>
            </div>
          </div>

          {/* HHI Donut */}
          {hhiPieData.length > 0 && (
            <div className="h-28 flex items-center">
              <ResponsiveContainer width="50%" height="100%">
                <PieChart>
                  <Pie
                    data={hhiPieData}
                    innerRadius={28}
                    outerRadius={44}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    <Cell fill={hhi! > 2500 ? '#f85149' : hhi! > 1500 ? '#d29922' : '#3fb950'} />
                    <Cell fill="#1c2128" />
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }}
                    formatter={(v: number) => [v.toFixed(0), '']}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 flex flex-col gap-1 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500" />
                  <span className="text-muted">HHI &gt; 2500 = High</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-yellow-500" />
                  <span className="text-muted">1500–2500 = Moderate</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-muted">&lt; 1500 = Low</span>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center text-muted text-xs py-6 border border-dashed border-border rounded">
          Select a tool to view supply chain risk
        </div>
      )}
    </div>
  )
}
