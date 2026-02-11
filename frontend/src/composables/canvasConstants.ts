import type { AreaStyle } from '../models/api'
import type { LayoutTuning, RenderTuning } from '../services/adminConfig'

export const UNIT_PX = 120
export const GRID_FALLBACK_X = 4
export const GRID_FALLBACK_Y = 2.5
export const POSITION_STANDARD_STEP_UNITS = 0.25
export const POSITION_STANDARD_DECIMALS = 2

// Layout tuning: khoảng cách và padding (đơn vị: inch)
export const DEFAULT_LAYOUT_TUNING: LayoutTuning = {
  layer_gap: 1.25,        // Khoảng cách giữa các tầng
  node_spacing: 1.1,      // Khoảng cách ngang giữa các device
  port_label_band: 0.0,   // Không cần thêm — port labels nằm trong band cells
  area_gap: 0.9,          // Khoảng cách giữa các area
  area_padding: 0.3,      // Padding bên trong area
  label_band: 0.35,       // Dải cho area label
  max_row_width_base: 12.0,
  max_nodes_per_row: 8,
  row_gap: 0.9,           // Khoảng cách giữa các hàng trong area
  row_stagger: 0.5        // Độ so le hàng (0-1)
}

// Render tuning: vẽ links và labels (đơn vị: px)
export const DEFAULT_RENDER_TUNING: RenderTuning = {
  port_edge_inset: 6,       // Khoảng cách port từ cạnh device
  port_label_offset: 18,    // Offset port label từ anchor
  bundle_gap: 34,           // Khoảng cách giữa các link trong bundle
  bundle_stub: 42,          // Độ dài stub khi tách bundle
  area_clearance: 36,       // Khoảng cách tránh cạnh area
  area_anchor_offset: 26,   // Offset điểm neo từ cạnh area
  label_gap_x: 8,           // Gap label theo chiều ngang
  label_gap_y: 6,           // Gap label theo chiều dọc
  corridor_gap: 64,         // Khoảng cách corridor bên ngoài bounds
  inter_area_links_per_channel: 4, // Số link tối đa trước khi tách thêm corridor channel
  inter_area_max_channels: 4,      // Số channel corridor liên-area tối đa mỗi cặp area
  inter_area_occupancy_weight: 1.0, // Trọng số tránh đường đã đông khi chọn channel
  icon_scale: 1.15,         // Hệ số phóng icon device
  icon_stroke_width: 1.5,   // Độ dày nét icon
  icon_min_size: 18,        // Kích thước icon tối thiểu
  icon_max_size: 32,        // Kích thước icon tối đa
  icon_color_default: '#4f4a44',
  icon_colors: {}           // Override theo loại icon, vd {"router":"#1f6feb"}
}

export const deviceTypes = [
  'Router',
  'Switch',
  'Firewall',
  'Server',
  'AP',
  'PC',
  'Storage',
  'Cloud',
  'Cloud-Network',
  'Cloud-Security',
  'Cloud-Service',
  'Unknown'
]
export const linkPurposes = ['DEFAULT', 'WAN', 'INTERNET', 'DMZ', 'LAN', 'MGMT', 'HA', 'HSRP', 'STACK', 'STORAGE', 'BACKUP', 'VPN']
export const DEFAULT_LINK_COLOR = '#2b2a28'
export const LINK_PURPOSE_COLORS: Record<string, string> = {
  DEFAULT: DEFAULT_LINK_COLOR,
  INTERNET: '#e74c3c',
  WAN: '#e67e22',
  DMZ: '#f1c40f',
  LAN: '#27ae60',
  MGMT: '#2980b9',
  HA: '#16a085',
  HSRP: '#9b59b6',
  STACK: '#2d8cf0',
  STACKWISE: '#2d8cf0',
  'STACK-WISE': '#2d8cf0',
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

export function snapUnitsToStandard(value: number, step = POSITION_STANDARD_STEP_UNITS) {
  if (!Number.isFinite(value) || !Number.isFinite(step) || step <= 0) return value
  const snapped = Math.round(value / step) * step
  return Number(snapped.toFixed(POSITION_STANDARD_DECIMALS))
}
