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
      <v-layer ref="gridLayerRef">
        <v-rect :config="gridConfig" />
      </v-layer>

      <v-layer ref="areaLayerRef">
        <v-group
          v-for="area in visibleAreas"
          :key="area.id"
          :config="area.group"
          @click="() => emitSelect(area.id, 'area')"
        >
          <v-rect :config="area.rect" />
          <v-text :config="area.label" />
        </v-group>
      </v-layer>

      <v-layer ref="linkLayerRef">
        <v-line
          v-for="link in visibleLinks"
          :key="link.id"
          :config="link.config"
        />
      </v-layer>

      <v-layer ref="deviceLayerRef">
        <v-group
          v-for="device in visibleDevices"
          :key="device.id"
          :config="device.group"
          @click="() => emitSelect(device.id, 'device')"
        >
          <v-rect :config="device.rect" />
          <v-text :config="device.label" />
        </v-group>
      </v-layer>

      <!-- L2/L3 Overlay Layer -->
      <v-layer ref="overlayLayerRef">
        <!-- L3 IP Labels (show in L3 and overview) -->
        <v-group
          v-for="label in l3Labels"
          :key="label.id"
          :config="label.group"
        >
          <v-rect :config="label.bg" />
          <v-text :config="label.text" />
        </v-group>
        <!-- L2 VLAN Labels (show in L2 and overview) -->
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
import { getVisibleBounds, logicalRectToView } from '../utils/viewport'

const props = defineProps<{
  areas: AreaModel[]
  devices: DeviceModel[]
  links: LinkModel[]
  viewport: Viewport
  layoutMode?: 'cisco' | 'iso' | 'custom'
  selectedId?: string | null
  viewMode?: ViewMode
  l2Assignments?: L2AssignmentRecord[]
  l3Addresses?: L3AddressRecord[]
  autoLayoutCoords?: Map<string, { x: number; y: number }> // Auto-layout coords (logical units/inches)
}>()

