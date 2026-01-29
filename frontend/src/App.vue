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

    <section class="workspace" :class="{ 'right-collapsed': !showRightPanel }" :style="{ '--right-panel-width': `${rightPanelWidth}px` }">
      <aside class="panel left">
        <div class="section">
          <h2>Tài khoản</h2>
          <div v-if="!currentUser" class="stack">
            <input v-model="authForm.email" type="email" placeholder="Email" class="input" />
            <input v-model="authForm.password" type="password" placeholder="Mật khẩu" class="input" />
            <div class="row">
              <button type="button" class="primary" @click="handleLogin">Đăng nhập</button>
            </div>
            <p class="hint-text">Đăng ký tự do đã tắt. Vui lòng dùng tài khoản admin được cấp.</p>
          </div>
          <div v-else class="stack">
            <div class="user-chip">
              <span>{{ currentUser.display_name || currentUser.email }}</span>
              <button type="button" class="ghost" @click="handleLogout">Đăng xuất</button>
            </div>
          </div>
        </div>

        <div v-if="currentUser" class="section">
          <h2>Dự án</h2>
          <div class="stack">
            <select v-model="selectedProjectId" class="select">
              <option :value="null">-- Chọn project --</option>
              <option v-for="project in projects" :key="project.id" :value="project.id">
                {{ project.name }} ({{ project.layout_mode }})
              </option>
            </select>
            <select v-if="activeProject" v-model="layoutModeSelection" class="select">
              <option value="cisco">Cisco</option>
              <option value="iso">ISO</option>
              <option value="custom">Custom</option>
            </select>
            <div class="divider"></div>
            <input v-model="projectForm.name" type="text" placeholder="Tên project" class="input" />
            <select v-model="projectForm.layoutMode" class="select">
              <option value="cisco">Cisco</option>
              <option value="iso">ISO</option>
              <option value="custom">Custom</option>
            </select>
            <input v-model="projectForm.description" type="text" placeholder="Mô tả (tuỳ chọn)" class="input" />
            <button type="button" class="primary" @click="handleCreateProject">Tạo project</button>
          </div>
        </div>

        <div v-if="activeProject" class="section">
          <h2>Thống kê</h2>
          <ul>
            <li>Areas: {{ areas.length }}</li>
            <li>Devices: {{ devices.length }}</li>
            <li>Links: {{ links.length }}</li>
          </ul>
        </div>

        <div class="section">
          <h2>Trạng thái</h2>
          <button type="button" class="primary" @click="fetchHealth">Kiểm tra backend</button>
        </div>

        <p v-if="notice" :class="['notice', noticeType]">{{ notice }}</p>
      </aside>

      <main class="canvas">
        <div class="canvas-toolbar">
          <button type="button" @click="zoomIn">Zoom +</button>
          <button type="button" @click="zoomOut">Zoom -</button>
          <button type="button" class="ghost" @click="resetViewport">Reset view</button>
          <span class="toolbar-divider"></span>
          <button type="button" :class="{ active: viewMode === 'L1' }" @click="setViewMode('L1')">L1</button>
          <button type="button" :class="{ active: viewMode === 'L2' }" @click="setViewMode('L2')">L2</button>
          <button type="button" :class="{ active: viewMode === 'L3' }" @click="setViewMode('L3')">L3</button>
          <button type="button" :class="{ active: viewMode === 'overview' }" @click="setViewMode('overview')">Tổng quan</button>
          <span class="toolbar-divider"></span>
          <button type="button" class="primary" @click="showAutoLayoutDialog = true" :disabled="!activeProject">
            Auto Layout
          </button>
          <span class="toolbar-divider"></span>
          <button type="button" class="ghost" @click="toggleRightPanel">
            {{ showRightPanel ? 'Ẩn panel' : 'Hiện panel' }}
          </button>
        </div>
        <CanvasStage
          :areas="canvasAreas"
          :devices="canvasDevices"
          :links="canvasLinks"
          :viewport="viewportState"
          :layout-mode="layoutMode"
          :selected-id="selectedId"
          :view-mode="viewMode"
          :l2-assignments="l2Assignments"
          :l3-addresses="l3Addresses"
          :auto-layout-coords="autoLayoutCoordsMap"
          :vlan-groups="vlanGroupsFromLayout"
          :subnet-groups="subnetGroupsFromLayout"
          @select="handleSelect"
          @update:viewport="updateViewport"
        />
      </main>

      <aside v-show="showRightPanel" class="panel right">
        <div class="grid-tabs">
          <button type="button" :class="{ active: activeGrid === 'areas' }" @click="activeGrid = 'areas'">Areas</button>
          <button type="button" :class="{ active: activeGrid === 'devices' }" @click="activeGrid = 'devices'">Devices</button>
          <button type="button" :class="{ active: activeGrid === 'links' }" @click="activeGrid = 'links'">Links</button>
          <button type="button" class="ghost" @click="togglePanelMode">
            {{ panelMode === 'selection' ? 'Chỉ chọn' : 'Xem tất cả' }}
          </button>
          <label class="panel-size">
            <span>Rộng</span>
            <input type="range" min="280" max="520" step="20" v-model.number="rightPanelWidth" />
          </label>
        </div>

        <div v-if="panelMode === 'selection' && !selectedRowForActiveGrid" class="panel-hint">
          Chọn một đối tượng trên canvas để xem chi tiết.
        </div>

        <DataGrid
          v-if="activeGrid === 'areas'"
          :rows="areaRowsView"
          :show-add="panelMode === 'all'"
          title="Grid: Areas"
          :columns="areaColumns"
          :default-row="areaDefaults"
          @update:rows="handleAreaRowsUpdate"
          @row:add="handleAreaAdd"
          @row:change="handleAreaChange"
          @row:remove="handleAreaRemove"
        />
        <DataGrid
          v-else-if="activeGrid === 'devices'"
          :rows="deviceRowsView"
          :show-add="panelMode === 'all'"
          title="Grid: Devices"
          :columns="deviceColumns"
          :default-row="deviceDefaults"
          @update:rows="handleDeviceRowsUpdate"
          @row:add="handleDeviceAdd"
          @row:change="handleDeviceChange"
          @row:remove="handleDeviceRemove"
        />
        <DataGrid
          v-else
          :rows="linkRowsView"
          :show-add="panelMode === 'all'"
          title="Grid: Links"
          :columns="linkColumns"
          :default-row="linkDefaults"
          @update:rows="handleLinkRowsUpdate"
          @row:add="handleLinkAdd"
          @row:change="handleLinkChange"
          @row:remove="handleLinkRemove"
        />

        <div class="hint">
          {{ activeProject ? 'Phase 7: Data grid nhập liệu (đã nối API)' : 'Cần đăng nhập và chọn project' }}
        </div>
      </aside>
    </section>

    <!-- Auto Layout Dialog -->
    <div v-if="showAutoLayoutDialog" class="dialog-overlay" @click.self="showAutoLayoutDialog = false">
      <div class="dialog-box">
        <div class="dialog-header">
          <h2>Auto Layout (Topology-Aware)</h2>
          <button type="button" class="ghost-close" @click="showAutoLayoutDialog = false">✕</button>
        </div>

        <div class="dialog-body">
          <div class="form-section">
            <label>Phạm vi bố cục</label>
            <select v-model="autoLayoutOptions.layout_scope" class="select">
              <option value="area">Trong Area (khuyến nghị)</option>
              <option value="project">Toàn dự án (xếp lại Area)</option>
            </select>
            <p class="hint-text">Thiết bị trong Area luôn top‑to‑bottom theo NS gốc.</p>
          </div>

          <div class="form-section">
            <label>Layer Gap ({{ autoLayoutOptions.layer_gap.toFixed(1) }} inches)</label>
            <input
              type="range"
              min="0.5"
              max="5.0"
              step="0.1"
              v-model.number="autoLayoutOptions.layer_gap"
              class="slider"
            />
          </div>

          <div class="form-section">
            <label>Node Spacing ({{ autoLayoutOptions.node_spacing.toFixed(1) }} inches)</label>
            <input
              type="range"
              min="0.2"
              max="2.0"
              step="0.1"
              v-model.number="autoLayoutOptions.node_spacing"
              class="slider"
            />
          </div>

          <div v-if="autoLayoutResult" class="layout-stats">
            <h3>Layout Statistics</h3>
            <ul>
              <li>Total Layers: {{ autoLayoutResult.stats.total_layers }}</li>
              <li>Edge Crossings: {{ autoLayoutResult.stats.total_crossings }}</li>
              <li>Execution Time: {{ autoLayoutResult.stats.execution_time_ms }}ms</li>
              <li>Algorithm: {{ autoLayoutResult.stats.algorithm }}</li>
              <li>Devices Positioned: {{ autoLayoutResult.devices.length }}</li>
            </ul>
          </div>
        </div>

        <div class="dialog-footer">
          <button
            type="button"
            class="primary"
            @click="handleAutoLayoutPreview"
            :disabled="!activeProject || autoLayoutLoading"
          >
            {{ autoLayoutLoading ? 'Computing...' : 'Preview Layout' }}
          </button>
          <button
            type="button"
            class="primary"
            @click="handleAutoLayoutApply"
            :disabled="!activeProject || !autoLayoutResult || autoLayoutLoading"
          >
            Apply to Database
          </button>
          <button type="button" class="ghost" @click="showAutoLayoutDialog = false">
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import CanvasStage from './components/CanvasStage.vue'
import DataGrid, { type ColumnDef } from './components/DataGrid.vue'
import type { AreaModel, DeviceModel, LinkModel, Viewport } from './models/types'
import type { AreaRecord, AreaStyle, DeviceRecord, LinkRecord, ProjectRecord, UserRecord } from './models/api'
import { getMe, loginUser, logout as logoutUser } from './services/auth'
import { listProjects, createProject, updateProject } from './services/projects'
import { listAreas, createArea, updateArea, deleteArea } from './services/areas'
import { listDevices, createDevice, updateDevice, deleteDevice } from './services/devices'
import { listLinks, createLink, updateLink, deleteLink } from './services/links'
import { getToken } from './services/api'
import { autoLayout, invalidateLayoutCache } from './services/layout'
import type { LayoutResult } from './services/layout'

