/**
 * Auto-Layout Service
 */

import { apiRequest } from './api'

export interface AutoLayoutOptions {
  algorithm?: string
  direction?: 'horizontal' | 'vertical'
  layer_gap?: number
  node_spacing?: number
  crossing_iterations?: number
  apply_to_db?: boolean
  group_by_area?: boolean
  layout_scope?: 'area' | 'project'
  anchor_routing?: boolean
  overview_mode?: 'l1-only'
}

export interface DeviceLayout {
  id: string
  area_id?: string | null
  x: number
  y: number
  layer: number
}

export interface AreaLayout {
  id: string
  name?: string
  x: number
  y: number
  width: number
  height: number
}

export interface LayoutStats {
  total_layers: number
  total_crossings: number
  execution_time_ms: number
  algorithm: string
}

export interface LayoutResult {
  devices: DeviceLayout[]
  areas: null | AreaLayout[]
  stats: LayoutStats
}

/**
 * Compute auto-layout for project.
 *
 * @param projectId - Project ID
 * @param options - Layout options
 * @returns Layout result with device coordinates and stats
 */
export async function autoLayout(
  projectId: string,
  options: AutoLayoutOptions = {}
): Promise<LayoutResult> {
  const defaultOptions: AutoLayoutOptions = {
    algorithm: 'sugiyama',
    direction: 'horizontal',
    layer_gap: 2.0,
    node_spacing: 0.5,
    crossing_iterations: 24,
    apply_to_db: false,
    group_by_area: true,
    layout_scope: 'project',
    anchor_routing: true,
    overview_mode: 'l1-only',
    ...options
  }

  return apiRequest<LayoutResult>(
    `/api/v1/projects/${projectId}/auto-layout`,
    {
      method: 'POST',
      body: JSON.stringify(defaultOptions)
    }
  )
}

/**
 * Invalidate layout cache for project.
 * Use after topology changes (add/remove devices or links).
 *
 * @param projectId - Project ID
 */
export async function invalidateLayoutCache(projectId: string): Promise<void> {
  await apiRequest(
    `/api/v1/projects/${projectId}/invalidate-layout-cache`,
    { method: 'POST' }
  )
}
