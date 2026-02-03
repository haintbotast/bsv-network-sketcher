export type UserRecord = {
  id: string
  email: string
  display_name?: string | null
  is_active?: boolean
  is_admin?: boolean
}

export type ProjectStats = {
  area_count?: number
  device_count?: number
  link_count?: number
}

export type ProjectRecord = {
  id: string
  name: string
  description?: string | null
  layout_mode: 'cisco' | 'iso' | 'custom'
  stats?: ProjectStats | null
}

export type AreaStyle = {
  fill_color_rgb: [number, number, number]
  stroke_color_rgb: [number, number, number]
  stroke_width: number
}

export type AreaRecord = {
  id: string
  project_id: string
  name: string
  grid_row: number
  grid_col: number
  position_x?: number | null
  position_y?: number | null
  width: number
  height: number
  style?: AreaStyle | null
}

export type DeviceRecord = {
  id: string
  project_id: string
  name: string
  area_id: string
  area_name?: string | null
  device_type: string
  position_x?: number | null
  position_y?: number | null
  width: number
  height: number
  color_rgb?: [number, number, number] | null
}

export type LinkRecord = {
  id: string
  project_id: string
  from_device_id: string
  from_device_name?: string | null
  from_port: string
  to_device_id: string
  to_device_name?: string | null
  to_port: string
  purpose?: string | null
  line_style?: 'solid' | 'dashed' | 'dotted' | null
  color_rgb?: [number, number, number] | null
}

export type PortAnchorOverrideRecord = {
  id: string
  project_id: string
  device_id: string
  port_name: string
  side: 'left' | 'right' | 'top' | 'bottom'
  offset_ratio: number
}

export type TokenResponse = {
  access_token: string
  refresh_token?: string | null
  token_type: string
  expires_in: number
}
