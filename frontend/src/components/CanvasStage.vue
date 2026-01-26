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
    </v-stage>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { AreaModel, DeviceModel, LinkModel, Viewport } from '../models/types'
import { getVisibleBounds, logicalRectToView } from '../utils/viewport'

const props = defineProps<{ 
  areas: AreaModel[]
  devices: DeviceModel[]
  links: LinkModel[]
  viewport: Viewport
  selectedId?: string | null
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

const areaViewMap = computed(() => {
  const map = new Map<string, { x: number; y: number; width: number; height: number }>()
  props.areas.forEach(area => {
    const rect = logicalRectToView(area, props.viewport)
    map.set(area.id, rect)
  })
  return map
})

const visibleAreas = computed(() => {
  const bounds = visibleBounds.value
  return props.areas
    .filter(area => {
      const rect = areaViewMap.value.get(area.id)
      if (!rect) return false
      const withinX = rect.x + rect.width > bounds.left - 50 && rect.x < bounds.right + 50
      const withinY = rect.y + rect.height > bounds.top - 50 && rect.y < bounds.bottom + 50
      return withinX && withinY
    })
    .map(area => {
      const rect = areaViewMap.value.get(area.id)!
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
          strokeWidth: 1.5,
          cornerRadius: 10
        },
        label: {
          x: TEXT_PADDING,
          y: TEXT_PADDING - 2,
          width: Math.max(rect.width - TEXT_PADDING * 2, 0),
          text: area.name,
          fontSize: 14,
          fill: '#3f3a33',
          wrap: 'none',
          ellipsis: true
        }
      }
    })
})

const DEVICE_GAP = 12

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

const deviceViewMap = computed(() => {
  const map = new Map<string, { x: number; y: number; width: number; height: number }>()
  const devicesByArea = new Map<string, Array<{ device: DeviceModel; rect: { x: number; y: number; width: number; height: number } }>>()

  props.devices.forEach(device => {
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

    let hasOverlap = false
    for (let i = 0; i < entries.length; i += 1) {
      for (let j = i + 1; j < entries.length; j += 1) {
        if (rectsOverlap(entries[i].rect, entries[j].rect)) {
          hasOverlap = true
          break
        }
      }
      if (hasOverlap) break
    }

    if (hasOverlap) {
      const sorted = [...entries].sort((a, b) => a.device.name.localeCompare(b.device.name))
      const maxWidth = Math.max(...sorted.map(entry => entry.rect.width))
      const maxHeight = Math.max(...sorted.map(entry => entry.rect.height))
      const availableWidth = Math.max(area.width - AREA_PADDING * 2, maxWidth)
      const cellWidth = maxWidth + DEVICE_GAP
      const cellHeight = maxHeight + DEVICE_GAP
      const cols = Math.max(1, Math.floor((availableWidth + DEVICE_GAP) / cellWidth))

      sorted.forEach((entry, index) => {
        const col = index % cols
        const row = Math.floor(index / cols)
        const rect = { ...entry.rect }
        rect.x = area.x + AREA_PADDING + col * cellWidth
        rect.y = area.y + AREA_PADDING + row * cellHeight
        clampIntoArea(rect, area)
        map.set(entry.device.id, rect)
      })
    } else {
      entries.forEach(entry => {
        const rect = { ...entry.rect }
        clampIntoArea(rect, area)
        map.set(entry.device.id, rect)
      })
    }
  })

  return map
})

const visibleDevices = computed(() => {
  const bounds = visibleBounds.value
  return props.devices
    .filter(device => {
      const rect = deviceViewMap.value.get(device.id)
      if (!rect) return false
      const withinX = rect.x + rect.width > bounds.left - 40 && rect.x < bounds.right + 40
      const withinY = rect.y + rect.height > bounds.top - 40 && rect.y < bounds.bottom + 40
      return withinX && withinY
    })
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

const visibleLinks = computed(() => {
  const bounds = visibleBounds.value
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
      const minX = Math.min(fromCenter.x, toCenter.x)
      const maxX = Math.max(fromCenter.x, toCenter.x)
      const minY = Math.min(fromCenter.y, toCenter.y)
      const maxY = Math.max(fromCenter.y, toCenter.y)
      if (maxX < bounds.left - 80 || minX > bounds.right + 80) return null
      if (maxY < bounds.top - 80 || minY > bounds.bottom + 80) return null
      return {
        id: link.id,
        config: {
          points: [fromCenter.x, fromCenter.y, toCenter.x, toCenter.y],
          stroke: '#2b2a28',
          strokeWidth: 1.5,
          dash: link.style === 'dashed' ? [8, 6] : link.style === 'dotted' ? [2, 4] : [],
          opacity: 0.8
        }
      }
    })
    .filter(Boolean) as Array<{ id: string; config: Record<string, unknown> }>
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
  emit('update:viewport', {
    ...props.viewport,
    offsetX: props.viewport.offsetX + dx,
    offsetY: props.viewport.offsetY + dy
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

watch([visibleAreas, visibleDevices, visibleLinks, stageSize], () => {
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
