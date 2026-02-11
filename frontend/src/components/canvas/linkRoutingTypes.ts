import type { ComputedRef, Ref } from 'vue'
import type { AreaModel, DeviceModel, L2AssignmentRecord, LinkModel, ViewMode, Viewport } from '../../models/types'

export type Rect = { x: number; y: number; width: number; height: number }

export type RenderLink = {
  id: string
  fromAnchor: { x: number; y: number; side?: string }
  toAnchor: { x: number; y: number; side?: string }
  fromCenter: { x: number; y: number }
  toCenter: { x: number; y: number }
  points: number[]
  config: Record<string, unknown>
}

export type AnchorOverrideMap = Map<string, Map<string, { x: number; y: number; side: string }>>
export type PortAnchorOverride = { side: 'left' | 'right' | 'top' | 'bottom'; offsetRatio: number | null }
export type PortAnchorOverrideMap = Map<string, Map<string, PortAnchorOverride>>

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
  inter_area_links_per_channel?: number
  inter_area_max_channels?: number
  inter_area_occupancy_weight?: number
  icon_scale?: number
  icon_stroke_width?: number
  icon_min_size?: number
  icon_max_size?: number
  icon_color_default?: string
  icon_colors?: Record<string, string>
}

export type LinkMeta = {
  link: LinkModel
  fromView: Rect
  toView: Rect
  fromCenter: { x: number; y: number }
  toCenter: { x: number; y: number }
  fromAnchor: { x: number; y: number; side?: string }
  toAnchor: { x: number; y: number; side?: string }
  fromLabelWidth?: number
  toLabelWidth?: number
  fromAreaId: string | undefined
  toAreaId: string | undefined
  fromArea: Rect | null | undefined
  toArea: Rect | null | undefined
}

export type AreaRectEntry = { id: string; rect: Rect }
export type DeviceRectEntry = { id: string; rect: Rect }

export type UseLinkRoutingParams = {
  props: {
    links: LinkModel[]
    areas: AreaModel[]
    devices: DeviceModel[]
    viewMode?: ViewMode
    l2Assignments?: L2AssignmentRecord[]
    portAnchorOverrides?: PortAnchorOverrideMap
  }
  layoutViewport: Ref<Viewport>
  renderTuning: ComputedRef<RenderTuning>
  deviceViewMap: ComputedRef<Map<string, Rect>>
  areaViewMap: ComputedRef<Map<string, Rect>>
  deviceAreaMap: ComputedRef<Map<string, string>>
  areaBounds: ComputedRef<{ minX: number; minY: number; maxX: number; maxY: number } | null>
  isPanning: Ref<boolean>
}
