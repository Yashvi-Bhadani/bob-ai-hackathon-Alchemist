import type { CombinedRiskResult, BottleneckListResponse } from '../types'

interface Props {
  criticalCount: number
  highCount?: number
  mostCritical: string | null
  combinedRisk: CombinedRiskResult | null
  bottleneckData: BottleneckListResponse | null
  loading: boolean
}

const TIER_COLORS: Record<string, string> = {
  GREEN: '#3fb950',
  AMBER: '#d29922',
  RED: '#f85149',
  CRITICAL: '#f85149',
}

export function StatusBar({ criticalCount, highCount = 0, mostCritical, combinedRisk, bottleneckData, loading }: Props) {
  const tier = combinedRisk?.risk_tier ?? 'GREEN'
  const tierColor = TIER_COLORS[tier] ?? '#58a6ff'
  const spofCount = bottleneckData?.bottlenecks?.filter(b => b.is_bottleneck).length ?? 0

  return (
    <div className="bg-panel border border-border rounded-lg px-4 py-2 flex items-center gap-6 text-xs overflow-x-auto">
      {/* System status */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <div className={`w-2 h-2 rounded-full ${loading ? 'bg-yellow-400 animate-pulse' : 'bg-green-400'}`} />
        <span className="text-muted font-mono">{loading ? 'UPDATING…' : 'LIVE'}</span>
      </div>

      <div className="h-4 w-px bg-border" />

      {/* Tool counts */}
      <div className="flex items-center gap-4 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-muted">Critical:</span>
          <span className={`font-mono font-bold ${criticalCount > 0 ? 'text-red-400' : 'text-green-400'}`}>
            {criticalCount}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted">Bottlenecks:</span>
          <span className={`font-mono font-bold ${spofCount > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
            {spofCount}
          </span>
        </div>
        {mostCritical && (
          <span className="font-mono text-red-400 border border-red-700/60 bg-red-900/20 px-1.5 py-0.5 rounded">
            ● {mostCritical}
          </span>
        )}
      </div>

      <div className="h-4 w-px bg-border" />

      {/* Selected tool combined risk */}
      {combinedRisk && (
        <>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-muted">Selected Tool:</span>
            <span className="font-mono text-gray-200">{combinedRisk.tool_id}</span>
          </div>

          <div className="h-4 w-px bg-border" />

          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-muted">Mfg. Risk:</span>
            <span className="font-mono" style={{ color: TIER_COLORS[combinedRisk.risk_tier] }}>
              {(combinedRisk.manufacturing_risk_score * 100).toFixed(1)}%
            </span>
          </div>

          <div className="h-4 w-px bg-border" />

          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-muted">Supply Risk:</span>
            <span className="font-mono" style={{ color: TIER_COLORS[combinedRisk.supply_risk?.risk_tier ?? 'GREEN'] }}>
              {(combinedRisk.supply_chain_risk_score * 100).toFixed(1)}%
            </span>
          </div>

          <div className="h-4 w-px bg-border" />

          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-muted">Combined:</span>
            <span
              className="font-mono font-bold text-sm"
              style={{ color: tierColor }}
            >
              {(combinedRisk.combined_risk_score * 100).toFixed(1)}%
            </span>
            <span
              className="rounded px-1.5 py-0.5 border font-semibold text-xs"
              style={{
                color: tierColor,
                borderColor: tierColor + '60',
                backgroundColor: tierColor + '15',
              }}
            >
              {combinedRisk.risk_tier_label}
            </span>
          </div>

          {combinedRisk.supply_risk?.has_spof && (
            <>
              <div className="h-4 w-px bg-border" />
              <div className="flex items-center gap-1 text-red-400 flex-shrink-0">
                <span>⚠ SPOF</span>
                <span className="text-muted font-mono">{combinedRisk.primary_material_id}</span>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
