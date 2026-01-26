<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <h1>BSV Network Sketcher</h1>
        <p>Port từ Network Sketcher gốc</p>
      </div>
      <div class="status">
        <span>Backend</span>
        <strong :class="statusClass">{{ statusText }}</strong>
      </div>
    </header>

    <section class="workspace">
      <aside class="panel left">
        <h2>Danh mục</h2>
        <ul>
          <li>Areas: {{ areas.length }}</li>
          <li>Devices: {{ devices.length }}</li>
          <li>Links: {{ links.length }}</li>
        </ul>

        <div class="controls">
          <button type="button" @click="zoomIn">Zoom +</button>
          <button type="button" @click="zoomOut">Zoom -</button>
          <button type="button" @click="togglePan">
            {{ viewport.isPanning ? 'Tắt kéo' : 'Bật kéo' }}
          </button>
          <button type="button" class="ghost" @click="resetViewport">Reset view</button>
        </div>

        <button type="button" class="primary" @click="fetchHealth">Kiểm tra backend</button>
      </aside>

      <main class="canvas">
        <CanvasStage
          :areas="areas"
          :devices="devices"
          :links="links"
          :viewport="viewportState"
          :is-panning="viewport.isPanning"
          :selected-id="selectedId"
          @select="handleSelect"
          @update:viewport="updateViewport"
        />
      </main>

      <aside class="panel right">
        <div class="grid-tabs">
          <button type="button" :class="{ active: activeGrid === 'areas' }" @click="activeGrid = 'areas'">Areas</button>
          <button type="button" :class="{ active: activeGrid === 'devices' }" @click="activeGrid = 'devices'">Devices</button>
          <button type="button" :class="{ active: activeGrid === 'links' }" @click="activeGrid = 'links'">Links</button>
        </div>

        <DataGrid
          v-if="activeGrid === 'areas'"
          v-model:rows="areas"
          title="Grid: Areas"
          :columns="areaColumns"
          :default-row="areaDefaults"
        />
        <DataGrid
          v-else-if="activeGrid === 'devices'"
          v-model:rows="devices"
          title="Grid: Devices"
          :columns="deviceColumns"
          :default-row="deviceDefaults"
        />
        <DataGrid
          v-else
          v-model:rows="links"
          title="Grid: Links"
          :columns="linkColumns"
          :default-row="linkDefaults"
        />

        <div class="hint">Phase 7: Data grid nhập liệu</div>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import CanvasStage from './components/CanvasStage.vue'
import DataGrid, { type ColumnDef } from './components/DataGrid.vue'
import type { AreaModel, DeviceModel, LinkModel, Viewport } from './models/types'

const statusText = ref('đang kiểm tra...')
const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const viewport = reactive({
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  isPanning: false
})

const areas = ref<AreaModel[]>([
  {
    id: 'area-1',
    name: 'Core',
    x: 40,
    y: 40,
    width: 420,
    height: 260,
    fill: '#fff4ea',
    stroke: '#c9b8a5'
  },
  {
    id: 'area-2',
    name: 'Edge',
    x: 520,
    y: 80,
    width: 320,
    height: 200,
    fill: '#f3f0ff',
    stroke: '#b3a8d6'
  }
])

const devices = ref<DeviceModel[]>([
  {
    id: 'dev-1',
    areaId: 'area-1',
    name: 'Core-SW-1',
    x: 120,
    y: 120,
    width: 120,
    height: 56,
    type: 'Switch'
  },
  {
    id: 'dev-2',
    areaId: 'area-1',
    name: 'Core-SW-2',
    x: 260,
    y: 200,
    width: 120,
    height: 56,
    type: 'Switch'
  },
  {
    id: 'dev-3',
    areaId: 'area-2',
    name: 'Edge-RTR',
    x: 580,
    y: 140,
    width: 120,
    height: 56,
    type: 'Router'
  }
])

const links = ref<LinkModel[]>([
  {
    id: 'link-1',
    fromDeviceId: 'dev-1',
    toDeviceId: 'dev-2',
    fromPort: 'Gi 0/1',
    toPort: 'Gi 0/2',
    style: 'solid'
  },
  {
    id: 'link-2',
    fromDeviceId: 'dev-2',
    toDeviceId: 'dev-3',
    fromPort: 'Gi 0/3',
    toPort: 'Gi 0/4',
    style: 'dashed'
  }
])

const selectedId = ref<string | null>(null)
const activeGrid = ref<'areas' | 'devices' | 'links'>('areas')

const deviceTypes = ['Router', 'Switch', 'Firewall', 'Server', 'AP', 'PC', 'Storage', 'Unknown']

const areaColumns: ColumnDef[] = [
  { key: 'name', label: 'Tên' },
  { key: 'x', label: 'X', type: 'number', width: '72px' },
  { key: 'y', label: 'Y', type: 'number', width: '72px' },
  { key: 'width', label: 'W', type: 'number', width: '72px' },
  { key: 'height', label: 'H', type: 'number', width: '72px' }
]

