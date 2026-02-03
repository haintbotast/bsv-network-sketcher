export type Point = {
  x: number
  y: number
}

export type Size = {
  width: number
  height: number
}

export type Viewport = {
  scale: number
  offsetX: number
  offsetY: number
}

export type AreaModel = {
  id: string
  name: string
  x: number
  y: number
  width: number
  height: number
  fill: string
  stroke: string
}

export type DeviceModel = {
  id: string
  areaId: string
  name: string
  x: number
  y: number
  width: number
  height: number
  type: string
}

export type LinkModel = {
  id: string
  fromDeviceId: string
  toDeviceId: string
  fromPort: string
  toPort: string
  style: 'solid' | 'dashed' | 'dotted'
}

export type PortAnchorOverride = {
  deviceId: string
  portName: string
  side: 'left' | 'right' | 'top' | 'bottom'
  offsetRatio: number | null
}

// View modes for canvas
export type ViewMode = 'L1' | 'L2' | 'L3'

// L2 Layer records
export type L2SegmentRecord = {
  id: string
  project_id: string
  name: string
  vlan_id: number
  description?: string | null
}

export type L2AssignmentRecord = {
  id: string
  project_id: string
  device_id: string
  device_name?: string | null
  interface_name: string
  l2_segment_id: string
  l2_segment_name?: string | null
  vlan_id?: number | null
  port_mode: 'access' | 'trunk'
  native_vlan?: number | null
  allowed_vlans?: number[] | null
}

// L3 Layer records
export type L3AddressRecord = {
  id: string
  project_id: string
  device_id: string
  device_name?: string | null
  interface_name: string
  ip_address: string
  prefix_length: number
  is_secondary: boolean
  description?: string | null
}
