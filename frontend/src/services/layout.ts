/**
 * Auto-Layout Service
 */

import { apiRequest } from './api'

export interface AutoLayoutOptions {
  layer_gap?: number
  node_spacing?: number
  apply_to_db?: boolean
  group_by_area?: boolean
  layout_scope?: 'area' | 'project'
  anchor_routing?: boolean
  overview_mode?: 'l1-only'
  view_mode?: 'L1' | 'L2' | 'L3'
  normalize_topology?: boolean
  auto_resize_devices?: boolean
  preserve_existing_positions?: boolean
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

export interface VlanGroupLayout {
  vlan_id: number
  name: string
  x: number
  y: number
  width: number
  height: number
  device_ids: string[]
}

export interface SubnetGroupLayout {
  subnet: string
  name: string
  x: number
  y: number
  width: number
  height: number
  device_ids: string[]
  router_id?: string | null
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
  vlan_groups?: null | VlanGroupLayout[]
  subnet_groups?: null | SubnetGroupLayout[]
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
    layer_gap: 2.0,
    node_spacing: 0.5,
    apply_to_db: false,
    group_by_area: true,
    layout_scope: 'project',
    anchor_routing: true,
    overview_mode: 'l1-only',
    view_mode: 'L1',
    normalize_topology: false,
    auto_resize_devices: true,
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
