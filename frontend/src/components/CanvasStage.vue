<template>
  <div ref="containerRef" class="canvas-shell">
    <v-stage
      :config="{
        width: stageSize.width,
        height: stageSize.height,
        draggable: isPanning
      }"
      @dragend="onStageDragEnd"
    >
      <v-layer ref="gridLayerRef">
        <v-rect :config="gridConfig" />
      </v-layer>

      <v-layer ref="areaLayerRef">
        <v-group
          v-for="area in visibleAreas"
          :key="area.id"
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
  isPanning: boolean
  selectedId?: string | null
}>()

const emit = defineEmits<{
  (event: 'update:viewport', value: Viewport): void
  (event: 'select', payload: { id: string; type: 'device' | 'area' }): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const stageSize = ref({ width: 300, height: 200 })
let observer: ResizeObserver | null = null

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
  cornerRadius: 12
}))

const visibleBounds = computed(() => getVisibleBounds(stageSize.value, props.viewport))

const visibleAreas = computed(() => {
  const bounds = visibleBounds.value
  return props.areas
    .filter(area => {
      const withinX = area.x + area.width > bounds.left - 50 && area.x < bounds.right + 50
      const withinY = area.y + area.height > bounds.top - 50 && area.y < bounds.bottom + 50
      return withinX && withinY
    })
    .map(area => {
      const rect = logicalRectToView(area, props.viewport)
      return {
        id: area.id,
        rect: {
          ...rect,
          fill: area.fill,
          stroke: area.stroke,
          strokeWidth: 1.5,
          cornerRadius: 10
        },
        label: {
          x: rect.x + 12,
          y: rect.y + 10,
          text: area.name,
          fontSize: 14,
          fill: '#3f3a33'
        }
      }
    })
})

const deviceMap = computed(() => new Map(props.devices.map(device => [device.id, device])))

const visibleDevices = computed(() => {
  const bounds = visibleBounds.value
  return props.devices
    .filter(device => {
      const withinX = device.x + device.width > bounds.left - 40 && device.x < bounds.right + 40
      const withinY = device.y + device.height > bounds.top - 40 && device.y < bounds.bottom + 40
      return withinX && withinY
    })
    .map(device => {
      const rect = logicalRectToView(device, props.viewport)
      const isSelected = props.selectedId === device.id
      return {
        id: device.id,
        rect: {
          ...rect,
          fill: isSelected ? '#ffd9c8' : '#ffffff',
          stroke: isSelected ? '#d66c3b' : '#5f564f',
          strokeWidth: isSelected ? 2 : 1.2,
          cornerRadius: 8
        },
        label: {
          x: rect.x + 10,
          y: rect.y + 10,
          text: device.name,
          fontSize: 13,
          fill: '#302b27'
        }
      }
    })
})

const visibleLinks = computed(() => {
  const bounds = visibleBounds.value
  return props.links
    .map(link => {
      const from = deviceMap.value.get(link.fromDeviceId)
      const to = deviceMap.value.get(link.toDeviceId)
      if (!from || !to) return null
      const fromView = logicalRectToView(from, props.viewport)
      const toView = logicalRectToView(to, props.viewport)
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

function onStageDragEnd(event: any) {
  const node = event?.target
  if (!node) return
  emit('update:viewport', {
    ...props.viewport,
    offsetX: node.x(),
    offsetY: node.y()
  })
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
