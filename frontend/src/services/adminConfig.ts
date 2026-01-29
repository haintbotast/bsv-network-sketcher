/**
 * Admin Config Service
 */

import { apiRequest } from './api'

export type LayoutTuning = {
  layer_gap?: number
  node_spacing?: number
  area_gap?: number
  area_padding?: number
  label_band?: number
  max_row_width_base?: number
}

export type RenderTuning = {
  port_edge_inset?: number
  port_label_offset?: number
  bundle_gap?: number
  bundle_stub?: number
  area_clearance?: number
  area_anchor_offset?: number
  label_gap_x?: number
  label_gap_y?: number
  corridor_gap?: number
}

export type AdminConfig = {
  layout_tuning?: LayoutTuning
  render_tuning?: RenderTuning
}

export async function getAdminConfig(): Promise<AdminConfig> {
  const response = await apiRequest<{ config: AdminConfig }>(`/api/v1/admin/config`)
  return response.config || {}
}

export async function updateAdminConfig(config: AdminConfig): Promise<AdminConfig> {
  const response = await apiRequest<{ config: AdminConfig }>(`/api/v1/admin/config`, {
    method: 'PUT',
    body: JSON.stringify({ config })
  })
  return response.config || config
}
