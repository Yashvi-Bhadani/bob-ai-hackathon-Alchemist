import { useState, useEffect } from 'react'
import type { CombinedRiskResult } from '../types'
import { api } from '../api'

interface Props {
  combinedRisk: CombinedRiskResult | null
  selectedTool: string
  outageHours: number | undefined
}

type ContextType = 'BOTTLENECK' | 'OUTAGE' | 'SUPPLY_RISK' | 'COMBINED'

const CONTEXT_LABELS: Record<ContextType, string> = {
  BOTTLENECK:   'Bottleneck Explanation',
  OUTAGE:       'Outage Decision Brief',
  SUPPLY_RISK:  'Supply Risk Summary',
  COMBINED:     'Combined Risk Executive Brief',
}

export function BobNarrationPanel({ combinedRisk, selectedTool, outageHours }: Props) {
  const [contextType, setContextType] = useState<ContextType>('COMBINED')
  const [narration, setNarration] = useState<string>('')
  const [isFallback, setIsFallback] = useState(false)
  const [modelUsed, setModelUsed] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const buildContextData = (): Record<string, unknown> => {
    if (!combinedRisk) return { tool_id: selectedTool }
    switch (contextType) {
      case 'BOTTLENECK':
        return {
          tools: [{
            tool_id: combinedRisk.tool_id,
            tool_name: combinedRisk.tool_name,
            process_step: combinedRisk.process_step,
            utilization_pct: Math.round(combinedRisk.manufacturing_risk_score * 100),
            wip_lots: 0,
            bottleneck_score: combinedRisk.manufacturing_risk_score,
            is_critical: combinedRisk.risk_tier === 'CRITICAL' || combinedRisk.risk_tier === 'RED',
          }],
        }
      case 'OUTAGE':
        return {
          ...(combinedRisk.outage_simulation ?? {}),
          tool_id: combinedRisk.tool_id,
          process_step: combinedRisk.process_step,
        }
      case 'SUPPLY_RISK':
        return {
          ...(combinedRisk.supply_risk ?? {}),
          material_id: combinedRisk.primary_material_id,
        }
      case 'COMBINED':
      default:
        return {
          tool_id: combinedRisk.tool_id,
          process_step: combinedRisk.process_step,
          manufacturing_risk_score: combinedRisk.manufacturing_risk_score,
          supply_chain_risk_score: combinedRisk.supply_chain_risk_score,
          combined_risk_score: combinedRisk.combined_risk_score,
          risk_tier: combinedRisk.risk_tier,
          risk_tier_label: combinedRisk.risk_tier_label,
          confidence_pct: combinedRisk.confidence_pct,
          recommendations: combinedRisk.recommendations,
        }
    }
  }

  const handleAsk = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = buildContextData()
      const result = await api.narration.explain(contextType, data)
      setNarration(result.narration_text)
      setIsFallback(result.is_fallback)
      setModelUsed(result.model_used)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  // Auto-refresh narration when combined risk changes
  useEffect(() => {
    if (combinedRisk) {
      handleAsk()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [combinedRisk?.tool_id, combinedRisk?.combined_risk_score, contextType])

  return (
    <div className="bg-panel border border-border rounded-lg p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
          <h2 className="text-purple-400 text-xs font-semibold uppercase tracking-widest">
            IBM Bob — AI Narration Layer
          </h2>
          {isFallback && (
            <span className="text-xs border border-yellow-700/60 bg-yellow-900/20 text-yellow-400 rounded px-1.5 py-0.5">
              TEMPLATE FALLBACK
            </span>
          )}
          {!isFallback && modelUsed && (
            <span className="text-xs border border-purple-700/60 bg-purple-900/20 text-purple-400 rounded px-1.5 py-0.5">
              {modelUsed}
            </span>
          )}
        </div>

        {/* Context selector */}
        <div className="flex gap-1">
          {(Object.keys(CONTEXT_LABELS) as ContextType[]).map(ct => (
            <button
              key={ct}
              onClick={() => setContextType(ct)}
              className={`text-xs px-2 py-1 rounded border transition-colors font-mono
                ${ct === contextType
                  ? 'border-purple-500 bg-purple-900/30 text-purple-300'
                  : 'border-border text-muted hover:border-gray-500 hover:text-gray-300'
                }`}
            >
              {ct === 'BOTTLENECK' ? 'BTLNK' :
               ct === 'OUTAGE'     ? 'OUTAGE' :
               ct === 'SUPPLY_RISK'? 'SUPPLY' : 'COMBINED'}
            </button>
          ))}
          <button
            onClick={handleAsk}
            disabled={loading}
            className="text-xs px-3 py-1 rounded border border-purple-500 bg-purple-900/30 text-purple-300
                       hover:bg-purple-900/50 disabled:opacity-40 disabled:cursor-not-allowed font-mono ml-1"
          >
            {loading ? '…' : '↺ ASK BOB'}
          </button>
        </div>
      </div>

      {/* Context label */}
      <div className="text-xs text-muted">
        Context: <span className="text-gray-300">{CONTEXT_LABELS[contextType]}</span>
        {' · '}Tool: <span className="font-mono text-gray-300">{selectedTool}</span>
      </div>

      {/* Narration output */}
      {error && (
        <div className="text-xs text-red-400 border border-red-700/60 bg-red-900/20 rounded p-2">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-start gap-2 p-3 bg-surface rounded border border-border">
          <div className="w-1 h-1 rounded-full bg-purple-400 animate-bounce mt-2" />
          <div className="w-1 h-1 rounded-full bg-purple-400 animate-bounce mt-2 delay-75" />
          <div className="w-1 h-1 rounded-full bg-purple-400 animate-bounce mt-2 delay-150" />
          <span className="text-muted text-xs ml-1">Bob is analysing…</span>
        </div>
      ) : narration ? (
        <div className="bg-surface rounded border border-border p-4 text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
          {narration}
        </div>
      ) : (
        <div className="text-center text-muted text-xs py-4 border border-dashed border-border rounded">
          Select a context type and click ↺ ASK BOB
        </div>
      )}

      {/* Attribution */}
      <div className="text-xs text-muted border-t border-border pt-2 flex justify-between">
        <span>
          {isFallback
            ? '⚠ Bob unavailable — deterministic template narration active. Application fully functional.'
            : '✓ Powered by IBM Bob (watsonx.ai Granite)'
          }
        </span>
        <span className="font-mono">
          {combinedRisk?.tool_id} · Score {combinedRisk?.combined_risk_score.toFixed(3)}
        </span>
      </div>
    </div>
  )
}
