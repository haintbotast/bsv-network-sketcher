import type { AreaStyle } from '../models/api'
import type { LayoutTuning, RenderTuning } from '../services/adminConfig'

export const UNIT_PX = 120
export const GRID_FALLBACK_X = 4
export const GRID_FALLBACK_Y = 2.5

export const DEFAULT_LAYOUT_TUNING: LayoutTuning = {
  layer_gap: 1.5,
  node_spacing: 0.8,
  port_label_band: 0.2,
  area_gap: 1.1,
  area_padding: 0.35,
  label_band: 0.5,
  max_row_width_base: 12.0,
  max_nodes_per_row: 8,
  row_gap: 0.5,
  row_stagger: 0.5
}

export const DEFAULT_RENDER_TUNING: RenderTuning = {
  port_edge_inset: 6,
  port_label_offset: 12,
  bundle_gap: 18,
  bundle_stub: 18,
  area_clearance: 18,
  area_anchor_offset: 18,
  label_gap_x: 8,
  label_gap_y: 6,
  corridor_gap: 40
}

export const deviceTypes = ['Router', 'Switch', 'Firewall', 'Server', 'AP', 'PC', 'Storage', 'Unknown']
export const linkPurposes = ['DEFAULT', 'WAN', 'INTERNET', 'DMZ', 'LAN', 'MGMT', 'HA', 'STORAGE', 'BACKUP', 'VPN']

export const defaultAreaStyle: AreaStyle = {
  fill_color_rgb: [240, 240, 240],
  stroke_color_rgb: [51, 51, 51],
  stroke_width: 1
}

export function rgbToHex(rgb: number[]) {
  return `#${rgb.map(c => c.toString(16).padStart(2, '0')).join('')}`
}
