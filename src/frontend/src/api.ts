/**
 * API service layer — typed wrappers around all backend endpoints.
 * Base URL comes from VITE_API_BASE_URL env var, defaulting to /api/v1 (proxied).
 *
 * Backend URL layout:
 *   /api/v1/bottleneck/tools
 *   /api/v1/bottleneck/processes
 *   /api/v1/bottleneck/wip
 *   /api/v1/bottleneck/bottlenecks
 *   /api/v1/bottleneck/bottlenecks/{tool_id}
 *   /api/v1/supply/hhi
 *   /api/v1/supply/spof
 *   /api/v1/supply/inventory
 *   /api/v1/supply/geopolitical
 *   /api/v1/supply/material/{material_id}
 *   /api/v1/impact/{tool_id}?outage_hours=N
 *   /api/v1/narration/  (POST)
 */

import type {
  BottleneckListResponse,
  BottleneckAssessment,
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

// ── Bottleneck (new module, score 0–100) ──────────────────────────────────────
export const api = {
  bottleneck: {
    // Returns { bottlenecks: BottleneckAssessment[], count, critical_count, most_critical_tool_id }
    getAll: () => get<BottleneckListResponse>('/bottleneck/bottlenecks'),
    // Returns full BottleneckAssessment including history[]
    getTool: (toolId: string) => get<BottleneckAssessment>(`/bottleneck/bottlenecks/${encodeURIComponent(toolId)}`),
    getTools: () => get<{ tools: BottleneckAssessment[]; count: number }>('/bottleneck/tools'),
    getProcesses: () => get<{ processes: Array<{ process_id: number; process_name: string; process_sequence: number; next_process_id: number | null }>; count: number }>('/bottleneck/processes'),
    getWip: () => get<{ lots: Array<Record<string, unknown>>; count: number; total_wafers: number }>('/bottleneck/wip'),
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
    // GET /api/v1/impact/{tool_id}?outage_hours=N
    getCombined: (toolId: string, outageHours?: number) => {
      const url = outageHours
        ? `/impact/${encodeURIComponent(toolId)}?outage_hours=${outageHours}`
        : `/impact/${encodeURIComponent(toolId)}`
      return get<CombinedRiskResult>(url)
    },
  },

  narration: {
    explain: (contextType: string, contextData: Record<string, unknown>) =>
      post<NarrationResponse>('/narration/', { context_type: contextType, context_data: contextData }),
  },
}