const UNIT_PX = 120
const GRID_FALLBACK_X = 4
const GRID_FALLBACK_Y = 2.5

const statusText = ref('đang kiểm tra...')
const notice = ref('')
const noticeType = ref<'info' | 'success' | 'error'>('info')

const authForm = reactive({
  email: '',
  password: ''
})
const currentUser = ref<UserRecord | null>(null)

const projects = ref<ProjectRecord[]>([])
const selectedProjectId = ref<string | null>(null)
const projectForm = reactive({
  name: '',
  description: '',
  layoutMode: 'cisco' as 'cisco' | 'iso' | 'custom'
})

type AreaRow = AreaRecord & { __temp?: boolean }
type DeviceRow = DeviceRecord & { __temp?: boolean }
type LinkRow = LinkRecord & { __temp?: boolean }

const areas = ref<AreaRow[]>([])
const devices = ref<DeviceRow[]>([])
const links = ref<LinkRow[]>([])

const selectedId = ref<string | null>(null)
const activeGrid = ref<'areas' | 'devices' | 'links'>('areas')

const viewport = reactive({
  scale: 1,
  offsetX: 0,
  offsetY: 0
})

const showRightPanel = ref(true)
const rightPanelWidth = ref(360)

const layoutMode = computed(() => activeProject.value?.layout_mode || 'cisco')
const layoutModeSelection = ref<'cisco' | 'iso' | 'custom'>('cisco')
const layoutModeUpdating = ref(false)

