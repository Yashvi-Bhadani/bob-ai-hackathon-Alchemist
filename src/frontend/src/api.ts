/**
 * API service layer — typed wrappers around all backend endpoints.
 * Base URL comes from VITE_API_BASE_URL env var, defaulting to /api/v1 (proxied).
 */

import type {
  BottleneckListResponse,
  BottleneckResult,
  OutageSimulationResult,
  HHIResult,
  SPOFResult,
  InventoryCoverageResult,
  GeopoliticalRiskItem,
  MaterialSupplyRisk,
  CombinedRiskResult,
  NarrationResponse,
} from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${path} → ${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API POST ${path} → ${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

// ── Bottleneck ─────────────────────────────────────────────────────────────────
export const api = {
  bottleneck: {
    getAll: () => get<BottleneckListResponse>('/bottleneck/'),
    getTool: (toolId: string) => get<BottleneckResult>(`/bottleneck/${toolId}`),
    simulateOutage: (toolId: string, outageHours: number) =>
      get<OutageSimulationResult>(
        `/bottleneck/simulate-outage?tool_id=${encodeURIComponent(toolId)}&outage_hours=${outageHours}`
      ),
  },

  supply: {
    getHHI: () => get<HHIResult[]>('/supply/hhi'),
    getSPOF: () => get<SPOFResult[]>('/supply/spof'),
    getInventory: () => get<InventoryCoverageResult[]>('/supply/inventory'),
    getGeopolitical: () => get<GeopoliticalRiskItem[]>('/supply/geopolitical'),
    getMaterialRisk: (materialId: string) =>
      get<MaterialSupplyRisk>(`/supply/material/${encodeURIComponent(materialId)}`),
  },

  impact: {
    getCombined: (toolId: string, outageHours?: number) => {
      const url = outageHours
        ? `/impact/${toolId}?outage_hours=${outageHours}`
        : `/impact/${toolId}`
      return get<CombinedRiskResult>(url)
    },
  },

  narration: {
    explain: (contextType: string, contextData: Record<string, unknown>) =>
      post<NarrationResponse>('/narration/', { context_type: contextType, context_data: contextData }),
  },
}