const deviceColumns = computed<ColumnDef[]>(() => [
  { key: 'name', label: 'Thiết bị' },
  {
    key: 'areaId',
    label: 'Area',
    type: 'select',
    options: areas.value.map(area => ({ value: area.id, label: area.name }))
  },
  {
    key: 'type',
    label: 'Loại',
    type: 'select',
    options: deviceTypes.map(type => ({ value: type, label: type }))
  },
  { key: 'x', label: 'X', type: 'number', width: '72px' },
  { key: 'y', label: 'Y', type: 'number', width: '72px' }
])

const linkColumns = computed<ColumnDef[]>(() => {
  const deviceOptions = devices.value.map(device => ({ value: device.id, label: device.name }))
  return [
    { key: 'fromDeviceId', label: 'Từ thiết bị', type: 'select', options: deviceOptions },
    { key: 'fromPort', label: 'Cổng đi' },
    { key: 'toDeviceId', label: 'Đến thiết bị', type: 'select', options: deviceOptions },
    { key: 'toPort', label: 'Cổng đến' },
    {
      key: 'style',
      label: 'Style',
      type: 'select',
      options: [
        { value: 'solid', label: 'Solid' },
        { value: 'dashed', label: 'Dashed' },
        { value: 'dotted', label: 'Dotted' }
      ]
    }
  ]
})

const areaDefaults: AreaModel = {
  id: 'area-new',
  name: 'Area mới',
  x: 80,
  y: 80,
  width: 240,
  height: 160,
  fill: '#fff4ea',
  stroke: '#c9b8a5'
}

const deviceDefaults: DeviceModel = {
  id: 'dev-new',
  areaId: 'area-1',
  name: 'Device mới',
  x: 120,
  y: 120,
  width: 120,
  height: 56,
  type: 'Switch'
}

const linkDefaults: LinkModel = {
  id: 'link-new',
  fromDeviceId: 'dev-1',
  toDeviceId: 'dev-2',
  fromPort: 'Gi 0/1',
  toPort: 'Gi 0/2',
  style: 'solid'
}

const statusClass = computed(() => {
  if (statusText.value === 'healthy') return 'ok'
  if (statusText.value === 'không kết nối được') return 'error'
  if (statusText.value === 'lỗi kết nối') return 'error'
  return 'pending'
})

const viewportState = computed<Viewport>(() => ({
  scale: viewport.scale,
  offsetX: viewport.offsetX,
  offsetY: viewport.offsetY
}))

function updateViewport(value: Viewport) {
  viewport.offsetX = value.offsetX
  viewport.offsetY = value.offsetY
  viewport.scale = value.scale
}

function handleSelect(payload: { id: string }) {
  selectedId.value = payload.id
}

function zoomIn() {
  viewport.scale = Math.min(viewport.scale + 0.1, 2)
}

function zoomOut() {
  viewport.scale = Math.max(viewport.scale - 0.1, 0.5)
}

function resetViewport() {
  viewport.scale = 1
  viewport.offsetX = 0
  viewport.offsetY = 0
}

function togglePan() {
  viewport.isPanning = !viewport.isPanning
}

async function fetchHealth() {
  try {
    const res = await fetch(`${apiBase}/api/v1/health`)
    if (!res.ok) {
      statusText.value = 'lỗi kết nối'
      return
    }
    const data = await res.json()
    statusText.value = data.status ?? 'không xác định'
  } catch {
    statusText.value = 'không kết nối được'
  }
}

fetchHealth()
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 16px;
  padding: 20px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--panel);
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  padding: 18px 22px;
  box-shadow: var(--shadow);
}

.topbar h1 {
  font-family: 'Fraunces', serif;
  font-size: 24px;
  margin: 0;
}

.topbar p {
  margin: 6px 0 0;
  color: var(--muted);
}

.status {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status span {
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.status strong {
  font-size: 16px;
}

.status .ok {
  color: #1c7c54;
}

.status .error {
  color: #d64545;
}

.status .pending {
  color: #a26b1f;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(200px, 260px) 1fr minmax(320px, 380px);
  gap: 16px;
  min-height: 60vh;
}

.panel {
  background: var(--panel);
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  padding: 18px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel h2 {
  font-size: 16px;
  margin: 0;
}

.panel ul {
  margin: 0;
  padding: 0 0 0 18px;
  color: var(--muted);
}

.controls {
  display: grid;
  gap: 10px;
}

.controls button {
  border-radius: 12px;
  border: 1px solid transparent;
  padding: 10px 14px;
  cursor: pointer;
  background: #efe7df;
}

.controls .ghost {
  background: transparent;
  border-color: #dccfc4;
}

.panel .primary {
  margin-top: auto;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 10px 14px;
  cursor: pointer;
}

.canvas {
  min-height: 60vh;
}

.grid-tabs {
  display: flex;
  gap: 8px;
}

.grid-tabs button {
  flex: 1;
  border: 1px solid rgba(28, 28, 28, 0.12);
  background: transparent;
  border-radius: 10px;
  padding: 6px 8px;
  cursor: pointer;
  font-size: 12px;
}

.grid-tabs button.active {
  background: var(--accent-soft);
  border-color: rgba(214, 108, 59, 0.4);
}

.hint {
  margin-top: auto;
  padding: 10px 12px;
  background: var(--accent-soft);
  border-radius: 12px;
  font-size: 13px;
}

@media (max-width: 1024px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .panel.left,
  .panel.right {
    order: 2;
  }

  .canvas {
    order: 1;
    min-height: 50vh;
  }
}
</style>
