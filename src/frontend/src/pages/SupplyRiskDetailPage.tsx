/**
 * /supply-risk/:materialId — Full supply chain risk detail for a single material.
 *
 * Shows:
 * - Combined supply risk score and tier
 * - HHI value with concentration level
 * - Supplier list with share breakdown (pie chart)
 * - Inventory coverage vs. lead time
 * - SPOF analysis
 * - Geopolitical risk
 * - Active recommendations
 */
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { api } from '../api'
import { NavBar } from '../components/NavBar'
import type { MaterialSupplyRisk, HHIResult, InventoryCoverageResult, GeopoliticalRiskItem, SPOFResult } from '../types'

const TIER_COLORS: Record<string, string> = {
  GREEN: '#3fb950',
  AMBER: '#d29922',
  RED: '#f85149',
  CRITICAL: '#f85149',
}
const RISK_COLORS: Record<string, string> = {
  CRITICAL: '#f85149', HIGH: '#f85149', RED: '#f85149',
  MEDIUM: '#d29922', AMBER: '#d29922',
  LOW: '#3fb950', MODERATE: '#58a6ff', GREEN: '#3fb950',
}
const PIE_COLORS = ['#f85149', '#d29922', '#58a6ff', '#3fb950', '#a371f7', '#e8b000']