const panelMode = ref<'selection' | 'all'>('all')

function togglePanelMode() {
  panelMode.value = panelMode.value === 'selection' ? 'all' : 'selection'
}

// View mode for canvas (L1/L2/L3/Overview)
type ViewMode = 'L1' | 'L2' | 'L3' | 'overview'
const viewMode = ref<ViewMode>('L1')

// L2/L3 data
type L2AssignmentRecord = {
  id: string
  device_id: string
  device_name?: string | null
  interface_name: string
  vlan_id?: number | null
  port_mode: 'access' | 'trunk'
}

type L3AddressRecord = {
  id: string
  device_id: string
  device_name?: string | null
  interface_name: string
  ip_address: string
  prefix_length: number
}

const l2Assignments = ref<L2AssignmentRecord[]>([])
const l3Addresses = ref<L3AddressRecord[]>([])
const l2Loaded = ref(false)
const l3Loaded = ref(false)

// Auto Layout state
const showAutoLayoutDialog = ref(false)
const autoLayoutOptions = reactive({
  layer_gap: 1.0,
  node_spacing: 0.5,
  layout_scope: 'project' as 'area' | 'project'
})
const autoLayoutResult = ref<LayoutResult | null>(null)
const autoLayoutLoading = ref(false)
const autoLayoutAutoApplying = ref(false)
const autoLayoutAutoAppliedProjects = new Set<string>()
let autoLayoutTimer: number | null = null

const selectedRowForActiveGrid = computed(() => {
  if (!selectedId.value) return null
  if (activeGrid.value === 'areas') {
    return areas.value.find(a => a.id === selectedId.value) || null
  }
  if (activeGrid.value === 'devices') {
    return devices.value.find(d => d.id === selectedId.value) || null
  }
  if (activeGrid.value === 'links') {
    return links.value.find(l => l.id === selectedId.value) || null
  }
  return null
})

const areaRowsView = computed(() => {
  if (panelMode.value === 'all') return areas.value
  if (!selectedId.value) return []
  const found = areas.value.find(a => a.id === selectedId.value)
  return found ? [found] : []
})

const deviceRowsView = computed(() => {
  if (panelMode.value === 'all') return devices.value
  if (!selectedId.value) return []
  const found = devices.value.find(d => d.id === selectedId.value)
  return found ? [found] : []
})

const linkRowsView = computed(() => {
  if (panelMode.value === 'all') return links.value
  if (!selectedId.value) return []
  const found = links.value.find(l => l.id === selectedId.value)
  return found ? [found] : []
})

function handleAreaRowsUpdate(rows: AreaRow[]) {
  if (panelMode.value === 'all') {
    areas.value = rows
  }
}

function handleDeviceRowsUpdate(rows: DeviceRow[]) {
  if (panelMode.value === 'all') {
    devices.value = rows
  }
}

function handleLinkRowsUpdate(rows: LinkRow[]) {
  if (panelMode.value === 'all') {
    links.value = rows
  }
}

const deviceTypes = ['Router', 'Switch', 'Firewall', 'Server', 'AP', 'PC', 'Storage', 'Unknown']
const linkPurposes = ['DEFAULT', 'WAN', 'INTERNET', 'DMZ', 'LAN', 'MGMT', 'HA', 'STORAGE', 'BACKUP', 'VPN']

const defaultAreaStyle: AreaStyle = {
  fill_color_rgb: [240, 240, 240],
  stroke_color_rgb: [51, 51, 51],
  stroke_width: 1
}

const areaColumns: ColumnDef[] = [
  { key: 'name', label: 'Tên' },
  { key: 'grid_row', label: 'Grid R', type: 'number', width: '72px' },
  { key: 'grid_col', label: 'Grid C', type: 'number', width: '72px' },
  { key: 'position_x', label: 'X (đv)', type: 'number', width: '80px' },
  { key: 'position_y', label: 'Y (đv)', type: 'number', width: '80px' },
  { key: 'width', label: 'W (đv)', type: 'number', width: '72px' },
  { key: 'height', label: 'H (đv)', type: 'number', width: '72px' }
]

const deviceColumns = computed<ColumnDef[]>(() => [
  { key: 'name', label: 'Thiết bị' },
  {
    key: 'area_name',
    label: 'Area',
    type: 'select',
    options: areas.value.map(area => ({ value: area.name, label: area.name }))
  },
  {
    key: 'device_type',
    label: 'Loại',
    type: 'select',
    options: deviceTypes.map(type => ({ value: type, label: type }))
  },
  { key: 'position_x', label: 'X (đv)', type: 'number', width: '80px' },
  { key: 'position_y', label: 'Y (đv)', type: 'number', width: '80px' },
  { key: 'width', label: 'W (đv)', type: 'number', width: '72px' },
  { key: 'height', label: 'H (đv)', type: 'number', width: '72px' }
])

