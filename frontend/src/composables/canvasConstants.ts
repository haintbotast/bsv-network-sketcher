import type { AreaStyle } from '../models/api'
import type { LayoutTuning, RenderTuning } from '../services/adminConfig'

export const UNIT_PX = 120
export const GRID_FALLBACK_X = 4
export const GRID_FALLBACK_Y = 2.5

// Layout tuning: khoảng cách và padding (đơn vị: inch)
export const DEFAULT_LAYOUT_TUNING: LayoutTuning = {
  layer_gap: 1.8,         // Khoảng cách giữa các tầng (Core → Distribution → Access)
  node_spacing: 1.0,      // Khoảng cách ngang giữa các device
  port_label_band: 0.25,  // Dải dành cho port labels
  area_gap: 1.3,          // Khoảng cách giữa các area
  area_padding: 0.4,      // Padding bên trong area
  label_band: 0.5,        // Dải cho area label
  max_row_width_base: 12.0,
  max_nodes_per_row: 8,
  row_gap: 0.6,           // Khoảng cách giữa các hàng trong area
  row_stagger: 0.5        // Độ so le hàng (0-1)
}

// Render tuning: vẽ links và labels (đơn vị: px)
export const DEFAULT_RENDER_TUNING: RenderTuning = {
  port_edge_inset: 6,       // Khoảng cách port từ cạnh device
  port_label_offset: 14,    // Offset port label từ anchor
  bundle_gap: 28,           // Khoảng cách giữa các link trong bundle
  bundle_stub: 28,          // Độ dài stub khi tách bundle
  area_clearance: 30,       // Khoảng cách tránh cạnh area
  area_anchor_offset: 26,   // Offset điểm neo từ cạnh area
  label_gap_x: 8,           // Gap label theo chiều ngang
  label_gap_y: 6,           // Gap label theo chiều dọc
  corridor_gap: 56          // Khoảng cách corridor bên ngoài bounds
}

export const deviceTypes = ['Router', 'Switch', 'Firewall', 'Server', 'AP', 'PC', 'Storage', 'Unknown']
export const linkPurposes = ['DEFAULT', 'WAN', 'INTERNET', 'DMZ', 'LAN', 'MGMT', 'HA', 'STORAGE', 'BACKUP', 'VPN']
export const DEFAULT_LINK_COLOR = '#2b2a28'
export const LINK_PURPOSE_COLORS: Record<string, string> = {
  DEFAULT: DEFAULT_LINK_COLOR,
  INTERNET: '#e74c3c',
  WAN: '#e67e22',
  DMZ: '#f1c40f',
  LAN: '#27ae60',
  MGMT: '#2980b9',
  HA: '#16a085',
  STORAGE: '#1abc9c',
  BACKUP: '#7f8c8d',
  VPN: '#9b59b6',
  UPLINK: '#e67e22',
  'INTER-AREA': '#e67e22',
  'INTER_AREA': '#e67e22'
}

export function resolveLinkPurposeColor(purpose?: string | null) {
  if (!purpose) return DEFAULT_LINK_COLOR
  const key = purpose.toUpperCase()
  return LINK_PURPOSE_COLORS[key] || DEFAULT_LINK_COLOR
}

export const defaultAreaStyle: AreaStyle = {
  fill_color_rgb: [240, 240, 240],
  stroke_color_rgb: [51, 51, 51],
  stroke_width: 1
}

export function rgbToHex(rgb: number[]) {
  return `#${rgb.map(c => c.toString(16).padStart(2, '0')).join('')}`
}