export function SupplyRiskDetailPage() {
  const { materialId } = useParams<{ materialId: string }>()
  const [risk, setRisk] = useState<MaterialSupplyRisk | null>(null)
  const [hhi, setHhi] = useState<HHIResult | null>(null)
  const [inv, setInv] = useState<InventoryCoverageResult | null>(null)
  const [spof, setSpof] = useState<SPOFResult | null>(null)
  const [geo, setGeo] = useState<GeopoliticalRiskItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!materialId) return
    setLoading(true)
    setError(null)

    Promise.all([
      api.supply.getMaterialRisk(materialId),
      api.supply.getHHI(),
      api.supply.getInventory(),
      api.supply.getSPOF(),
      api.supply.getGeopolitical(),
    ])
      .then(([riskData, hhiList, invList, spofList, geoList]) => {
        setRisk(riskData)
        setHhi(hhiList.find(h => h.material_id === materialId) ?? null)
        setInv(invList.find(i => i.material_id === materialId) ?? null)
        setSpof(spofList.find(s => s.material_id === materialId) ?? null)
        setGeo(geoList.filter(g => g.affected_material_id === materialId || g.affected_material_id === null))
        setLoading(false)
      })
      .catch(err => {
        setError(String(err))
        setLoading(false)
      })
  }, [materialId])

  const tierColor = risk ? TIER_COLORS[risk.risk_tier] ?? '#58a6ff' : '#58a6ff'

  if (loading) {
    return (
      <div className="min-h-screen bg-surface">
        <NavBar />
        <div className="flex items-center justify-center h-64">
          <span className="text-muted text-sm animate-pulse">Loading supply risk for {materialId}…</span>
        </div>
      </div>
    )
  }

  if (error || !risk) {
    return (
      <div className="min-h-screen bg-surface">
        <NavBar />
        <div className="max-w-4xl mx-auto p-6">
          <div className="bg-red-900/20 border border-red-700/60 rounded p-4 text-red-400 text-sm">
            {error ?? `Material '${materialId}' not found.`}
          </div>
          <Link to="/" className="text-accent text-sm mt-4 inline-block hover:underline">← Back to Dashboard</Link>
        </div>
      </div>
    )
  }

  const supplierPieData = hhi?.suppliers.map((s, i) => ({
    name: s.supplier_name.replace(' (Demo)', ''),
    value: s.share_pct,
    fill: PIE_COLORS[i % PIE_COLORS.length],
  })) ?? []

  const inventoryBarData = inv ? [
    { name: 'On Hand', value: inv.quantity_on_hand, fill: '#58a6ff' },
    { name: 'Reorder Pt.', value: inv.reorder_point, fill: '#d29922' },
    { name: 'Safety Stock', value: inv.safety_stock, fill: '#f85149' },
  ] : []

  return (
    <div className="min-h-screen bg-surface text-gray-200">
      <NavBar />
      <div className="max-w-screen-xl mx-auto p-6 flex flex-col gap-6">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-muted">
          <Link to="/" className="text-accent hover:underline">Dashboard</Link>
          <span>/</span>
          <span>Supply Risk</span>
          <span>/</span>
          <span className="text-gray-300 font-mono">{materialId}</span>
        </div>

        {/* Hero */}
        <div className="bg-panel border border-border rounded-lg p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-lg font-semibold text-gray-100 mb-1">{risk.material_name}</h1>
              <div className="text-xs text-muted font-mono mb-4">{risk.material_id}</div>
              <div className="flex items-center gap-3">
                <div className="text-4xl font-mono font-black" style={{ color: tierColor }}>
                  {(risk.combined_supply_risk * 100).toFixed(1)}%
                </div>
                <div>
                  <span
                    className="text-sm font-semibold rounded px-2 py-0.5 border"
                    style={{ color: tierColor, borderColor: tierColor + '60', backgroundColor: tierColor + '15' }}
                  >
                    {risk.risk_tier}
                  </span>
                  <div className="text-xs text-muted mt-1">Combined Supply Risk</div>
                </div>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2 text-xs">
              {risk.has_spof && (
                <span className="text-red-400 border border-red-700/60 bg-red-900/20 rounded px-2 py-1 font-mono">
                  ⚠ SINGLE POINT OF FAILURE
                </span>
              )}
              {hhi && hhi.hhi_value > 2500 && (
                <span className="text-yellow-400 border border-yellow-700/60 bg-yellow-900/20 rounded px-2 py-1 font-mono">
                  HIGH HHI CONCENTRATION
                </span>
              )}
            </div>
          </div>

          {/* Risk score breakdown */}
          <div className="grid grid-cols-4 gap-3 mt-4">
            {[
              { label: 'HHI Score', value: `${risk.hhi_value?.toFixed(0) ?? 'N/A'}`, color: risk.hhi_value && risk.hhi_value > 2500 ? '#f85149' : risk.hhi_value && risk.hhi_value > 1500 ? '#d29922' : '#3fb950' },
              { label: 'Inventory Risk', value: risk.inventory_risk_tier, color: RISK_COLORS[risk.inventory_risk_tier] ?? '#58a6ff' },
              { label: 'SPOF', value: risk.has_spof ? '⚠ YES' : '✓ NO', color: risk.has_spof ? '#f85149' : '#3fb950' },
              { label: 'Geo Risk', value: `${(risk.geopolitical_risk_score * 100).toFixed(0)}%`, color: risk.geopolitical_risk_score > 0.5 ? '#f85149' : risk.geopolitical_risk_score > 0.3 ? '#d29922' : '#3fb950' },
            ].map(item => (
              <div key={item.label} className="bg-surface rounded border border-border p-3">
                <div className="text-xs text-muted mb-1">{item.label}</div>
                <div className="font-mono text-sm font-bold" style={{ color: item.color }}>{item.value}</div>
              </div>
            ))}
          </div>
          <div className="text-xs text-muted mt-2">
            Formula: 0.30 × HHI + 0.30 × Inventory + 0.25 × SPOF + 0.15 × Geopolitical
          </div>
        </div>

        {/* HHI + Supplier breakdown */}
        {hhi && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-panel border border-border rounded-lg p-4">
              <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">
                Supplier Concentration (HHI: {hhi.hhi_value.toFixed(0)})
              </h2>
              <div className="flex items-center gap-2 mb-3">
                <div className="text-2xl font-mono font-black" style={{ color: hhi.hhi_value > 2500 ? '#f85149' : hhi.hhi_value > 1500 ? '#d29922' : '#3fb950' }}>
                  {hhi.concentration_level}
                </div>
                <div className="text-xs text-muted">
                  {hhi.supplier_count} qualified supplier{hhi.supplier_count !== 1 ? 's' : ''}
                </div>
              </div>
              {/* HHI scale bar */}
              <div className="mb-3">
                <div className="flex justify-between text-xs text-muted mb-0.5">
                  <span>0</span><span>2,500 (High)</span><span>10,000 (Monopoly)</span>
                </div>
                <div className="bg-gray-800 rounded-full h-3 relative">
                  <div
                    className="h-3 rounded-full"
                    style={{ width: `${Math.min(hhi.hhi_value / 100, 100)}%`, backgroundColor: hhi.hhi_value > 2500 ? '#f85149' : hhi.hhi_value > 1500 ? '#d29922' : '#3fb950' }}
                  />
                  <div className="absolute top-0 left-[25%] h-3 w-px bg-yellow-500/50" />
                </div>
              </div>
              {/* Supplier table */}
              <div className="border border-border rounded overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-surface border-b border-border">
                      <th className="text-left px-2 py-1.5 text-muted font-normal">Supplier</th>
                      <th className="text-left px-2 py-1.5 text-muted font-normal">Country</th>
                      <th className="text-right px-2 py-1.5 text-muted font-normal">Share</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hhi.suppliers.map((s, i) => (
                      <tr key={s.supplier_id} className={i < hhi.suppliers.length - 1 ? 'border-b border-border' : ''}>
                        <td className="px-2 py-1.5 text-gray-300">{s.supplier_name.replace(' (Demo)', '')}</td>
                        <td className="px-2 py-1.5 text-muted">{s.country}</td>
                        <td className="px-2 py-1.5 text-right font-mono" style={{ color: s.share_pct >= 70 ? '#f85149' : s.share_pct >= 50 ? '#d29922' : undefined }}>
                          {s.share_pct.toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-panel border border-border rounded-lg p-4">
              <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">Supplier Share</h2>
              {supplierPieData.length > 0 ? (
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={supplierPieData} innerRadius={40} outerRadius={80} paddingAngle={2} dataKey="value">
                        {supplierPieData.map((entry, i) => (
                          <Cell key={i} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }}
                        formatter={(val: number) => [`${val.toFixed(0)}%`, 'Share']}
                      />
                      <Legend iconSize={8} wrapperStyle={{ fontSize: 10, color: '#8b949e' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="text-center text-muted text-xs py-8">No supplier data</div>
              )}
            </div>
          </div>
        )}

        {/* Inventory Coverage */}
        {inv && (
          <div className="bg-panel border border-border rounded-lg p-4">
            <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">Inventory Coverage</h2>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="bg-surface rounded border border-border p-3">
                <div className="text-xs text-muted mb-1">Coverage Days</div>
                <div className="font-mono text-2xl font-black" style={{ color: RISK_COLORS[inv.risk_tier] }}>
                  {inv.coverage_days.toFixed(1)}d
                </div>
                <div className="text-xs" style={{ color: RISK_COLORS[inv.risk_tier] }}>{inv.risk_tier} risk</div>
              </div>
              <div className="bg-surface rounded border border-border p-3">
                <div className="text-xs text-muted mb-1">On Hand</div>
                <div className="font-mono text-lg font-bold text-gray-300">{inv.quantity_on_hand.toFixed(1)}</div>
                <div className={`text-xs ${inv.below_reorder_point ? 'text-red-400' : 'text-muted'}`}>
                  {inv.below_reorder_point ? '⚠ Below reorder point' : 'Above reorder point'}
                </div>
              </div>
              <div className="bg-surface rounded border border-border p-3">
                <div className="text-xs text-muted mb-1">Daily Consumption</div>
                <div className="font-mono text-lg font-bold text-gray-300">{inv.daily_consumption.toFixed(1)}</div>
                <div className={`text-xs ${inv.below_safety_stock ? 'text-red-400' : 'text-muted'}`}>
                  {inv.below_safety_stock ? '⚠ Below safety stock' : 'Safety stock OK'}
                </div>
              </div>
            </div>
            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={inventoryBarData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="#30363d" strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#8b949e', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }} />
                  <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                    {inventoryBarData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Geopolitical Risks */}
        {geo.length > 0 && (
          <div className="bg-panel border border-border rounded-lg p-4">
            <h2 className="text-accent text-xs font-semibold uppercase tracking-widest mb-3">
              Geopolitical Risk Entries ({geo.length})
            </h2>
            <div className="flex flex-col gap-2">
              {geo.map(g => (
                <div key={g.risk_id} className="bg-surface rounded border border-border p-3">
                  <div className="flex items-start justify-between mb-1">
                    <span className="text-xs font-mono font-semibold text-gray-300">{g.affected_region}</span>
                    <span
                      className="text-xs rounded px-1.5 py-0.5 border font-mono"
                      style={{ color: RISK_COLORS[g.risk_level], borderColor: RISK_COLORS[g.risk_level] + '60', backgroundColor: RISK_COLORS[g.risk_level] + '15' }}
                    >
                      {g.risk_level}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed">{g.risk_reason}</p>
                  <div className="text-xs text-muted mt-1">{g.source} · {g.source_date}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SPOF detail */}
        {spof && (
          <div className="bg-panel border border-red-700/40 rounded-lg p-4">
            <h2 className="text-red-400 text-xs font-semibold uppercase tracking-widest mb-3">
              ⚠ Single Point of Failure Detected
            </h2>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-muted">Dominant supplier: </span>
                <span className="text-gray-300">{spof.dominant_supplier_name}</span>
              </div>
              <div>
                <span className="text-muted">Share: </span>
                <span className="text-red-400 font-mono font-semibold">{spof.dominant_share_pct.toFixed(0)}%</span>
              </div>
              <div>
                <span className="text-muted">Qualified suppliers: </span>
                <span className="text-gray-300 font-mono">{spof.qualified_supplier_count}</span>
              </div>
              <div>
                <span className="text-muted">Reason: </span>
                <span className="text-gray-300">{spof.spof_reason}</span>
              </div>
            </div>
            <div className="mt-3 p-2 bg-red-900/20 rounded border border-red-700/40 text-xs text-red-300">
              Recommendation: Initiate qualification of a second source supplier to eliminate SPOF.
              Target: reduce dominant-supplier share to ≤ 50%.
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