const linkColumns = computed<ColumnDef[]>(() => {
  const deviceOptions = devices.value.map(device => ({ value: device.name, label: device.name }))
  return [
    { key: 'from_device_name', label: 'Từ thiết bị', type: 'select', options: deviceOptions },
    { key: 'from_port', label: 'Cổng đi' },
    { key: 'to_device_name', label: 'Đến thiết bị', type: 'select', options: deviceOptions },
    { key: 'to_port', label: 'Cổng đến' },
    {
      key: 'line_style',
      label: 'Style',
      type: 'select',
      options: [
        { value: 'solid', label: 'Solid' },
        { value: 'dashed', label: 'Dashed' },
        { value: 'dotted', label: 'Dotted' }
      ]
    },
    {
      key: 'purpose',
      label: 'Mục đích',
      type: 'select',
      options: linkPurposes.map(purpose => ({ value: purpose, label: purpose }))
    }
  ]
})

const areaDefaults: AreaRow = {
  id: 'area-temp',
  project_id: '',
  name: 'Area mới',
  grid_row: 1,
  grid_col: 1,
  position_x: 1,
  position_y: 1,
  width: 3,
  height: 1.5,
  style: defaultAreaStyle,
  __temp: true
}

const deviceDefaults: DeviceRow = {
  id: 'device-temp',
  project_id: '',
  name: 'Device mới',
  area_id: '',
  area_name: '',
  device_type: 'Switch',
  position_x: 1,
  position_y: 1,
  width: 1.2,
  height: 0.5,
  color_rgb: null,
  __temp: true
}

