<template>
  <div ref="containerRef" class="canvas-shell">
    <v-stage
      ref="stageRef"
      :config="{
        width: stageSize.width,
        height: stageSize.height
      }"
      @mousedown="onPointerDown"
      @mousemove="onPointerMove"
      @mouseup="onPointerUp"
      @mouseleave="onPointerUp"
      @touchstart="onPointerDown"
      @touchmove="onPointerMove"
      @touchend="onPointerUp"
    >
      <v-layer ref="gridLayerRef" :config="layerTransform">
        <v-rect :config="gridConfig" />
      </v-layer>

      <!-- L1 View: Areas with minimized visuals -->
      <v-layer ref="areaLayerRef" :config="layerTransform">
        <v-group
          v-for="area in visibleAreas"
          :key="area.id"
          :config="area.group"
          @click="() => emitSelect(area.id, 'area')"
          @dragstart="event => onObjectDragStart(event, area.id, 'area')"
          @dragmove="event => onObjectDragMove(event, area.id, 'area')"
          @dragend="event => onObjectDragEnd(event, area.id, 'area')"
        >
          <v-rect :config="area.rect" />
        </v-group>
        <v-group v-for="group in visibleVlanGroups" :key="group.id">
          <v-rect :config="group.rect" />
          <v-text :config="group.label" />
        </v-group>
        <v-group v-for="group in visibleSubnetGroups" :key="group.id">
          <v-rect :config="group.rect" />
          <v-text :config="group.label" />
        </v-group>
      </v-layer>

      <v-layer ref="linkLayerRef" :config="layerTransform">
        <v-shape
          v-for="link in visibleLinkShapes"
          :key="link.id"
          :config="link.config"
        />
      </v-layer>

      <v-layer ref="deviceLayerRef" :config="layerTransform">
        <v-group
          v-for="device in visibleDevices"
          :key="device.id"
          :config="device.group"
          @click="() => emitSelect(device.id, 'device')"
          @dragstart="event => onObjectDragStart(event, device.id, 'device')"
          @dragmove="event => onObjectDragMove(event, device.id, 'device')"
          @dragend="event => onObjectDragEnd(event, device.id, 'device')"
        >
          <v-rect :config="device.bodyRect" />
          <v-shape v-if="device.iconShape" :config="device.iconShape" />
          <v-group
            v-for="port in device.topPorts"
            :key="port.id"
          >
            <v-rect :config="port.rect" />
            <v-text :config="port.text" />
          </v-group>
          <v-group
            v-for="port in device.bottomPorts"
            :key="port.id"
          >
            <v-rect :config="port.rect" />
            <v-text :config="port.text" />
          </v-group>
          <v-text :config="device.label" />
        </v-group>
        <v-group
          v-for="label in visibleAreaLabels"
          :key="label.id"
          :config="label.group"
          @click="() => emitSelect(label.id, 'area')"
        >
          <v-text :config="label.text" />
        </v-group>
      </v-layer>

      <!-- L2/L3 Overlay Layer -->
      <v-layer ref="overlayLayerRef" :config="layerTransform">
        <v-line
          v-for="guide in alignmentGuides"
          :key="guide.id"
          :config="guide.config"
        />
        <!-- L1 Port Labels -->
        <v-group
          v-for="label in visibleLinkPortLabels"
          :key="label.id"
          :config="label.group"
        >
          <v-rect :config="label.bg" />
          <v-text :config="label.text" />
        </v-group>
        <!-- L3 IP Labels (show in L3) -->
        <v-group
          v-for="label in l3Labels"
          :key="label.id"
          :config="label.group"
        >
          <v-rect :config="label.bg" />
          <v-text :config="label.text" />
        </v-group>
        <!-- L2 VLAN Labels (show in L2) -->
        <v-group
          v-for="label in l2Labels"
          :key="label.id"
          :config="label.group"
        >
          <v-rect :config="label.bg" />
          <v-text :config="label.text" />
        </v-group>
      </v-layer>
    </v-stage>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { AreaModel, DeviceModel, LinkModel, Viewport, ViewMode, L2AssignmentRecord, L3AddressRecord } from '../models/types'
import type { PortAnchorOverrideMap, Rect } from './canvas/linkRoutingTypes'
import { getVisibleBounds, logicalRectToView, logicalToView, viewToLogical } from '../utils/viewport'
import { useLinkRouting } from './canvas/useLinkRouting'
import { comparePorts } from './canvas/linkRoutingUtils'
import { buildDeviceTierMap, resolveAutoPortSide } from './canvas/portSidePolicy'
import { POSITION_STANDARD_STEP_UNITS, UNIT_PX } from '../composables/canvasConstants'