const emit = defineEmits<{
  (event: 'update:viewport', value: Viewport): void
  (event: 'select', payload: { id: string; type: 'device' | 'area' }): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const stageRef = ref()
const stageSize = ref({ width: 300, height: 200 })
let observer: ResizeObserver | null = null
const isPanning = ref(false)
const lastPointer = ref<{ x: number; y: number } | null>(null)

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

const visibleBounds = computed(() => getVisibleBounds(stageSize.value, props.viewport))

const AREA_PADDING = 12
const TEXT_PADDING = 10
const SUB_ZONES = new Set(['Department', 'Projects', 'IT'])
const LABEL_GAP_MAIN = 22
const LABEL_GAP_SUB = 18

const areaViewMap = computed(() => {
  const map = new Map<string, { x: number; y: number; width: number; height: number }>()
  props.areas.forEach(area => {
    const rect = logicalRectToView(area, props.viewport)
    map.set(area.id, rect)
  })
  return map
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
    const rect = areaViewMap.value.get(area.id)
    if (!rect) return

    areaList.forEach(potentialParent => {
      if (potentialParent.id === area.id) return
      const parentRect = areaViewMap.value.get(potentialParent.id)
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
  const visible = props.areas
    .filter(area => areaViewMap.value.has(area.id))
    .sort((a, b) => {
      const rectA = areaViewMap.value.get(a.id)
      const rectB = areaViewMap.value.get(b.id)
      if (!rectA || !rectB) return 0
      return rectB.width * rectB.height - rectA.width * rectA.height
    })
    .map(area => {
      const rect = areaViewMap.value.get(area.id)!
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

      const isSubZone = SUB_ZONES.has(zone)
      const fontSize = isSubZone ? 12 : 14

      return {
        id: area.id,
        group: {
          x: rect.x,
          y: rect.y,
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
          fill: area.fill,
          stroke: area.stroke,
          strokeWidth: hasChildren ? 2 : 1.5,
          cornerRadius: 10
        },
        label: {
          x: labelAlign === 'right' ? rect.width - TEXT_PADDING : TEXT_PADDING,
          y: labelY,
          width: Math.max(rect.width - TEXT_PADDING * 2, 0),
          text: area.name,
          fontSize,
          fill: '#3f3a33',
          wrap: 'none',
          ellipsis: true,
          align: labelAlign
        }
      }
    })
  return visible
})

const DEVICE_GAP = 12
const ROLE_ORDER_MAIN = ['router', 'firewall', 'core', 'dist', 'access', 'endpoint']
const ROLE_ORDER_SUB = ['access', 'endpoint']

const DEVICE_COLORS: Array<{ match: (device: DeviceModel) => boolean; color: [number, number, number] }> = [
  { match: device => device.type === 'Router' || /RTR|ROUTER|ISP/i.test(device.name), color: [70, 130, 180] },
  { match: device => device.type === 'Firewall' || /FW|FIREWALL/i.test(device.name), color: [220, 80, 80] },
  { match: device => /CORE|SW-CORE/i.test(device.name), color: [34, 139, 34] },
  { match: device => /DIST|DISTR/i.test(device.name), color: [60, 179, 113] },
  { match: device => /ACC|ACCESS/i.test(device.name), color: [0, 139, 139] },
  { match: device => device.type === 'Server' || /SRV|SERVER|APP|WEB|DB/i.test(device.name), color: [106, 90, 205] },
  { match: device => device.type === 'Storage' || /STO|NAS|SAN|STORAGE|BACKUP/i.test(device.name), color: [205, 133, 63] },
  { match: device => device.type === 'AP' || /\\bAP\\b/i.test(device.name), color: [0, 139, 139] }
]

function rgbToHex(rgb: [number, number, number]) {
  return `#${rgb.map(value => value.toString(16).padStart(2, '0')).join('')}`
}

function resolveDeviceFill(device: DeviceModel) {
  for (const entry of DEVICE_COLORS) {
    if (entry.match(device)) {
      return rgbToHex(entry.color)
    }
  }
  return '#d9d9d9'
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
  if (name.includes('ACC') || name.includes('ACCESS')) {
    return 'access'
  }
  return 'endpoint'
}

const deviceViewMap = computed(() => {
  const map = new Map<string, { x: number; y: number; width: number; height: number }>()
  const devicesByArea = new Map<string, Array<{ device: DeviceModel; rect: { x: number; y: number; width: number; height: number } }>>()

  props.devices.forEach(device => {
    // Priority 1: Auto-layout preview coords (temporary, from dialog)
    const autoCoords = props.autoLayoutCoords?.get(device.id)
    if (autoCoords) {
      const deviceWithAutoCoords = { ...device, x: autoCoords.x * 120, y: autoCoords.y * 120 }
      const rect = logicalRectToView(deviceWithAutoCoords, props.viewport)
      map.set(device.id, rect)
      return
    }

    // Priority 2: Database positions (from applied auto-layout or manual positioning)
    // If device has non-zero position_x/position_y from DB, use them directly
    if (device.x !== 0 || device.y !== 0) {
      const rect = logicalRectToView(device, props.viewport)
      map.set(device.id, rect)
      return
    }

    // Priority 3: Fallback to tier-based positioning (for devices without positions)
    const rect = logicalRectToView(device, props.viewport)
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
        if (props.layoutMode === 'iso') {
          rect.x = deviceArea.x + AREA_PADDING + (rowCursor + row) * cellWidth
          rect.y = deviceArea.y + AREA_PADDING + col * cellHeight
        } else {
          rect.x = deviceArea.x + AREA_PADDING + col * cellWidth
          rect.y = deviceArea.y + AREA_PADDING + (rowCursor + row) * cellHeight
        }
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
      const fill = resolveDeviceFill(device)
      return {
        id: device.id,
        group: {
          x: rect.x,
          y: rect.y,
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
          fill,
          stroke: isSelected ? '#d66c3b' : '#5f564f',
          strokeWidth: isSelected ? 2 : 1.2,
          cornerRadius: 8
        },
        label: {
          x: 8,
          y: 8,
          width: Math.max(rect.width - 16, 0),
          text: device.name,
          fontSize: 13,
          fill: '#302b27',
          wrap: 'none',
          ellipsis: true
        }
      }
    })
})

const areaBounds = computed(() => {
  let minX = 0
  let minY = 0
  let maxX = 0
  let maxY = 0
  let hasBounds = false
  areaViewMap.value.forEach(rect => {
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

const deviceAreaMap = computed(() => {
  const map = new Map<string, string | null>()
  props.devices.forEach(device => {
    map.set(device.id, device.areaId || null)
  })
  return map
})

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function computeAreaAnchor(
  areaRect: { x: number; y: number; width: number; height: number },
  fromPoint: { x: number; y: number },
  targetPoint: { x: number; y: number }
) {
  const dx = targetPoint.x - fromPoint.x
  const dy = targetPoint.y - fromPoint.y
  const inset = 6
  if (Math.abs(dx) >= Math.abs(dy)) {
    const x = dx >= 0 ? areaRect.x + areaRect.width : areaRect.x
    const y = clamp(fromPoint.y, areaRect.y + inset, areaRect.y + areaRect.height - inset)
    return { x, y }
  }
  const y = dy >= 0 ? areaRect.y + areaRect.height : areaRect.y
  const x = clamp(fromPoint.x, areaRect.x + inset, areaRect.x + areaRect.width - inset)
  return { x, y }
}

const visibleLinks = computed(() => {
  return props.links
    .map(link => {
      const fromView = deviceViewMap.value.get(link.fromDeviceId)
      const toView = deviceViewMap.value.get(link.toDeviceId)
      if (!fromView || !toView) return null
      const fromCenter = {
        x: fromView.x + fromView.width / 2,
        y: fromView.y + fromView.height / 2
      }
      const toCenter = {
        x: toView.x + toView.width / 2,
        y: toView.y + toView.height / 2
      }
      const fromAreaId = deviceAreaMap.value.get(link.fromDeviceId)
      const toAreaId = deviceAreaMap.value.get(link.toDeviceId)
      const fromArea = fromAreaId ? areaViewMap.value.get(fromAreaId) : null
      const toArea = toAreaId ? areaViewMap.value.get(toAreaId) : null

      let points = [fromCenter.x, fromCenter.y, toCenter.x, toCenter.y]
      if (fromAreaId && toAreaId && fromAreaId !== toAreaId && fromArea && toArea) {
        const fromAnchor = computeAreaAnchor(fromArea, fromCenter, toCenter)
        const toAnchor = computeAreaAnchor(toArea, toCenter, fromCenter)
        const bounds = areaBounds.value
        if (bounds) {
          const corridorGap = 24
          const dx = toCenter.x - fromCenter.x
          const dy = toCenter.y - fromCenter.y
          if (Math.abs(dx) >= Math.abs(dy)) {
            const topY = bounds.minY - corridorGap
            const bottomY = bounds.maxY + corridorGap
            const midY = (fromCenter.y + toCenter.y) / 2
            const corridorY = Math.abs(midY - topY) <= Math.abs(midY - bottomY) ? topY : bottomY
            points = [
              fromCenter.x, fromCenter.y,
              fromAnchor.x, fromAnchor.y,
              fromAnchor.x, corridorY,
              toAnchor.x, corridorY,
              toAnchor.x, toAnchor.y,
              toCenter.x, toCenter.y
            ]
          } else {
            const leftX = bounds.minX - corridorGap
            const rightX = bounds.maxX + corridorGap
            const midX = (fromCenter.x + toCenter.x) / 2
            const corridorX = Math.abs(midX - leftX) <= Math.abs(midX - rightX) ? leftX : rightX
            points = [
              fromCenter.x, fromCenter.y,
              fromAnchor.x, fromAnchor.y,
              corridorX, fromAnchor.y,
              corridorX, toAnchor.y,
              toAnchor.x, toAnchor.y,
              toCenter.x, toCenter.y
            ]
          }
        } else {
          const midX = (fromAnchor.x + toAnchor.x) / 2
          points = [
            fromCenter.x, fromCenter.y,
            fromAnchor.x, fromAnchor.y,
            midX, fromAnchor.y,
            midX, toAnchor.y,
            toAnchor.x, toAnchor.y,
            toCenter.x, toCenter.y
          ]
        }
      }

      return {
        id: link.id,
        config: {
          points,
          stroke: '#2b2a28',
          strokeWidth: 1.5,
          dash: link.style === 'dashed' ? [8, 6] : link.style === 'dotted' ? [2, 4] : [],
          opacity: 0.8
        }
      }
    })
    .filter(Boolean) as Array<{ id: string; config: Record<string, unknown> }>
})

// L2 Labels - VLAN info on devices
const l2Labels = computed(() => {
  const mode = props.viewMode || 'L1'
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
      text: { x: 4, y: 2, text, fontSize: 10, fill: '#2d5a2d' }
    })
  })

  return labels
})

// L3 Labels - IP addresses on devices
const l3Labels = computed(() => {
  const mode = props.viewMode || 'L1'
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
    // Position below device (and below L2 label if in overview)
    const yOffset = mode === 'overview' ? deviceRect.height + 20 : deviceRect.height + 2
    labels.push({
      id: `l3-${deviceId}`,
      group: { x: deviceRect.x, y: deviceRect.y + yOffset },
      bg: { x: 0, y: 0, width: labelWidth, height: 16, fill: '#e8e8f4', cornerRadius: 4 },
      text: { x: 4, y: 2, text, fontSize: 10, fill: '#2d2d5a' }
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
  lastPointer.value = { x: pointer.x, y: pointer.y }
}

function onPointerMove(event: any) {
  if (!isPanning.value) return
  const stage = stageRef.value?.getNode?.()
  const pointer = stage?.getPointerPosition?.()
  if (!pointer || !lastPointer.value) return
  const dx = pointer.x - lastPointer.value.x
  const dy = pointer.y - lastPointer.value.y
  lastPointer.value = { x: pointer.x, y: pointer.y }

  // Calculate diagram bounds (in view coordinates)
  let minX = 0, minY = 0, maxX = 0, maxY = 0
  let hasBounds = false

  // Get bounds from areas
  props.areas.forEach(area => {
    if (area.x !== undefined && area.y !== undefined) {
      const areaView = logicalRectToView({ x: area.x, y: area.y, width: area.width, height: area.height }, props.viewport)
      minX = hasBounds ? Math.min(minX, areaView.x) : areaView.x
      minY = hasBounds ? Math.min(minY, areaView.y) : areaView.y
      maxX = hasBounds ? Math.max(maxX, areaView.x + areaView.width) : areaView.x + areaView.width
      maxY = hasBounds ? Math.max(maxY, areaView.y + areaView.height) : areaView.y + areaView.height
      hasBounds = true
    }
  })

  // Get bounds from devices (if no areas)
  if (!hasBounds) {
    deviceViewMap.value.forEach(rect => {
      minX = hasBounds ? Math.min(minX, rect.x) : rect.x
      minY = hasBounds ? Math.min(minY, rect.y) : rect.y
      maxX = hasBounds ? Math.max(maxX, rect.x + rect.width) : rect.x + rect.width
      maxY = hasBounds ? Math.max(maxY, rect.y + rect.height) : rect.y + rect.height
      hasBounds = true
    })
  }

  // Clamp pan to keep diagram visible (allow 20% overflow)
  const MARGIN = 200  // Pixels of margin
  let newOffsetX = props.viewport.offsetX + dx
  let newOffsetY = props.viewport.offsetY + dy

  if (hasBounds && stageSize.value.width > 0 && stageSize.value.height > 0) {
    const diagramWidth = maxX - minX
    const diagramHeight = maxY - minY

    // Clamp X (allow panning until diagram edge is at margin distance from canvas edge)
    const maxOffsetX = MARGIN
    const minOffsetX = stageSize.value.width - diagramWidth - MARGIN
    newOffsetX = Math.max(minOffsetX, Math.min(maxOffsetX, newOffsetX))

    // Clamp Y
    const maxOffsetY = MARGIN
    const minOffsetY = stageSize.value.height - diagramHeight - MARGIN
    newOffsetY = Math.max(minOffsetY, Math.min(maxOffsetY, newOffsetY))
  }

  emit('update:viewport', {
    ...props.viewport,
    offsetX: newOffsetX,
    offsetY: newOffsetY
  })
}

function onPointerUp() {
  isPanning.value = false
  lastPointer.value = null
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
})

watch([visibleAreas, visibleDevices, visibleLinks, l2Labels, l3Labels, stageSize], () => {
  batchDraw()
})
</script>

<style scoped>
.canvas-shell {
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at 20% 20%, #fff7f2 0%, #ffffff 42%, #f6f1ea 100%);
  border-radius: 18px;
  border: 1px solid rgba(28, 28, 28, 0.08);
  box-shadow: var(--shadow);
  overflow: hidden;
}
</style>