const linkDefaults: LinkRow = {
  id: 'link-temp',
  project_id: '',
  from_device_id: '',
  from_device_name: '',
  from_port: 'Gi 0/1',
  to_device_id: '',
  to_device_name: '',
  to_port: 'Gi 0/2',
  purpose: 'DEFAULT',
  line_style: 'solid',
  color_rgb: null,
  __temp: true
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

const activeProject = computed(() => projects.value.find(p => p.id === selectedProjectId.value) || null)

const canvasAreas = computed<AreaModel[]>(() => {
  return areas.value.map(area => {
    const style = area.style || defaultAreaStyle
    const preview = autoLayoutAreaMap.value?.get(area.id)
    const xUnits = preview?.x ?? area.position_x ?? (area.grid_col - 1) * GRID_FALLBACK_X
    const yUnits = preview?.y ?? area.position_y ?? (area.grid_row - 1) * GRID_FALLBACK_Y
    const widthUnits = preview?.width ?? (area.width || 3)
    const heightUnits = preview?.height ?? (area.height || 1.5)
    return {
      id: area.id,
      name: area.name,
      x: xUnits * UNIT_PX,
      y: yUnits * UNIT_PX,
      width: widthUnits * UNIT_PX,
      height: heightUnits * UNIT_PX,
      fill: rgbToHex(style.fill_color_rgb),
      stroke: rgbToHex(style.stroke_color_rgb)
    }
  })
})

const canvasDevices = computed<DeviceModel[]>(() => {
  return devices.value.map(device => {
    const xUnits = device.position_x ?? 0
    const yUnits = device.position_y ?? 0
    return {
      id: device.id,
      areaId: device.area_id,
      name: device.name,
      x: xUnits * UNIT_PX,
      y: yUnits * UNIT_PX,
      width: (device.width || 1.2) * UNIT_PX,
      height: (device.height || 0.5) * UNIT_PX,
      type: device.device_type || 'Unknown'
    }
  })
})

const canvasLinks = computed<LinkModel[]>(() => {
  const byName = new Map(devices.value.map(device => [device.name, device]))
  const byId = new Map(devices.value.map(device => [device.id, device]))
  return links.value
    .map(link => {
      const from = link.from_device_name ? byName.get(link.from_device_name) : byId.get(link.from_device_id)
      const to = link.to_device_name ? byName.get(link.to_device_name) : byId.get(link.to_device_id)
      if (!from || !to) return null
      return {
        id: link.id,
        fromDeviceId: from.id,
        toDeviceId: to.id,
        fromPort: link.from_port,
        toPort: link.to_port,
        style: (link.line_style || 'solid') as 'solid' | 'dashed' | 'dotted'
      }
    })
    .filter(Boolean) as LinkModel[]
})

const autoLayoutCoordsMap = computed(() => {
  if (!autoLayoutResult.value) return undefined
  const map = new Map<string, { x: number; y: number }>()
  autoLayoutResult.value.devices.forEach(device => {
    map.set(device.id, { x: device.x, y: device.y })
  })
  return map
})

const autoLayoutAreaMap = computed(() => {
  if (!autoLayoutResult.value?.areas) return undefined
  const map = new Map<string, { x: number; y: number; width: number; height: number }>()
  autoLayoutResult.value.areas.forEach(area => {
    map.set(area.id, { x: area.x, y: area.y, width: area.width, height: area.height })
  })
  return map
})

const vlanGroupsFromLayout = computed(() => {
  return autoLayoutResult.value?.vlan_groups || []
})

const subnetGroupsFromLayout = computed(() => {
  return autoLayoutResult.value?.subnet_groups || []
})

function rgbToHex(rgb: [number, number, number]) {
  return `#${rgb.map(value => value.toString(16).padStart(2, '0')).join('')}`
}

function updateViewport(value: Viewport) {
  viewport.offsetX = value.offsetX
  viewport.offsetY = value.offsetY
  viewport.scale = value.scale
}

function handleSelect(payload: { id: string; type?: 'device' | 'area' }) {
  selectedId.value = payload.id

  // Auto-switch to relevant tab when selecting an object
  if (panelMode.value === 'selection' && payload.id) {
    if (payload.type === 'device') {
      activeGrid.value = 'devices'
    } else if (payload.type === 'area') {
      activeGrid.value = 'areas'
    } else {
      // Infer type from data
      const isArea = areas.value.some(a => a.id === payload.id)
      const isDevice = devices.value.some(d => d.id === payload.id)
      const isLink = links.value.some(l => l.id === payload.id)

      if (isArea) {
        activeGrid.value = 'areas'
      } else if (isDevice) {
        activeGrid.value = 'devices'
      } else if (isLink) {
        activeGrid.value = 'links'
      }
    }
  }
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

function toggleRightPanel() {
  showRightPanel.value = !showRightPanel.value
}

async function setViewMode(mode: ViewMode) {
  viewMode.value = mode
  if (!selectedProjectId.value) return

  // Lazy load L2 data
  if (mode === 'L2' && !l2Loaded.value) {
    await fetchL2Data()
  }
  // Lazy load L3 data
  if (mode === 'L3' && !l3Loaded.value) {
    await fetchL3Data()
  }
}

async function fetchL2Data() {
  if (!selectedProjectId.value) return
  try {
    const res = await fetch(
      `${import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'}/api/v1/projects/${selectedProjectId.value}/l2/assignments`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
    if (res.ok) {
      l2Assignments.value = await res.json()
      l2Loaded.value = true
      console.log('L2 data loaded:', l2Assignments.value.length, 'assignments')
    } else {
      console.error('L2 fetch failed:', res.status, res.statusText)
    }
  } catch (e) {
    console.error('Failed to fetch L2 assignments:', e)
  }
}

async function fetchL3Data() {
  if (!selectedProjectId.value) return
  try {
    const res = await fetch(
      `${import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'}/api/v1/projects/${selectedProjectId.value}/l3/addresses`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
    if (res.ok) {
      l3Addresses.value = await res.json()
      l3Loaded.value = true
      console.log('L3 data loaded:', l3Addresses.value.length, 'addresses')
    } else {
      console.error('L3 fetch failed:', res.status, res.statusText)
    }
  } catch (e) {
    console.error('Failed to fetch L3 addresses:', e)
  }
}

function setNotice(message: string, type: 'info' | 'success' | 'error' = 'info') {
  notice.value = message
  noticeType.value = type
}

async function fetchHealth() {
  try {
    const res = await fetch(`${import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'}/api/v1/health`)
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

async function initAuth() {
  const token = getToken()
  if (!token) return
  try {
    currentUser.value = await getMe()
    await loadProjects()
  } catch (error) {
    logoutUser()
    currentUser.value = null
    setNotice('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error')
  }
}

async function handleLogin() {
  if (!authForm.email || !authForm.password) {
    setNotice('Vui lòng nhập email và mật khẩu.', 'error')
    return
  }
  try {
    await loginUser({ email: authForm.email, password: authForm.password })
    currentUser.value = await getMe()
    await loadProjects()
    setNotice('Đăng nhập thành công.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Đăng nhập thất bại.', 'error')
  }
}

function handleLogout() {
  logoutUser()
  currentUser.value = null
  projects.value = []
  selectedProjectId.value = null
  areas.value = []
  devices.value = []
  links.value = []
}

async function loadProjects() {
  try {
    projects.value = await listProjects()
    if (!selectedProjectId.value && projects.value.length > 0) {
      selectedProjectId.value = projects.value[0].id
    }
  } catch (error: any) {
    setNotice(error?.message || 'Không tải được danh sách project.', 'error')
  }
}

async function handleCreateProject() {
  if (!projectForm.name) {
    setNotice('Tên project không được để trống.', 'error')
    return
  }
  try {
    const created = await createProject({
      name: projectForm.name,
      description: projectForm.description || undefined,
      layout_mode: projectForm.layoutMode
    })
    projects.value = [created, ...projects.value]
    selectedProjectId.value = created.id
    projectForm.name = ''
    projectForm.description = ''
    setNotice('Đã tạo project.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Tạo project thất bại.', 'error')
  }
}

async function loadProjectData(projectId: string) {
  try {
    const [areasData, devicesData, linksData] = await Promise.all([
      listAreas(projectId),
      listDevices(projectId),
      listLinks(projectId)
    ])
    areas.value = areasData
    devices.value = devicesData
    links.value = linksData
  } catch (error: any) {
    setNotice(error?.message || 'Không tải được dữ liệu project.', 'error')
  }
}

const areaUpdateTimers = new Map<string, number>()
const deviceUpdateTimers = new Map<string, number>()
const linkUpdateTimers = new Map<string, number>()

function scheduleUpdate(map: Map<string, number>, key: string, handler: () => void) {
  const existing = map.get(key)
  if (existing) window.clearTimeout(existing)
  const timer = window.setTimeout(() => {
    map.delete(key)
    handler()
  }, 600)
  map.set(key, timer)
}

async function handleAreaAdd(row: AreaRow) {
  if (!selectedProjectId.value) {
    setNotice('Vui lòng chọn project trước.', 'error')
    return
  }
  const projectId = selectedProjectId.value
  try {
    const created = await createArea(projectId, {
      name: row.name,
      grid_row: row.grid_row,
      grid_col: row.grid_col,
      position_x: row.position_x,
      position_y: row.position_y,
      width: row.width,
      height: row.height,
      style: row.style || defaultAreaStyle
    })
    const index = areas.value.findIndex(area => area.id === row.id)
    if (index >= 0) areas.value[index] = created
    scheduleAutoLayout(projectId, true)
  } catch (error: any) {
    setNotice(error?.message || 'Tạo area thất bại.', 'error')
  }
}

function handleAreaChange(payload: { row: AreaRow }) {
  if (!selectedProjectId.value) return
  const projectId = selectedProjectId.value
  if (payload.row.__temp) return
  scheduleUpdate(areaUpdateTimers, payload.row.id, async () => {
    try {
      const updated = await updateArea(projectId as string, payload.row.id, {
        name: payload.row.name,
        grid_row: payload.row.grid_row,
        grid_col: payload.row.grid_col,
        position_x: payload.row.position_x,
        position_y: payload.row.position_y,
        width: payload.row.width,
        height: payload.row.height,
        style: payload.row.style || undefined
      })
      const index = areas.value.findIndex(area => area.id === payload.row.id)
      if (index >= 0) areas.value[index] = updated
      scheduleAutoLayout(projectId, true)
    } catch (error: any) {
      setNotice(error?.message || 'Cập nhật area thất bại.', 'error')
    }
  })
}

async function handleAreaRemove(row: AreaRow) {
  if (!selectedProjectId.value) return
  const projectId = selectedProjectId.value
  if (row.__temp) return
  try {
    await deleteArea(projectId, row.id)
    scheduleAutoLayout(projectId, true)
  } catch (error: any) {
    setNotice(error?.message || 'Xóa area thất bại.', 'error')
  }
}

async function handleDeviceAdd(row: DeviceRow) {
  if (!selectedProjectId.value) {
    setNotice('Vui lòng chọn project trước.', 'error')
    return
  }
  const projectId = selectedProjectId.value
  if (!row.area_name) {
    setNotice('Cần chọn area cho device.', 'error')
    return
  }
  try {
    const created = await createDevice(projectId, {
      name: row.name,
      area_name: row.area_name,
      device_type: row.device_type,
      position_x: row.position_x,
      position_y: row.position_y,
      width: row.width,
      height: row.height,
      color_rgb: row.color_rgb || undefined
    })
    const index = devices.value.findIndex(device => device.id === row.id)
    if (index >= 0) devices.value[index] = created
    scheduleAutoLayout(projectId, true)
  } catch (error: any) {
    setNotice(error?.message || 'Tạo device thất bại.', 'error')
  }
}

function handleDeviceChange(payload: { row: DeviceRow }) {
  if (!selectedProjectId.value) return
  const projectId = selectedProjectId.value
  if (payload.row.__temp) return
  scheduleUpdate(deviceUpdateTimers, payload.row.id, async () => {
    try {
      const updated = await updateDevice(projectId as string, payload.row.id, {
        name: payload.row.name,
        area_name: payload.row.area_name || undefined,
        device_type: payload.row.device_type,
        position_x: payload.row.position_x,
        position_y: payload.row.position_y,
        width: payload.row.width,
        height: payload.row.height,
        color_rgb: payload.row.color_rgb || undefined
      })
      const index = devices.value.findIndex(device => device.id === payload.row.id)
      if (index >= 0) devices.value[index] = updated
      scheduleAutoLayout(projectId, true)
    } catch (error: any) {
      setNotice(error?.message || 'Cập nhật device thất bại.', 'error')
    }
  })
}

async function handleDeviceRemove(row: DeviceRow) {
  if (!selectedProjectId.value) return
  const projectId = selectedProjectId.value
  if (row.__temp) return
  try {
    await deleteDevice(projectId, row.id)
    scheduleAutoLayout(projectId, true)
  } catch (error: any) {
    setNotice(error?.message || 'Xóa device thất bại.', 'error')
  }
}

async function handleLinkAdd(row: LinkRow) {
  if (!selectedProjectId.value) {
    setNotice('Vui lòng chọn project trước.', 'error')
    return
  }
  const projectId = selectedProjectId.value
  if (!row.from_device_name || !row.to_device_name) {
    setNotice('Cần chọn thiết bị đầu/cuối cho link.', 'error')
    return
  }
  try {
    const created = await createLink(projectId, {
      from_device: row.from_device_name,
      from_port: row.from_port,
      to_device: row.to_device_name,
      to_port: row.to_port,
      purpose: row.purpose || undefined,
      line_style: row.line_style || 'solid'
    })
    const index = links.value.findIndex(link => link.id === row.id)
    if (index >= 0) links.value[index] = created
    scheduleAutoLayout(projectId, true)
  } catch (error: any) {
    setNotice(error?.message || 'Tạo link thất bại.', 'error')
  }
}

function handleLinkChange(payload: { row: LinkRow }) {
  if (!selectedProjectId.value) return
  const projectId = selectedProjectId.value
  if (payload.row.__temp) return
  scheduleUpdate(linkUpdateTimers, payload.row.id, async () => {
    try {
      const updated = await updateLink(projectId as string, payload.row.id, {
        from_device: payload.row.from_device_name || undefined,
        from_port: payload.row.from_port,
        to_device: payload.row.to_device_name || undefined,
        to_port: payload.row.to_port,
        purpose: payload.row.purpose || undefined,
        line_style: payload.row.line_style || undefined
      })
      const index = links.value.findIndex(link => link.id === payload.row.id)
      if (index >= 0) links.value[index] = updated
      scheduleAutoLayout(projectId, true)
    } catch (error: any) {
      setNotice(error?.message || 'Cập nhật link thất bại.', 'error')
    }
  })
}

async function handleLinkRemove(row: LinkRow) {
  if (!selectedProjectId.value) return
  const projectId = selectedProjectId.value
  if (row.__temp) return
  try {
    await deleteLink(projectId, row.id)
    scheduleAutoLayout(projectId, true)
  } catch (error: any) {
    setNotice(error?.message || 'Xóa link thất bại.', 'error')
  }
}

watch(selectedProjectId, async (projectId) => {
  // Reset L2/L3 loaded flags when project changes
  l2Loaded.value = false
  l3Loaded.value = false
  l2Assignments.value = []
  l3Addresses.value = []
  viewMode.value = 'L1'

  if (projectId) {
    await loadProjectData(projectId)
    const project = projects.value.find(item => item.id === projectId)
    if (project) {
      layoutModeSelection.value = project.layout_mode
    }
    autoLayoutResult.value = null
    scheduleAutoLayout(projectId)
  } else {
    areas.value = []
    devices.value = []
    links.value = []
    autoLayoutResult.value = null
  }
})

watch(layoutModeSelection, async (value) => {
  if (!activeProject.value) return
  if (layoutModeUpdating.value) return
  if (activeProject.value.layout_mode === value) return
  layoutModeUpdating.value = true
  try {
    const updated = await updateProject(activeProject.value.id, { layout_mode: value })
    projects.value = projects.value.map(project => (project.id === updated.id ? updated : project))
    setNotice('Đã cập nhật layout mode.', 'success')
    scheduleAutoLayout(updated.id, true)
  } catch (error: any) {
    setNotice(error?.message || 'Cập nhật layout mode thất bại.', 'error')
    layoutModeSelection.value = activeProject.value.layout_mode
  } finally {
    layoutModeUpdating.value = false
  }
})

function computeAutoLayoutTuning() {
  const deviceCount = devices.value.length
  const density = Math.min(1, Math.max(0, (deviceCount - 20) / 60))
  // Layout luôn top-to-bottom, auto-tune layer_gap dựa trên density
  const layer_gap = Number((0.8 + density * 1.0).toFixed(2))  // 0.8-1.8 inches
  const node_spacing = Number((0.45 + density * 0.25).toFixed(2))  // 0.45-0.7 inches
  return { layer_gap, node_spacing }
}

function scheduleAutoLayout(projectId: string, force = false) {
  if (autoLayoutTimer) window.clearTimeout(autoLayoutTimer)
  autoLayoutTimer = window.setTimeout(() => {
    autoLayoutTimer = null
    runAutoLayoutAuto(projectId, force)
  }, 800)
}

async function runAutoLayoutAuto(projectId: string, force = false) {
  if (autoLayoutAutoApplying.value) return
  if (!force && autoLayoutAutoAppliedProjects.has(projectId)) return
  if (!devices.value.length) return

  const hasAreas = areas.value.length > 0
  if (!hasAreas && !links.value.length) return

  autoLayoutAutoApplying.value = true
  try {
    const tuning = computeAutoLayoutTuning()
    await autoLayout(projectId, {
      layer_gap: tuning.layer_gap,
      node_spacing: tuning.node_spacing,
      apply_to_db: true,
      group_by_area: hasAreas,
      layout_scope: 'project',
      anchor_routing: true,
      overview_mode: 'l1-only'
    })
    autoLayoutAutoAppliedProjects.add(projectId)
    await loadProjectData(projectId)
    await invalidateLayoutCache(projectId)
    setNotice('Auto-layout đã được áp dụng tự động.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Auto-layout tự động thất bại.', 'error')
  } finally {
    autoLayoutAutoApplying.value = false
  }
}

async function handleAutoLayoutPreview() {
  if (!selectedProjectId.value) {
    setNotice('Vui lòng chọn project trước.', 'error')
    return
  }
  autoLayoutLoading.value = true
  try {
    const result = await autoLayout(selectedProjectId.value, {
      layer_gap: autoLayoutOptions.layer_gap,
      node_spacing: autoLayoutOptions.node_spacing,
      apply_to_db: false,
      group_by_area: viewMode.value === 'L1',  // Only group by area for L1 view
      layout_scope: autoLayoutOptions.layout_scope,
      anchor_routing: true,
      overview_mode: 'l1-only',
      view_mode: viewMode.value === 'overview' ? 'L1' : viewMode.value  // Default overview to L1
    })
    autoLayoutResult.value = result
    setNotice(
      `Preview (${viewMode.value}): ${result.devices.length} devices, ${result.stats.total_layers} layers, ${result.stats.total_crossings} crossings`,
      'success'
    )
  } catch (error: any) {
    setNotice(error?.message || 'Auto-layout preview thất bại.', 'error')
    autoLayoutResult.value = null
  } finally {
    autoLayoutLoading.value = false
  }
}

async function handleAutoLayoutApply() {
  if (!selectedProjectId.value) {
    setNotice('Vui lòng chọn project trước.', 'error')
    return
  }
  if (!autoLayoutResult.value) {
    setNotice('Vui lòng preview layout trước khi apply.', 'error')
    return
  }
  autoLayoutLoading.value = true
  try {
    await autoLayout(selectedProjectId.value, {
      layer_gap: autoLayoutOptions.layer_gap,
      node_spacing: autoLayoutOptions.node_spacing,
      apply_to_db: true,
      group_by_area: viewMode.value === 'L1',  // Only group by area for L1 view
      layout_scope: autoLayoutOptions.layout_scope,
      anchor_routing: true,
      overview_mode: 'l1-only',
      view_mode: viewMode.value === 'overview' ? 'L1' : viewMode.value  // Default overview to L1
    })
    setNotice(`Layout (${viewMode.value}) đã được áp dụng vào database!`, 'success')
    // Reload project data to reflect new positions
    await loadProjectData(selectedProjectId.value)
    // Invalidate cache
    await invalidateLayoutCache(selectedProjectId.value)
    // Close dialog
    showAutoLayoutDialog.value = false
    autoLayoutResult.value = null
  } catch (error: any) {
    setNotice(error?.message || 'Áp dụng layout thất bại.', 'error')
  } finally {
    autoLayoutLoading.value = false
  }
}

onMounted(() => {
  fetchHealth()
  initAuth()
})
</script>

<style scoped>
.app-shell {
  height: 100vh;
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
  grid-template-columns: minmax(220px, 280px) 1fr var(--right-panel-width, 360px);
  gap: 16px;
  height: 100%;
  min-height: 0;
}

.workspace.right-collapsed {
  grid-template-columns: minmax(220px, 280px) 1fr 0px;
}

.panel {
  background: var(--panel);
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  padding: 18px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: auto;
}

.section h2 {
  font-size: 15px;
  margin: 0 0 8px;
}

.panel ul {
  margin: 0;
  padding: 0 0 0 18px;
  color: var(--muted);
}

.stack {
  display: grid;
  gap: 8px;
}

.row {
  display: flex;
  gap: 8px;
}

.input,
.select {
  width: 100%;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(28, 28, 28, 0.12);
  font-family: inherit;
  font-size: 13px;
}

.divider {
  height: 1px;
  background: rgba(28, 28, 28, 0.08);
  margin: 4px 0;
}

.user-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 12px;
  background: #f8f1ea;
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

.ghost {
  background: transparent;
  border-color: #dccfc4;
}

.primary {
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 8px 12px;
  cursor: pointer;
}

.notice {
  font-size: 12px;
  padding: 10px 12px;
  border-radius: 12px;
}

.notice.info {
  background: #f0efe9;
  color: #5c544d;
}

.notice.success {
  background: #e5f3eb;
  color: #1c7c54;
}

.notice.error {
  background: #f7e8e8;
  color: #b63d3d;
}

.canvas {
  height: 100%;
  min-height: 0;
  position: relative;
}

.canvas-toolbar {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 2;
  display: flex;
  gap: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 12px;
  border: 1px solid rgba(28, 28, 28, 0.1);
  box-shadow: var(--shadow);
}

.canvas-toolbar button {
  border-radius: 10px;
  border: 1px solid transparent;
  padding: 6px 10px;
  cursor: pointer;
  background: #efe7df;
  font-size: 12px;
}

.canvas-toolbar .ghost {
  background: transparent;
  border-color: #dccfc4;
}

.canvas-toolbar button.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.toolbar-divider {
  width: 1px;
  height: 24px;
  background: rgba(28, 28, 28, 0.15);
  margin: 0 4px;
}

.grid-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
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

.panel-size {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}

.panel-size input {
  width: 120px;
}

.hint {
  margin-top: auto;
  padding: 10px 12px;
  background: var(--accent-soft);
  border-radius: 12px;
  font-size: 13px;
}

.panel-hint {
  padding: 16px 12px;
  background: #f8f5f2;
  border-radius: 12px;
  font-size: 13px;
  color: var(--muted);
  text-align: center;
}

.hint-text {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

@media (max-width: 1024px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .canvas {
    order: 1;
    min-height: 50vh;
  }

  .panel-size {
    width: 100%;
    margin-left: 0;
  }
}

/* Auto Layout Dialog */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.dialog-box {
  background: var(--panel);
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 520px;
  max-height: 90vh;
  overflow: auto;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(28, 28, 28, 0.08);
}

.dialog-header h2 {
  font-size: 18px;
  margin: 0;
}

.ghost-close {
  background: transparent;
  border: 1px solid #dccfc4;
  border-radius: 8px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.ghost-close:hover {
  background: #f8f1ea;
}

.dialog-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-section label {
  font-size: 13px;
  font-weight: 500;
  color: var(--muted);
}

.slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e5ddd4;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  border: none;
}

.layout-stats {
  background: #f8f1ea;
  border-radius: 12px;
  padding: 14px 18px;
}

.layout-stats h3 {
  font-size: 14px;
  margin: 0 0 10px;
}

.layout-stats ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.layout-stats li {
  font-size: 13px;
  color: var(--muted);
}

.dialog-footer {
  padding: 16px 24px;
  border-top: 1px solid rgba(28, 28, 28, 0.08);
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.dialog-footer button {
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
}

.dialog-footer .primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