const props = defineProps<{
  areas: AreaModel[]
  devices: DeviceModel[]
  links: LinkModel[]
  viewport: Viewport
  positionEditEnabled?: boolean
  selectedId?: string | null
  viewMode?: ViewMode
  l2Assignments?: L2AssignmentRecord[]
  l3Addresses?: L3AddressRecord[]
  portAnchorOverrides?: PortAnchorOverrideMap
  devicePortsMap?: Map<string, Array<{ name: string; side: 'top' | 'bottom' | 'left' | 'right' }>>
  autoLayoutCoords?: Map<string, { x: number; y: number }> // Auto-layout coords (logical units/inches)
  renderTuning?: {
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
  vlanGroups?: Array<{
    vlan_id: number
    name: string
    x: number
    y: number
    width: number
    height: number
    device_ids: string[]
  }>
  subnetGroups?: Array<{
    subnet: string
    name: string
    x: number
    y: number
    width: number
    height: number
    device_ids: string[]
    router_id?: string | null
  }>
}>()

const emit = defineEmits<{
  (event: 'update:viewport', value: Viewport): void
  (event: 'select', payload: { id: string; type: 'device' | 'area' }): void
  (event: 'object:position-change', payload: { id: string; type: 'device' | 'area'; x: number; y: number }): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const stageRef = ref()
const stageSize = ref({ width: 300, height: 200 })
let observer: ResizeObserver | null = null
const isPanning = ref(false)
const isObjectDragging = ref(false)
const panStartPointer = ref<{ x: number; y: number } | null>(null)
const panBaseOffset = ref<{ x: number; y: number } | null>(null)
const panTranslation = ref({ x: 0, y: 0 })
const pendingTranslation = ref<{ x: number; y: number } | null>(null)
let panRaf = 0
const layoutViewport = ref<Viewport>({ ...props.viewport })

type DragObjectContext = {
  id: string
  type: 'device' | 'area'
  width: number
  height: number
  areaId: string | null
}

type AlignmentMatch = {
  axis: 'x' | 'y'
  delta: number
  lineCoord: number
}

const dragContext = ref<DragObjectContext | null>(null)
const activeGuideCoords = ref<{ x: number | null; y: number | null }>({ x: null, y: null })

const gridLayerRef = ref()
const areaLayerRef = ref()
const linkLayerRef = ref()
const deviceLayerRef = ref()
const overlayLayerRef = ref()

const gridConfig = computed(() => ({
  x: 16,
  y: 16,
  width: Math.max(stageSize.value.width - 32, 0),
  height: Math.max(stageSize.value.height - 32, 0),
  stroke: '#d0c6bc',
  strokeWidth: 1,
  dash: [8, 6],
  cornerRadius: 12,
  name: 'grid-bg'
}))

const visibleBounds = computed(() => getVisibleBounds(stageSize.value, layoutViewport.value))

const alignmentGuides = computed(() => {
  if (!props.positionEditEnabled || !isObjectDragging.value) return []
  const guides: Array<{ id: string; config: Record<string, any> }> = []
  const bounds = visibleBounds.value
  const x = activeGuideCoords.value.x
  const y = activeGuideCoords.value.y

  if (x != null) {
    guides.push({
      id: 'guide-x',
      config: {
        points: [x, bounds.top, x, bounds.bottom],
        stroke: GUIDE_STROKE,
        strokeWidth: 1,
        dash: [6, 4],
        opacity: 0.85,
        listening: false,
      },
    })
  }
  if (y != null) {
    guides.push({
      id: 'guide-y',
      config: {
        points: [bounds.left, y, bounds.right, y],
        stroke: GUIDE_STROKE,
        strokeWidth: 1,
        dash: [6, 4],
        opacity: 0.85,
        listening: false,
      },
    })
  }
  return guides
})

const AREA_PADDING = 12
const TEXT_PADDING = 10
const SUB_ZONES = new Set(['Department', 'Projects', 'IT'])
const LABEL_GAP_MAIN = 22
const LABEL_GAP_SUB = 18
const FONT_FAMILY = 'Calibri'
const AREA_DISPLAY_PAD_X = 24
const AREA_DISPLAY_PAD_Y = 18
const AREA_DISPLAY_LABEL_BAND = 22
const AREA_DISPLAY_MIN_WIDTH = 200
const AREA_DISPLAY_MIN_HEIGHT = 130
const DRAG_SNAP_THRESHOLD_PX = 10
const GUIDE_STROKE = '#d66c3b'
const POSITION_STANDARD_STEP_PX = POSITION_STANDARD_STEP_UNITS * UNIT_PX

const areaViewMap = computed(() => {
  const map = new Map<string, { x: number; y: number; width: number; height: number }>()
  props.areas.forEach(area => {
    const rect = logicalRectToView(area, layoutViewport.value)
    map.set(area.id, rect)
  })
  return map
})

const areaDisplayMap = computed(() => {
  const map = new Map<string, { x: number; y: number; width: number; height: number }>()
  const boundsByArea = new Map<string, { minX: number; minY: number; maxX: number; maxY: number }>()

  props.devices.forEach(device => {
    const areaId = device.areaId
    if (!areaId) return
    const autoCoords = props.autoLayoutCoords?.get(device.id)
    const source = autoCoords
      ? { ...device, x: autoCoords.x * 120, y: autoCoords.y * 120 }
      : device
    const rect = logicalRectToView(source, layoutViewport.value)
    const current = boundsByArea.get(areaId)
    if (!current) {
      boundsByArea.set(areaId, {
        minX: rect.x,
        minY: rect.y,
        maxX: rect.x + rect.width,
        maxY: rect.y + rect.height,
      })
      return
    }
    current.minX = Math.min(current.minX, rect.x)
    current.minY = Math.min(current.minY, rect.y)
    current.maxX = Math.max(current.maxX, rect.x + rect.width)
    current.maxY = Math.max(current.maxY, rect.y + rect.height)
  })

  const fitInBase = (base: { x: number; y: number; width: number; height: number }, target: { x: number; y: number; width: number; height: number }) => {
    const minW = Math.min(AREA_DISPLAY_MIN_WIDTH, base.width)
    const minH = Math.min(AREA_DISPLAY_MIN_HEIGHT, base.height)
    let x = target.x
    let y = target.y
    let width = Math.max(minW, target.width)
    let height = Math.max(minH, target.height)

    if (width > base.width) width = base.width
    if (height > base.height) height = base.height
    if (x < base.x) x = base.x
    if (y < base.y) y = base.y
    if (x + width > base.x + base.width) x = base.x + base.width - width
    if (y + height > base.y + base.height) y = base.y + base.height - height
    return { x, y, width, height }
  }

  props.areas.forEach(area => {
    const base = areaViewMap.value.get(area.id)
    if (!base) return
    if (area.name.endsWith('_wp_')) {
      map.set(area.id, base)
      return
    }
    const bounds = boundsByArea.get(area.id)
    if (!bounds) {
      map.set(area.id, base)
      return
    }
    const compact = fitInBase(base, {
      x: bounds.minX - AREA_DISPLAY_PAD_X,
      y: bounds.minY - AREA_DISPLAY_PAD_Y - AREA_DISPLAY_LABEL_BAND,
      width: (bounds.maxX - bounds.minX) + AREA_DISPLAY_PAD_X * 2,
      height: (bounds.maxY - bounds.minY) + AREA_DISPLAY_PAD_Y * 2 + AREA_DISPLAY_LABEL_BAND,
    })
    map.set(area.id, compact)
  })

  return map
})

const areaRenderMap = computed(() => {
  return props.positionEditEnabled ? areaViewMap.value : areaDisplayMap.value
})

const areaById = computed(() => {
  const map = new Map<string, AreaModel>()
  props.areas.forEach(area => map.set(area.id, area))
  return map
})

const headOfficeTopByLocation = computed(() => {
  const map = new Map<string, number>()
  props.areas.forEach(area => {
    const parts = area.name.split(' - ')
    if (parts.length < 2) return
    const location = parts[0]
    const zone = parts.slice(1).join(' - ')
    if (!SUB_ZONES.has(zone)) return
    const rect = areaViewMap.value.get(area.id)
    if (!rect) return
    const current = map.get(location)
    map.set(location, current === undefined ? rect.y : Math.min(current, rect.y))
  })
  return map
})

const childAreasByParent = computed(() => {
  const map = new Map<string, Array<{ id: string; rect: { x: number; y: number; width: number; height: number } }>>()
  const areaList = [...props.areas]

  areaList.forEach(area => {
    const rect = areaDisplayMap.value.get(area.id)
    if (!rect) return

    areaList.forEach(potentialParent => {
      if (potentialParent.id === area.id) return
      const parentRect = areaDisplayMap.value.get(potentialParent.id)
      if (!parentRect) return

      const isInside = rect.x >= parentRect.x &&
                       rect.y >= parentRect.y &&
                       rect.x + rect.width <= parentRect.x + parentRect.width &&
                       rect.y + rect.height <= parentRect.y + parentRect.height

      if (isInside) {
        const children = map.get(potentialParent.id) || []
        children.push({ id: area.id, rect })
        map.set(potentialParent.id, children)
      }
    })
  })

  return map
})

const visibleAreas = computed(() => {
  // Hide areas in L2/L3 views (they're replaced by VLAN/subnet groups)
  if (props.viewMode === 'L2' || props.viewMode === 'L3') {
    return []
  }

  const visible = props.areas
    .filter(area => areaRenderMap.value.has(area.id))
    .sort((a, b) => {
      const rectA = areaRenderMap.value.get(a.id)
      const rectB = areaRenderMap.value.get(b.id)
      if (!rectA || !rectB) return 0
      return rectB.width * rectB.height - rectA.width * rectA.height
    })
    .map(area => {
      const rect = areaRenderMap.value.get(area.id)!
      const parts = area.name.split(' - ')
      const zone = parts.slice(1).join(' - ')
      const children = childAreasByParent.value.get(area.id) || []
      const hasChildren = children.length > 0

      let labelY = 8
      let labelAlign: 'left' | 'right' = 'left'

      if (hasChildren) {
        const topLeftChild = children.reduce((closest, child) => {
          if (!closest) return child
          const closestDist = Math.sqrt(Math.pow(closest.rect.x - rect.x, 2) + Math.pow(closest.rect.y - rect.y, 2))
          const childDist = Math.sqrt(Math.pow(child.rect.x - rect.x, 2) + Math.pow(child.rect.y - rect.y, 2))
          return childDist < closestDist ? child : closest
        }, children[0])

        if (topLeftChild && topLeftChild.rect.x - rect.x < rect.width * 0.4) {
          labelAlign = 'right'
        }
      }

      const isWaypoint = area.name.endsWith('_wp_')
      const isSubZone = SUB_ZONES.has(zone)
      const fontSize = isWaypoint ? 0 : (isSubZone ? 12 : 14)

      // L1 view: areas fully visible with clear borders (NS gốc style)
      // Waypoint areas: nhỏ, mờ, viền nét đứt
      const areaOpacity = isWaypoint ? 0.25 : 1
      const areaFill = isWaypoint ? '#fbfbfb' : 'rgba(255,255,255,0)'

      const isSelected = props.selectedId === area.id
      return {
        id: area.id,
        group: {
          x: rect.x,
          y: rect.y,
          draggable: !!props.positionEditEnabled,
          clipX: 0,
          clipY: 0,
          clipWidth: rect.width,
          clipHeight: rect.height
        },
        rect: {
          x: 0,
          y: 0,
          width: rect.width,
          height: rect.height,
          fill: areaFill,
          opacity: areaOpacity,
          stroke: isWaypoint ? '#bdbdbd' : (isSelected ? '#d66c3b' : '#cdcdcd'),
          strokeWidth: isWaypoint ? 1 : (isSelected ? 2 : 1),
          dash: isWaypoint ? [4, 3] : [],
          cornerRadius: isWaypoint ? 2 : 4,
          shadowColor: 'transparent',
          shadowBlur: 0,
          shadowOffset: { x: 0, y: 0 },
          shadowOpacity: 0,
          shadowForStrokeEnabled: false
        },
        label: {
          x: labelAlign === 'right' ? rect.width - TEXT_PADDING : TEXT_PADDING,
          y: labelY,
          width: Math.max(rect.width - TEXT_PADDING * 2, 0),
          text: isWaypoint ? '' : area.name,
          fontSize,
          fontFamily: FONT_FAMILY,
          fill: '#3f3a33',
          opacity: 1.0,
          wrap: 'none',
          ellipsis: true,
          align: labelAlign
        }
      }
    })
  return visible
})

const visibleAreaLabels = computed(() => {
  if (!visibleAreas.value.length) return []
  return visibleAreas.value
    .filter(area => area.label.text)
    .map(area => ({
      id: area.id,
      group: { x: area.group.x, y: area.group.y },
      text: { ...area.label }
    }))
})

// VLAN Groups for L2 view
const visibleVlanGroups = computed(() => {
  if (props.viewMode !== 'L2' || !props.vlanGroups || props.vlanGroups.length === 0) {
    return []
  }

  return props.vlanGroups.map(group => {
    const logicalRect = {
      x: group.x,
      y: group.y,
      width: group.width,
      height: group.height
    }
    const viewRect = logicalRectToView(logicalRect, layoutViewport.value)

    return {
      id: `vlan-${group.vlan_id}`,
      vlan_id: group.vlan_id,
      rect: {
        x: viewRect.x,
        y: viewRect.y,
        width: viewRect.width,
        height: viewRect.height,
        fill: '#e3f2fd',
        opacity: 0.25,
        stroke: 'transparent',
        strokeWidth: 0,
        cornerRadius: 10,
        shadowColor: 'rgba(25, 118, 210, 0.35)',
        shadowBlur: 8,
        shadowOffset: { x: 0, y: 4 },
        shadowOpacity: 0.2,
        shadowForStrokeEnabled: false
      },
      label: {
        x: viewRect.x + 10,
        y: viewRect.y + 10,
        text: group.name,
        fontSize: 14,
        fontFamily: FONT_FAMILY,
        fill: '#1976d2',
        fontStyle: 'bold'
      }
    }
  })
})

// Subnet Groups for L3 view
const visibleSubnetGroups = computed(() => {
  if (props.viewMode !== 'L3' || !props.subnetGroups || props.subnetGroups.length === 0) {
    return []
  }

  return props.subnetGroups.map(group => {
    const logicalRect = {
      x: group.x,
      y: group.y,
      width: group.width,
      height: group.height
    }
    const viewRect = logicalRectToView(logicalRect, layoutViewport.value)

    return {
      id: `subnet-${group.subnet}`,
      subnet: group.subnet,
      rect: {
        x: viewRect.x,
        y: viewRect.y,
        width: viewRect.width,
        height: viewRect.height,
        fill: '#f3e5f5',
        opacity: 0.25,
        stroke: 'transparent',
        strokeWidth: 0,
        cornerRadius: 10,
        shadowColor: 'rgba(123, 31, 162, 0.35)',
        shadowBlur: 8,
        shadowOffset: { x: 0, y: 4 },
        shadowOpacity: 0.2,
        shadowForStrokeEnabled: false
      },
      label: {
        x: viewRect.x + 10,
        y: viewRect.y + 10,
        text: group.name,
        fontSize: 14,
        fontFamily: FONT_FAMILY,
        fill: '#7b1fa2',
        fontStyle: 'bold'
      }
    }
  })
})

const DEVICE_GAP = 12
const ROLE_ORDER_MAIN = ['router', 'firewall', 'core', 'dist', 'server', 'access', 'endpoint']
const ROLE_ORDER_SUB = ['access', 'server', 'endpoint']
const DEVICE_PORT_CELL_MIN_WIDTH = 30
const DEVICE_PORT_CELL_HEIGHT = 18
const DEVICE_PORT_CELL_GAP = 2
const DEVICE_PORT_BAND_PADDING_X = 6
const DEVICE_PORT_BAND_PADDING_Y = 4
const DEVICE_PORT_FONT_SIZE = 10
const DEVICE_LABEL_FONT_SIZE = 13
const DEVICE_LABEL_MIN_HEIGHT = 24
const DEVICE_STANDARD_TOTAL_HEIGHT = 76
const DEVICE_BODY_VERTICAL_PADDING = 6
const DEVICE_MIN_WIDTH = 96
const DEVICE_ICON_STROKE_WIDTH = 1
const DEVICE_ICON_MIN_SIZE = 14
const DEVICE_ICON_MAX_SIZE = 24
const DEVICE_ICON_MARGIN_LEFT = 10
const DEVICE_ICON_LABEL_GAP = 10
const DEVICE_ICON_COLOR = '#4f4a44'

type DeviceIconKind = 'router' | 'switch' | 'firewall' | 'server' | 'storage' | 'ap' | 'endpoint' | 'cloud' | 'unknown'

const CLOUD_ICON_KEYWORDS = ['CLOUD', 'INTERNET', 'SAAS', 'PAAS', 'IAAS', 'O365', 'OFFICE365']

function clampNumber(value: number, min: number, max: number) {
  if (value < min) return min
  if (value > max) return max
  return value
}

function resolveDeviceRole(device: DeviceModel) {
  const name = device.name.toUpperCase()
  if (device.type === 'Router' || name.includes('RTR') || name.includes('ROUTER') || name.includes('ISP')) {
    return 'router'
  }
  if (device.type === 'Firewall' || name.includes('FW') || name.includes('FIREWALL')) {
    return 'firewall'
  }
  if (name.includes('CORE')) {
    return 'core'
  }
  if (name.includes('DIST')) {
    return 'dist'
  }
  if (device.type === 'Server' || name.includes('SRV') || name.includes('SERVER')) {
    return 'server'
  }
  if (device.type === 'Switch' && (name.includes('SRV') || name.includes('SERVER') || name.includes('STORAGE') || name.includes('NAS') || name.includes('SAN'))) {
    return 'server'
  }
  if (name.includes('ACC') || name.includes('ACCESS')) {
    return 'access'
  }
  return 'endpoint'
}

function resolveDeviceIconKind(device: DeviceModel): DeviceIconKind {
  const name = (device.name || '').toUpperCase()
  if (CLOUD_ICON_KEYWORDS.some(keyword => name.includes(keyword))) return 'cloud'
  if (device.type === 'Storage') return 'storage'
  if (device.type === 'AP') return 'ap'
  if (device.type === 'PC') return 'endpoint'
  const role = resolveDeviceRole(device)
  if (role === 'router') return 'router'
  if (role === 'firewall') return 'firewall'
  if (role === 'server') return 'server'
  if (role === 'endpoint') {
    if (name.includes('AP') || name.includes('ACCESS POINT')) return 'ap'
    if (name.includes('NAS') || name.includes('SAN') || name.includes('STORAGE')) return 'storage'
    return 'endpoint'
  }
  if (role === 'access' || role === 'core' || role === 'dist') return 'switch'
  return 'unknown'
}

type DevicePortBands = {
  top: string[]
  bottom: string[]
}

type DevicePortCell = {
  id: string
  rect: {
    x: number
    y: number
    width: number
    height: number
    fill: string
    stroke: string
    strokeWidth: number
    cornerRadius: number
    opacity: number
  }
  text: {
    x: number
    y: number
    width: number
    height: number
    text: string
    fontSize: number
    fill: string
    align: 'center'
    verticalAlign: 'middle'
  }
}

type DeviceRenderFrame = {
  topBandHeight: number
  bottomBandHeight: number
  bodyHeight: number
}

type DeviceIconFrame = {
  x: number
  y: number
  size: number
}

const DEVICE_PORT_BAND_HEIGHT = DEVICE_PORT_CELL_HEIGHT + DEVICE_PORT_BAND_PADDING_Y * 2

function buildDeviceIconFrame(bodyY: number, bodyHeight: number, bodyWidth: number): DeviceIconFrame | null {
  if (bodyHeight <= 10 || bodyWidth <= DEVICE_ICON_MARGIN_LEFT + DEVICE_ICON_MIN_SIZE + 14) return null
  const rawSize = Math.min(bodyHeight - 4, bodyWidth * 0.22, DEVICE_ICON_MAX_SIZE)
  const size = clampNumber(rawSize, DEVICE_ICON_MIN_SIZE, DEVICE_ICON_MAX_SIZE)
  return {
    x: DEVICE_ICON_MARGIN_LEFT,
    y: bodyY + (bodyHeight - size) / 2,
    size,
  }
}

function buildDeviceIconShape(
  kind: DeviceIconKind,
  frame: DeviceIconFrame | null,
  isSelected: boolean
) {
  if (!frame) return null
  const { x, y, size } = frame
  const cx = x + size / 2
  const cy = y + size / 2
  const stroke = isSelected ? '#d66c3b' : DEVICE_ICON_COLOR
  const dash = kind === 'unknown' ? [2, 2] : []

  return {
    x: 0,
    y: 0,
    stroke,
    strokeWidth: DEVICE_ICON_STROKE_WIDTH,
    lineCap: 'round',
    lineJoin: 'round',
    dash,
    listening: false,
    sceneFunc: (ctx: CanvasRenderingContext2D, shape: any) => {
      ctx.beginPath()

      if (kind === 'router') {
        const r = size * 0.42
        for (let i = 0; i < 6; i += 1) {
          const angle = Math.PI / 6 + (i * Math.PI) / 3
          const px = cx + r * Math.cos(angle)
          const py = cy + r * Math.sin(angle)
          if (i === 0) ctx.moveTo(px, py)
          else ctx.lineTo(px, py)
        }
        ctx.closePath()
        ctx.moveTo(cx - r * 0.55, cy)
        ctx.lineTo(cx + r * 0.55, cy)
        ctx.moveTo(cx, cy - r * 0.55)
        ctx.lineTo(cx, cy + r * 0.55)
      } else if (kind === 'switch') {
        const left = x + size * 0.08
        const top = y + size * 0.3
        const width = size * 0.84
        const height = size * 0.46
        ctx.rect(left, top, width, height)
        const slotW = size * 0.1
        const slotH = size * 0.08
        const colGap = size * 0.04
        const rowGap = size * 0.07
        const row1Y = top + size * 0.07
        const row2Y = row1Y + slotH + rowGap
        const startX = left + size * 0.08
        for (let row = 0; row < 2; row += 1) {
          for (let col = 0; col < 3; col += 1) {
            const sx = startX + col * (slotW + colGap)
            const sy = row === 0 ? row1Y : row2Y
            ctx.rect(sx, sy, slotW, slotH)
          }
        }
        ctx.moveTo(left + size * 0.1, top - size * 0.08)
        ctx.lineTo(left + width - size * 0.1, top - size * 0.08)
      } else if (kind === 'firewall') {
        const left = x + size * 0.14
        const top = y + size * 0.18
        const width = size * 0.72
        const height = size * 0.64
        ctx.rect(left, top, width, height)
        ctx.moveTo(left, top + height / 3)
        ctx.lineTo(left + width, top + height / 3)
        ctx.moveTo(left, top + (height * 2) / 3)
        ctx.lineTo(left + width, top + (height * 2) / 3)
        ctx.moveTo(left + width * 0.3, top)
        ctx.lineTo(left + width * 0.3, top + height / 3)
        ctx.moveTo(left + width * 0.7, top + height / 3)
        ctx.lineTo(left + width * 0.7, top + (height * 2) / 3)
        ctx.moveTo(left + width * 0.3, top + (height * 2) / 3)
        ctx.lineTo(left + width * 0.3, top + height)
      } else if (kind === 'server') {
        const left = x + size * 0.24
        const top = y + size * 0.1
        const width = size * 0.52
        const height = size * 0.8
        ctx.rect(left, top, width, height)
        const bay1Y = top + height * 0.28
        const bay2Y = top + height * 0.56
        ctx.moveTo(left, bay1Y)
        ctx.lineTo(left + width, bay1Y)
        ctx.moveTo(left, bay2Y)
        ctx.lineTo(left + width, bay2Y)
        const ledR = size * 0.03
        const ledX = left + width * 0.2
        const ledYs = [top + height * 0.14, top + height * 0.42, top + height * 0.7]
        ledYs.forEach(ledY => {
          ctx.moveTo(ledX + ledR, ledY)
          ctx.arc(ledX, ledY, ledR, 0, Math.PI * 2)
        })
      } else if (kind === 'storage') {
        const rx = size * 0.28
        const ry = size * 0.12
        const topY = y + size * 0.22
        const bottomY = y + size * 0.78
        ctx.moveTo(cx - rx, topY)
        ctx.ellipse(cx, topY, rx, ry, 0, 0, Math.PI * 2)
        ctx.moveTo(cx - rx, topY)
        ctx.lineTo(cx - rx, bottomY)
        ctx.moveTo(cx + rx, topY)
        ctx.lineTo(cx + rx, bottomY)
        ctx.moveTo(cx - rx, bottomY)
        ctx.ellipse(cx, bottomY, rx, ry, 0, 0, Math.PI)
      } else if (kind === 'ap') {
        const r0 = size * 0.06
        ctx.moveTo(cx + r0, cy + size * 0.14)
        ctx.arc(cx, cy + size * 0.14, r0, 0, Math.PI * 2)
        const arcs = [size * 0.16, size * 0.28]
        arcs.forEach(r => {
          ctx.moveTo(cx - r * 0.72, cy + size * 0.14)
          ctx.arc(cx, cy + size * 0.14, r, Math.PI * 1.18, Math.PI * 1.82)
        })
      } else if (kind === 'cloud') {
        const left = x + size * 0.1
        const right = x + size * 0.9
        const bottom = y + size * 0.78
        ctx.moveTo(left, bottom)
        ctx.bezierCurveTo(x + size * 0.05, y + size * 0.62, x + size * 0.18, y + size * 0.5, x + size * 0.3, y + size * 0.53)
        ctx.bezierCurveTo(x + size * 0.34, y + size * 0.34, x + size * 0.5, y + size * 0.3, x + size * 0.6, y + size * 0.44)
        ctx.bezierCurveTo(x + size * 0.7, y + size * 0.36, x + size * 0.86, y + size * 0.44, right, y + size * 0.58)
        ctx.bezierCurveTo(right, y + size * 0.7, x + size * 0.8, bottom, x + size * 0.66, bottom)
        ctx.lineTo(x + size * 0.3, bottom)
        ctx.bezierCurveTo(x + size * 0.18, bottom, x + size * 0.1, y + size * 0.86, left, bottom)
      } else if (kind === 'endpoint') {
        const left = x + size * 0.08
        const top = y + size * 0.16
        const width = size * 0.62
        const height = size * 0.42
        const screenCx = left + width / 2
        ctx.rect(left, top, width, height)
        ctx.moveTo(screenCx, top + height)
        ctx.lineTo(screenCx, y + size * 0.82)
        ctx.moveTo(screenCx - size * 0.2, y + size * 0.82)
        ctx.lineTo(screenCx + size * 0.14, y + size * 0.82)
        const towerX = x + size * 0.76
        const towerY = y + size * 0.24
        const towerW = size * 0.14
        const towerH = size * 0.48
        ctx.rect(towerX, towerY, towerW, towerH)
        const btnR = size * 0.02
        ctx.moveTo(towerX + towerW * 0.5 + btnR, towerY + towerH * 0.18)
        ctx.arc(towerX + towerW * 0.5, towerY + towerH * 0.18, btnR, 0, Math.PI * 2)
      } else {
        const left = x + size * 0.14
        const top = y + size * 0.14
        const width = size * 0.72
        const height = size * 0.72
        ctx.rect(left, top, width, height)
        ctx.moveTo(cx - size * 0.1, cy - size * 0.08)
        ctx.quadraticCurveTo(cx, cy - size * 0.26, cx + size * 0.1, cy - size * 0.08)
        ctx.quadraticCurveTo(cx + size * 0.16, cy, cx, cy + size * 0.1)
        ctx.lineTo(cx, cy + size * 0.2)
        ctx.moveTo(cx + size * 0.01, cy + size * 0.3)
        ctx.arc(cx, cy + size * 0.3, size * 0.01, 0, Math.PI * 2)
      }

      ctx.strokeShape(shape)
    },
  }
}

const deviceTierMap = computed(() => buildDeviceTierMap(props.devices))

const normalizedOverrideSide = (side: 'left' | 'right' | 'top' | 'bottom') => {
  if (side === 'top') return 'top'
  if (side === 'bottom') return 'bottom'
  return 'bottom'
}

const devicePortBands = computed(() => {
  const map = new Map<string, DevicePortBands>()
  const addPort = (deviceId: string, port: string | null | undefined, side: 'top' | 'bottom') => {
    const normalizedPort = (port || '').trim()
    if (!deviceId || !normalizedPort) return
    const entry = map.get(deviceId) || { top: [], bottom: [] }
    const from = side === 'top' ? entry.top : entry.bottom
    if (!from.includes(normalizedPort)) from.push(normalizedPort)
    map.set(deviceId, entry)
  }

  props.links.forEach(link => {
    const fromPort = (link.fromPort || '').trim()
    const toPort = (link.toPort || '').trim()

    let fromSide = fromPort
      ? resolveAutoPortSide(link.fromDeviceId, link.toDeviceId, fromPort, deviceTierMap.value)
      : 'bottom'
    let toSide = toPort
      ? resolveAutoPortSide(link.toDeviceId, link.fromDeviceId, toPort, deviceTierMap.value)
      : 'bottom'

    const fromOverride = props.portAnchorOverrides?.get(link.fromDeviceId)?.get(fromPort)
    if (fromOverride) fromSide = normalizedOverrideSide(fromOverride.side)
    const toOverride = props.portAnchorOverrides?.get(link.toDeviceId)?.get(toPort)
    if (toOverride) toSide = normalizedOverrideSide(toOverride.side)

    addPort(link.fromDeviceId, fromPort, fromSide)
    addPort(link.toDeviceId, toPort, toSide)
  })

  props.portAnchorOverrides?.forEach((ports, deviceId) => {
    ports.forEach((override, portName) => {
      addPort(deviceId, portName, normalizedOverrideSide(override.side))
    })
  })

  props.devicePortsMap?.forEach((ports, deviceId) => {
    ports.forEach(port => {
      addPort(deviceId, port.name, normalizedOverrideSide(port.side))
    })
  })

  map.forEach((entry, deviceId) => {
    const overrides = props.portAnchorOverrides?.get(deviceId)
    const sortSide = (ports: string[]) => {
      if (!overrides || overrides.size === 0) {
        ports.sort(comparePorts)
        return
      }
      // Tính effective ratio cho TẤT CẢ port:
      // - Port có override: dùng offsetRatio
      // - Port không override: dùng auto-slot ratio theo thứ tự comparePorts
      const natural = [...ports].sort(comparePorts)
      const total = natural.length
      const effectiveRatio = new Map<string, number>()
      natural.forEach((port, index) => {
        const override = overrides.get(port)
        if (override?.offsetRatio != null) {
          effectiveRatio.set(port, override.offsetRatio)
        } else {
          effectiveRatio.set(port, (index + 1) / (total + 1))
        }
      })
      ports.sort((a, b) => (effectiveRatio.get(a) ?? 0.5) - (effectiveRatio.get(b) ?? 0.5))
    }
    sortSide(entry.top)
    sortSide(entry.bottom)
  })

  return map
})

const estimatePortCellWidth = (portName: string) => {
  const text = portName.trim()
  const charWidth = DEVICE_PORT_FONT_SIZE * 0.62
  return Math.max(DEVICE_PORT_CELL_MIN_WIDTH, Math.ceil(text.length * charWidth + 10))
}

const estimateBandWidth = (ports: string[]) => {
  if (!ports.length) return 0
  const cellsWidth = ports.reduce((sum, port) => sum + estimatePortCellWidth(port), 0)
  const gapsWidth = DEVICE_PORT_CELL_GAP * Math.max(ports.length - 1, 0)
  return DEVICE_PORT_BAND_PADDING_X * 2 + cellsWidth + gapsWidth
}

const resolveDeviceRenderFrame = (deviceRect: { width: number; height: number }, bands: DevicePortBands): DeviceRenderFrame => {
  const topBandHeight = bands.top.length > 0 ? DEVICE_PORT_BAND_HEIGHT : 0
  const bottomBandHeight = bands.bottom.length > 0 ? DEVICE_PORT_BAND_HEIGHT : 0
  const minBodyHeight = Math.max(
    DEVICE_LABEL_MIN_HEIGHT,
    DEVICE_LABEL_FONT_SIZE + DEVICE_BODY_VERTICAL_PADDING * 2
  )
  const baseTotalHeight = Math.max(deviceRect.height, DEVICE_STANDARD_TOTAL_HEIGHT)
  const availableBodyHeight = baseTotalHeight - topBandHeight - bottomBandHeight
  const bodyHeight = Math.max(availableBodyHeight, minBodyHeight)
  return { topBandHeight, bottomBandHeight, bodyHeight }
}

const expandDeviceRectForPorts = (deviceId: string, rect: { x: number; y: number; width: number; height: number }) => {
  const bands = devicePortBands.value.get(deviceId) || { top: [], bottom: [] }
  const width = Math.max(
    rect.width,
    DEVICE_MIN_WIDTH,
    estimateBandWidth(bands.top),
    estimateBandWidth(bands.bottom)
  )
  const frame = resolveDeviceRenderFrame(rect, bands)
  const height = frame.topBandHeight + frame.bodyHeight + frame.bottomBandHeight
  const centerX = rect.x + rect.width / 2
  return {
    x: centerX - width / 2,
    // Keep top baseline stable, grow downward to avoid drifting devices upward on dense port bands.
    y: rect.y,
    width,
    height
  }
}

const buildPortCells = (
  deviceId: string,
  ports: string[],
  y: number,
  deviceWidth: number,
  side: 'top' | 'bottom'
): DevicePortCell[] => {
  if (!ports.length) return []
  const cellWidths = ports.map(estimatePortCellWidth)
  const totalWidth = cellWidths.reduce((sum, width) => sum + width, 0) + DEVICE_PORT_CELL_GAP * Math.max(ports.length - 1, 0)
  const startX = Math.max(DEVICE_PORT_BAND_PADDING_X, (deviceWidth - totalWidth) / 2)
  let cursorX = startX
  const cells: DevicePortCell[] = []
  ports.forEach((portName, index) => {
    const width = cellWidths[index]
    const id = `${deviceId}-${side}-${portName}`
    cells.push({
      id,
      rect: {
        x: cursorX,
        y: y + DEVICE_PORT_BAND_PADDING_Y,
        width,
        height: DEVICE_PORT_CELL_HEIGHT,
        fill: '#ffffff',
        stroke: '#2b2a28',
        strokeWidth: 1,
        cornerRadius: 0,
        opacity: 0.96
      },
      text: {
        x: cursorX + 2,
        y: y + DEVICE_PORT_BAND_PADDING_Y + 1,
        width: Math.max(width - 4, 1),
        height: Math.max(DEVICE_PORT_CELL_HEIGHT - 2, 1),
        text: portName,
        fontSize: DEVICE_PORT_FONT_SIZE,
        fontFamily: FONT_FAMILY,
        fill: '#2b2a28',
        align: 'center',
        verticalAlign: 'middle'
      }
    })
    cursorX += width + DEVICE_PORT_CELL_GAP
  })
  return cells
}

const deviceViewMap = computed(() => {
  const map = new Map<string, { x: number; y: number; width: number; height: number }>()
  const devicesByArea = new Map<string, Array<{ device: DeviceModel; rect: { x: number; y: number; width: number; height: number } }>>()

  props.devices.forEach(device => {
    // Priority 1: Auto-layout preview coords (temporary, from dialog)
    const autoCoords = props.autoLayoutCoords?.get(device.id)
    if (autoCoords) {
      const deviceWithAutoCoords = { ...device, x: autoCoords.x * 120, y: autoCoords.y * 120 }
      const baseRect = logicalRectToView(deviceWithAutoCoords, layoutViewport.value)
      map.set(device.id, expandDeviceRectForPorts(device.id, baseRect))
      return
    }

    // Priority 2: Database positions (from applied auto-layout or manual positioning)
    // If device has non-zero position_x/position_y from DB, use them directly
    if (device.x !== 0 || device.y !== 0) {
      const baseRect = logicalRectToView(device, layoutViewport.value)
      map.set(device.id, expandDeviceRectForPorts(device.id, baseRect))
      return
    }

    // Priority 3: Fallback to tier-based positioning (for devices without positions)
    const baseRect = logicalRectToView(device, layoutViewport.value)
    const rect = expandDeviceRectForPorts(device.id, baseRect)
    const list = devicesByArea.get(device.areaId) || []
    list.push({ device, rect })
    devicesByArea.set(device.areaId, list)
  })

  const clampIntoArea = (rect: { x: number; y: number; width: number; height: number }, area: { x: number; y: number; width: number; height: number }) => {
    const minX = area.x + AREA_PADDING
    const minY = area.y + AREA_PADDING
    const maxX = area.x + area.width - rect.width - AREA_PADDING
    const maxY = area.y + area.height - rect.height - AREA_PADDING
    rect.x = maxX >= minX ? Math.min(Math.max(rect.x, minX), maxX) : minX
    rect.y = maxY >= minY ? Math.min(Math.max(rect.y, minY), maxY) : minY
  }

  const rectsOverlap = (a: { x: number; y: number; width: number; height: number }, b: { x: number; y: number; width: number; height: number }) => {
    return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y
  }

  devicesByArea.forEach((entries, areaId) => {
    const area = areaViewMap.value.get(areaId)
    if (!area) {
      entries.forEach(entry => map.set(entry.device.id, entry.rect))
      return
    }

    let deviceArea = area
    const areaModel = areaById.value.get(areaId)
    let zoneName = ''
    if (areaModel) {
      const parts = areaModel.name.split(' - ')
      const location = parts[0]
      zoneName = parts.slice(1).join(' - ')
      if (zoneName === 'Head Office') {
        const subTop = headOfficeTopByLocation.value.get(location)
        if (subTop !== undefined) {
          const usableHeight = Math.max(subTop - area.y - DEVICE_GAP, 0)
          if (usableHeight > 0) {
            deviceArea = { ...area, height: usableHeight }
          }
        }
      }
    }

    const labelGap = SUB_ZONES.has(zoneName) ? LABEL_GAP_SUB : LABEL_GAP_MAIN
    deviceArea = {
      ...deviceArea,
      y: deviceArea.y + labelGap,
      height: Math.max(deviceArea.height - labelGap, 0)
    }

    const sorted = [...entries].sort((a, b) => a.device.name.localeCompare(b.device.name))
    const maxWidth = Math.max(...sorted.map(entry => entry.rect.width))
    const maxHeight = Math.max(...sorted.map(entry => entry.rect.height))
    const availableWidth = Math.max(deviceArea.width - AREA_PADDING * 2, maxWidth)
    const cellWidth = maxWidth + DEVICE_GAP
    const cellHeight = maxHeight + DEVICE_GAP
    const maxCols = Math.max(1, Math.floor((availableWidth + DEVICE_GAP) / cellWidth))

    const tiers = new Map<string, Array<{ device: DeviceModel; rect: { x: number; y: number; width: number; height: number } }>>()
    sorted.forEach(entry => {
      const role = resolveDeviceRole(entry.device)
      const list = tiers.get(role) || []
      list.push(entry)
      tiers.set(role, list)
    })

    const order = SUB_ZONES.has(zoneName) ? ROLE_ORDER_SUB : ROLE_ORDER_MAIN
    let rowCursor = 0

    order.forEach(role => {
      const list = tiers.get(role)
      if (!list || list.length === 0) return
      const cols = Math.min(maxCols, list.length)
      const rowsNeeded = Math.ceil(list.length / cols)
      list.forEach((entry, index) => {
        const col = index % cols
        const row = Math.floor(index / cols)
        const rect = { ...entry.rect }
        rect.x = deviceArea.x + AREA_PADDING + col * cellWidth
        rect.y = deviceArea.y + AREA_PADDING + (rowCursor + row) * cellHeight
        clampIntoArea(rect, deviceArea)
        map.set(entry.device.id, rect)
      })
      rowCursor += rowsNeeded
    })

    // Ensure no overlap after clamping (push down in same column)
    const placed = sorted
      .map(entry => ({ id: entry.device.id, rect: map.get(entry.device.id) }))
      .filter(item => item.rect)
      .map(item => item as { id: string; rect: { x: number; y: number; width: number; height: number } })
      .sort((a, b) => a.rect.y - b.rect.y || a.rect.x - b.rect.x)

    for (let i = 1; i < placed.length; i += 1) {
      const prev = placed[i - 1]
      const curr = placed[i]
      const sameColumn = Math.abs(curr.rect.x - prev.rect.x) < (cellWidth * 0.5)
      if (sameColumn && curr.rect.y < prev.rect.y + prev.rect.height + DEVICE_GAP) {
        curr.rect.y = prev.rect.y + prev.rect.height + DEVICE_GAP
        clampIntoArea(curr.rect, deviceArea)
      }
    }
  })

  return map
})

const visibleDevices = computed(() => {
  return props.devices
    .filter(device => deviceViewMap.value.has(device.id))
    .map(device => {
      const rect = deviceViewMap.value.get(device.id)!
      const isSelected = props.selectedId === device.id
      const bands = devicePortBands.value.get(device.id) || { top: [], bottom: [] }
      const frame = resolveDeviceRenderFrame(rect, bands)
      const bodyY = frame.topBandHeight
      const bodyHeight = frame.bodyHeight
      const iconKind = resolveDeviceIconKind(device)
      const iconFrame = buildDeviceIconFrame(bodyY, bodyHeight, rect.width)
      const iconShape = buildDeviceIconShape(iconKind, iconFrame, isSelected)
      const labelX = iconFrame
        ? Math.min(iconFrame.x + iconFrame.size + DEVICE_ICON_LABEL_GAP, Math.max(rect.width - 20, 10))
        : 10
      const topPorts = buildPortCells(device.id, bands.top, 0, rect.width, 'top')
      const bottomPorts = buildPortCells(
        device.id,
        bands.bottom,
        rect.height - frame.bottomBandHeight,
        rect.width,
        'bottom'
      )
      return {
        id: device.id,
        group: {
          x: rect.x,
          y: rect.y,
          draggable: !!props.positionEditEnabled,
          clipX: 0,
          clipY: 0,
          clipWidth: rect.width,
          clipHeight: rect.height
        },
        bodyRect: {
          x: 0,
          y: bodyY,
          width: rect.width,
          height: bodyHeight,
          fill: '#ffffff',
          stroke: isSelected ? '#d66c3b' : '#2b2a28',
          strokeWidth: isSelected ? 2 : 1,
          cornerRadius: 0,
          shadowColor: 'transparent',
          shadowBlur: 0,
          shadowOffset: { x: 0, y: 0 },
          shadowOpacity: 0,
          shadowForStrokeEnabled: false
        },
        iconShape,
        topPorts,
        bottomPorts,
        label: {
          x: labelX,
          y: bodyY + Math.max((bodyHeight - DEVICE_LABEL_FONT_SIZE) / 2 - 1, 4),
          width: Math.max(rect.width - labelX - 8, 0),
          text: device.name,
          fontSize: DEVICE_LABEL_FONT_SIZE,
          fontFamily: FONT_FAMILY,
          fill: '#1f1f1f',
          wrap: 'none',
          align: 'left',
          ellipsis: true
        }
      }
  })
})

const mergeBounds = (boundsList: Array<{ minX: number; minY: number; maxX: number; maxY: number } | null>) => {
  let minX = 0
  let minY = 0
  let maxX = 0
  let maxY = 0
  let hasBounds = false

  boundsList.forEach(bounds => {
    if (!bounds) return
    if (!hasBounds) {
      minX = bounds.minX
      minY = bounds.minY
      maxX = bounds.maxX
      maxY = bounds.maxY
      hasBounds = true
      return
    }
    minX = Math.min(minX, bounds.minX)
    minY = Math.min(minY, bounds.minY)
    maxX = Math.max(maxX, bounds.maxX)
    maxY = Math.max(maxY, bounds.maxY)
  })

  if (!hasBounds) return null
  return { minX, minY, maxX, maxY }
}

const areaBounds = computed(() => {
  // Loại trừ waypoint areas (_wp_) khỏi bounding box
  const wpIds = new Set(props.areas.filter(a => a.name.endsWith('_wp_')).map(a => a.id))
  let minX = 0
  let minY = 0
  let maxX = 0
  let maxY = 0
  let hasBounds = false
  areaDisplayMap.value.forEach((rect, id) => {
    if (wpIds.has(id)) return
    if (!hasBounds) {
      minX = rect.x
      minY = rect.y
      maxX = rect.x + rect.width
      maxY = rect.y + rect.height
      hasBounds = true
      return
    }
    minX = Math.min(minX, rect.x)
    minY = Math.min(minY, rect.y)
    maxX = Math.max(maxX, rect.x + rect.width)
    maxY = Math.max(maxY, rect.y + rect.height)
  })
  if (!hasBounds) return null
  return { minX, minY, maxX, maxY }
})

const waypointBounds = computed(() => {
  const wpAreas = props.areas.filter(a => a.name.endsWith('_wp_'))
  if (!wpAreas.length) return null
  let minX = 0
  let minY = 0
  let maxX = 0
  let maxY = 0
  let hasBounds = false
  wpAreas.forEach(area => {
    const rect = areaViewMap.value.get(area.id)
    if (!rect) return
    if (!hasBounds) {
      minX = rect.x
      minY = rect.y
      maxX = rect.x + rect.width
      maxY = rect.y + rect.height
      hasBounds = true
      return
    }
    minX = Math.min(minX, rect.x)
    minY = Math.min(minY, rect.y)
    maxX = Math.max(maxX, rect.x + rect.width)
    maxY = Math.max(maxY, rect.y + rect.height)
  })
  if (!hasBounds) return null
  return { minX, minY, maxX, maxY }
})

const deviceBounds = computed(() => {
  let minX = 0
  let minY = 0
  let maxX = 0
  let maxY = 0
  let hasBounds = false
  deviceViewMap.value.forEach(rect => {
    if (!hasBounds) {
      minX = rect.x
      minY = rect.y
      maxX = rect.x + rect.width
      maxY = rect.y + rect.height
      hasBounds = true
      return
    }
    minX = Math.min(minX, rect.x)
    minY = Math.min(minY, rect.y)
    maxX = Math.max(maxX, rect.x + rect.width)
    maxY = Math.max(maxY, rect.y + rect.height)
  })
  if (!hasBounds) return null
  return { minX, minY, maxX, maxY }
})


const zoomScale = computed(() => {
  const baseScale = layoutViewport.value.scale || 1
  return baseScale > 0 ? props.viewport.scale / baseScale : 1
})

const cameraOffset = computed(() => ({
  x: props.viewport.offsetX - layoutViewport.value.offsetX,
  y: props.viewport.offsetY - layoutViewport.value.offsetY
}))

const layerTranslation = computed(() => {
  const base = cameraOffset.value
  if (!isPanning.value) return base
  return {
    x: base.x + panTranslation.value.x,
    y: base.y + panTranslation.value.y
  }
})

const layerTransform = computed(() => ({
  x: layerTranslation.value.x,
  y: layerTranslation.value.y,
  scaleX: zoomScale.value,
  scaleY: zoomScale.value
}))

const deviceAreaMap = computed(() => {
  const map = new Map<string, string | null>()
  props.devices.forEach(device => {
    map.set(device.id, device.areaId || null)
  })
  return map
})

function clearDragGuides() {
  activeGuideCoords.value = { x: null, y: null }
}

function buildAxisAnchors(start: number, size: number) {
  return [start, start + size * 0.5, start + size]
}

function resolveAlignmentMatch(
  sourceValues: number[],
  targetValues: number[],
  threshold: number,
  axis: 'x' | 'y'
): AlignmentMatch | null {
  let best: AlignmentMatch | null = null
  let bestAbs = Number.POSITIVE_INFINITY
  sourceValues.forEach(source => {
    targetValues.forEach(target => {
      const delta = target - source
      const abs = Math.abs(delta)
      if (abs > threshold || abs >= bestAbs) return
      bestAbs = abs
      best = { axis, delta, lineCoord: target }
    })
  })
  return best
}

function resolveStandardPositionMatch(
  value: number,
  axis: 'x' | 'y',
  threshold: number
): AlignmentMatch | null {
  const offset = axis === 'x' ? layoutViewport.value.offsetX : layoutViewport.value.offsetY
  const logicalValue = viewToLogical(value, layoutViewport.value.scale, offset)
  const snappedLogical = Math.round(logicalValue / POSITION_STANDARD_STEP_PX) * POSITION_STANDARD_STEP_PX
  const snappedView = logicalToView(snappedLogical, layoutViewport.value.scale, offset)
  const delta = snappedView - value
  if (Math.abs(delta) > threshold) return null
  return {
    axis,
    delta,
    lineCoord: snappedView,
  }
}

function pickBestSnap(primary: AlignmentMatch | null, secondary: AlignmentMatch | null) {
  if (primary && secondary) {
    return Math.abs(primary.delta) <= Math.abs(secondary.delta) ? primary : secondary
  }
  return primary || secondary
}

function collectRelatedRects(context: DragObjectContext) {
  if (context.type === 'area') {
    const rects: Rect[] = []
    areaRenderMap.value.forEach((rect, id) => {
      if (id === context.id) return
      rects.push(rect)
    })
    return rects
  }

  const rects: Rect[] = []
  const areaId = context.areaId
  deviceViewMap.value.forEach((rect, id) => {
    if (id === context.id) return
    if (areaId && deviceAreaMap.value.get(id) !== areaId) return
    rects.push(rect)
  })
  if (areaId) {
    const areaRect = areaRenderMap.value.get(areaId)
    if (areaRect) rects.push(areaRect)
  }
  return rects
}

const DEFAULT_RENDER_TUNING = {
  port_edge_inset: 6,
  port_label_offset: 18,
  bundle_gap: 34,
  bundle_stub: 42,
  area_clearance: 36,
  area_anchor_offset: 26,
  label_gap_x: 8,
  label_gap_y: 6,
  corridor_gap: 64,
  inter_area_links_per_channel: 4,
  inter_area_max_channels: 4,
  inter_area_occupancy_weight: 1.0
}
const renderTuning = computed(() => ({
  ...DEFAULT_RENDER_TUNING,
  ...(props.renderTuning || {})
}))

const { visibleLinks, visibleLinkShapes } = useLinkRouting({
  props,
  layoutViewport,
  renderTuning,
  deviceViewMap,
  areaViewMap: areaDisplayMap,
  deviceAreaMap,
  areaBounds,
  isPanning
})
const visibleLinkPortLabels = computed(() => {
  // Port label được render trực tiếp trên object (top/bottom port band), không render overlay trên link.
  return []
})

const linkBounds = computed(() => {
  if (!visibleLinks.value.length) return null
  let minX = 0
  let minY = 0
  let maxX = 0
  let maxY = 0
  let hasBounds = false

  visibleLinks.value.forEach(link => {
    const points = link.points
    for (let i = 0; i < points.length; i += 2) {
      const x = points[i]
      const y = points[i + 1]
      if (!hasBounds) {
        minX = x
        minY = y
        maxX = x
        maxY = y
        hasBounds = true
        continue
      }
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x)
      maxY = Math.max(maxY, y)
    }
  })

  if (!hasBounds) return null
  return { minX, minY, maxX, maxY }
})

const diagramBounds = computed(() => mergeBounds([
  areaBounds.value,
  waypointBounds.value,
  deviceBounds.value,
  linkBounds.value
]))

// L2 Labels - VLAN info on devices
const l2Labels = computed(() => {
  const mode = props.viewMode || 'L1'
  if (isPanning.value) return []
  if (mode !== 'L2') return []
  if (!props.l2Assignments || props.l2Assignments.length === 0) {
    return []
  }

  // Group assignments by device
  const byDevice = new Map<string, { vlans: Set<number>; modes: Set<string> }>()
  props.l2Assignments.forEach(a => {
    if (!a.device_id || a.vlan_id == null) return
    const existing = byDevice.get(a.device_id) || { vlans: new Set(), modes: new Set() }
    existing.vlans.add(a.vlan_id)
    existing.modes.add(a.port_mode)
    byDevice.set(a.device_id, existing)
  })
  const labels: Array<{
    id: string
    group: { x: number; y: number }
    bg: { x: number; y: number; width: number; height: number; fill: string; cornerRadius: number }
    text: { x: number; y: number; text: string; fontSize: number; fill: string }
  }> = []

  byDevice.forEach((info, deviceId) => {
    const deviceRect = deviceViewMap.value.get(deviceId)
    if (!deviceRect) return
    const vlans = Array.from(info.vlans).slice(0, 3).join(',')
    const moreCount = info.vlans.size > 3 ? ` +${info.vlans.size - 3}` : ''
    const text = `VLAN: ${vlans}${moreCount}`
    const labelWidth = text.length * 6 + 8
    labels.push({
      id: `l2-${deviceId}`,
      group: { x: deviceRect.x, y: deviceRect.y + deviceRect.height + 2 },
      bg: { x: 0, y: 0, width: labelWidth, height: 16, fill: '#e8f4e8', cornerRadius: 4 },
      text: { x: 4, y: 2, text, fontSize: 10, fontFamily: FONT_FAMILY, fill: '#2d5a2d' }
    })
  })

  return labels
})

// L3 Labels - IP addresses on devices
const l3Labels = computed(() => {
  const mode = props.viewMode || 'L1'
  if (isPanning.value) return []
  if (mode !== 'L3') return []
  if (!props.l3Addresses || props.l3Addresses.length === 0) return []

  // Group addresses by device
  const byDevice = new Map<string, Array<{ ip: string; prefix: number }>>()
  props.l3Addresses.forEach(a => {
    if (!a.device_id) return
    const list = byDevice.get(a.device_id) || []
    list.push({ ip: a.ip_address, prefix: a.prefix_length })
    byDevice.set(a.device_id, list)
  })

  const labels: Array<{
    id: string
    group: { x: number; y: number }
    bg: { x: number; y: number; width: number; height: number; fill: string; cornerRadius: number }
    text: { x: number; y: number; text: string; fontSize: number; fill: string }
  }> = []

  byDevice.forEach((addresses, deviceId) => {
    const deviceRect = deviceViewMap.value.get(deviceId)
    if (!deviceRect) return
    // Show first 2 IPs, then "+N more"
    const shown = addresses.slice(0, 2).map(a => `${a.ip}/${a.prefix}`).join(', ')
    const moreCount = addresses.length > 2 ? ` +${addresses.length - 2}` : ''
    const text = `${shown}${moreCount}`
    const labelWidth = Math.min(text.length * 6 + 8, deviceRect.width)
    // Position below device
    const yOffset = deviceRect.height + 2
    labels.push({
      id: `l3-${deviceId}`,
      group: { x: deviceRect.x, y: deviceRect.y + yOffset },
      bg: { x: 0, y: 0, width: labelWidth, height: 16, fill: '#e8e8f4', cornerRadius: 4 },
      text: { x: 4, y: 2, text, fontSize: 10, fontFamily: FONT_FAMILY, fill: '#2d2d5a' }
    })
  })

  return labels
})

function updateSize() {
  const el = containerRef.value
  if (!el) return
  const rect = {
    width: el.clientWidth,
    height: el.clientHeight
  }
  if (!rect.width || !rect.height) return
  if (rect.width === stageSize.value.width && rect.height === stageSize.value.height) return
  stageSize.value = {
    width: Math.max(Math.floor(rect.width), 0),
    height: Math.max(Math.floor(rect.height), 0)
  }
}

function emitSelect(id: string, type: 'device' | 'area') {
  emit('select', { id, type })
}

function batchDraw() {
  gridLayerRef.value?.getNode()?.batchDraw()
  areaLayerRef.value?.getNode()?.batchDraw()
  linkLayerRef.value?.getNode()?.batchDraw()
  deviceLayerRef.value?.getNode()?.batchDraw()
  overlayLayerRef.value?.getNode()?.batchDraw()
}

let batchDrawRaf = 0
function scheduleBatchDraw() {
  if (batchDrawRaf) return
  batchDrawRaf = requestAnimationFrame(() => {
    batchDrawRaf = 0
    batchDraw()
  })
}

function isStageTarget(event: any) {
  const stage = stageRef.value?.getNode?.()
  if (!stage) return false
  const target = event?.target
  if (!target) return false
  if (target === stage) return true
  const name = typeof target.name === 'function'
    ? target.name()
    : (typeof target.getAttr === 'function' ? target.getAttr('name') : '')
  return name === 'grid-bg'
}

function onPointerDown(event: any) {
  if (!isStageTarget(event)) return
  const stage = stageRef.value?.getNode?.()
  const pointer = stage?.getPointerPosition?.()
  if (!pointer) return
  isPanning.value = true
  panStartPointer.value = { x: pointer.x, y: pointer.y }
  panBaseOffset.value = { x: props.viewport.offsetX, y: props.viewport.offsetY }
  panTranslation.value = { x: 0, y: 0 }
  pendingTranslation.value = null
}

function onObjectDragStart(_event: any, id: string, type: 'device' | 'area') {
  if (!props.positionEditEnabled) return
  const rect = type === 'area' ? areaRenderMap.value.get(id) : deviceViewMap.value.get(id)
  if (!rect) return

  isObjectDragging.value = true
  dragContext.value = {
    id,
    type,
    width: rect.width,
    height: rect.height,
    areaId: type === 'device' ? (deviceAreaMap.value.get(id) || null) : null,
  }
  clearDragGuides()

  isPanning.value = false
  panStartPointer.value = null
  panBaseOffset.value = null
  panTranslation.value = { x: 0, y: 0 }
  pendingTranslation.value = null
}

function onObjectDragMove(event: any, id: string, type: 'device' | 'area') {
  if (!props.positionEditEnabled) return
  const context = dragContext.value
  if (!context || context.id !== id || context.type !== type) return
  const target = event?.target
  if (!target || typeof target.x !== 'function' || typeof target.y !== 'function') return

  const rawX = Number(target.x())
  const rawY = Number(target.y())
  if (!Number.isFinite(rawX) || !Number.isFinite(rawY)) return

  const threshold = Math.max(2, DRAG_SNAP_THRESHOLD_PX / Math.max(zoomScale.value, 0.1))
  const relatedRects = collectRelatedRects(context)
  const targetXValues = relatedRects.flatMap(rect => buildAxisAnchors(rect.x, rect.width))
  const targetYValues = relatedRects.flatMap(rect => buildAxisAnchors(rect.y, rect.height))
  const sourceXValues = buildAxisAnchors(rawX, context.width)
  const sourceYValues = buildAxisAnchors(rawY, context.height)

  const matchX = resolveAlignmentMatch(sourceXValues, targetXValues, threshold, 'x')
  const matchY = resolveAlignmentMatch(sourceYValues, targetYValues, threshold, 'y')
  const standardMatchX = resolveStandardPositionMatch(rawX, 'x', threshold)
  const standardMatchY = resolveStandardPositionMatch(rawY, 'y', threshold)
  const finalMatchX = pickBestSnap(matchX, standardMatchX)
  const finalMatchY = pickBestSnap(matchY, standardMatchY)

  const snappedX = finalMatchX ? rawX + finalMatchX.delta : rawX
  const snappedY = finalMatchY ? rawY + finalMatchY.delta : rawY
  if (snappedX !== rawX) target.x(snappedX)
  if (snappedY !== rawY) target.y(snappedY)

  activeGuideCoords.value = {
    x: finalMatchX?.lineCoord ?? null,
    y: finalMatchY?.lineCoord ?? null,
  }
}

function onObjectDragEnd(event: any, id: string, type: 'device' | 'area') {
  if (!props.positionEditEnabled) return
  const target = event?.target
  if (!target || typeof target.x !== 'function' || typeof target.y !== 'function') return
  const x = Number(target.x())
  const y = Number(target.y())
  if (!Number.isFinite(x) || !Number.isFinite(y)) return

  isObjectDragging.value = false
  dragContext.value = null
  clearDragGuides()

  const logicalX = viewToLogical(x, layoutViewport.value.scale, layoutViewport.value.offsetX)
  const logicalY = viewToLogical(y, layoutViewport.value.scale, layoutViewport.value.offsetY)
  const snappedLogicalX = Math.round(logicalX / POSITION_STANDARD_STEP_PX) * POSITION_STANDARD_STEP_PX
  const snappedLogicalY = Math.round(logicalY / POSITION_STANDARD_STEP_PX) * POSITION_STANDARD_STEP_PX
  const snappedViewX = logicalToView(snappedLogicalX, layoutViewport.value.scale, layoutViewport.value.offsetX)
  const snappedViewY = logicalToView(snappedLogicalY, layoutViewport.value.scale, layoutViewport.value.offsetY)
  if (Math.abs(snappedViewX - x) > 0.01) target.x(snappedViewX)
  if (Math.abs(snappedViewY - y) > 0.01) target.y(snappedViewY)
  emit('object:position-change', {
    id,
    type,
    x: Number(snappedLogicalX.toFixed(2)),
    y: Number(snappedLogicalY.toFixed(2)),
  })
}

function onPointerMove(event: any) {
  if (!isPanning.value) return
  const stage = stageRef.value?.getNode?.()
  const pointer = stage?.getPointerPosition?.()
  if (!pointer || !panStartPointer.value || !panBaseOffset.value) return
  const dx = pointer.x - panStartPointer.value.x
  const dy = pointer.y - panStartPointer.value.y

  // Clamp pan to keep diagram visible (allow 20% overflow)
  const MARGIN = 200  // Pixels of margin
  let newOffsetX = panBaseOffset.value.x + dx
  let newOffsetY = panBaseOffset.value.y + dy

  const bounds = diagramBounds.value
  if (bounds && stageSize.value.width > 0 && stageSize.value.height > 0) {
    const diagramWidth = bounds.maxX - bounds.minX
    const diagramHeight = bounds.maxY - bounds.minY

    // Clamp X (allow panning until diagram edge is at margin distance from canvas edge)
    const maxOffsetX = MARGIN
    const minOffsetX = stageSize.value.width - diagramWidth - MARGIN
    newOffsetX = Math.max(minOffsetX, Math.min(maxOffsetX, newOffsetX))

    // Clamp Y
    const maxOffsetY = MARGIN
    const minOffsetY = stageSize.value.height - diagramHeight - MARGIN
    newOffsetY = Math.max(minOffsetY, Math.min(maxOffsetY, newOffsetY))
  }

  const nextTranslation = {
    x: newOffsetX - panBaseOffset.value.x,
    y: newOffsetY - panBaseOffset.value.y
  }
  pendingTranslation.value = nextTranslation
  if (!panRaf) {
    panRaf = requestAnimationFrame(() => {
      panRaf = 0
      if (!pendingTranslation.value) return
      panTranslation.value = pendingTranslation.value
    })
  }
}

function onPointerUp() {
  isPanning.value = false
  panStartPointer.value = null
  if (panBaseOffset.value) {
    emit('update:viewport', {
      ...props.viewport,
      offsetX: panBaseOffset.value.x + panTranslation.value.x,
      offsetY: panBaseOffset.value.y + panTranslation.value.y
    })
  }
  panBaseOffset.value = null
  panTranslation.value = { x: 0, y: 0 }
  pendingTranslation.value = null
  if (panRaf) {
    cancelAnimationFrame(panRaf)
    panRaf = 0
  }
}

onMounted(() => {
  updateSize()
  observer = new ResizeObserver(() => updateSize())
  if (containerRef.value) {
    observer.observe(containerRef.value)
  }
})

onBeforeUnmount(() => {
  if (observer && containerRef.value) {
    observer.unobserve(containerRef.value)
  }
  observer = null
  isObjectDragging.value = false
  dragContext.value = null
  clearDragGuides()
  if (batchDrawRaf) {
    cancelAnimationFrame(batchDrawRaf)
    batchDrawRaf = 0
  }
})

watch([visibleAreas, visibleDevices, visibleLinks, visibleLinkPortLabels, l2Labels, l3Labels, alignmentGuides, stageSize], () => {
  scheduleBatchDraw()
})

</script>

<style scoped>
.canvas-shell {
  width: 100%;
  height: 100%;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid rgba(28, 28, 28, 0.1);
  box-shadow: none;
  overflow: hidden;
}
</style>
