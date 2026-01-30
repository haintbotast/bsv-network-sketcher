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
          <button type="button" :class="{ active: viewMode === 'L1' }" @click="setViewMode('L1')">[L1]</button>
          <button type="button" :class="{ active: viewMode === 'L2' }" @click="setViewMode('L2')">[L2]</button>
          <button type="button" :class="{ active: viewMode === 'L3' }" @click="setViewMode('L3')">[L3]</button>
          <span class="view-badge">{{ viewModeLabel }}</span>
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
          :render-tuning="renderTuning"
          @select="handleSelect"
          @update:viewport="updateViewport"
        />
      </main>

      <aside v-show="showRightPanel" class="panel right">
        <div class="inspector-header">
          <div class="inspector-tabs">
            <button
              type="button"
              :class="{ active: rightPanelTab === 'properties' }"
              @click="rightPanelTab = 'properties'"
            >
              Thuộc tính
            </button>
            <button
              type="button"
              :class="{ active: rightPanelTab === 'layout' }"
              @click="rightPanelTab = 'layout'"
            >
              Bố cục
            </button>
          </div>
          <label class="panel-size">
            <span>Rộng</span>
            <input type="range" min="280" max="520" step="20" v-model.number="rightPanelWidth" />
          </label>
        </div>

        <div v-if="rightPanelTab === 'layout'" class="inspector-content">
          <div v-if="!currentUser" class="inspector-empty">
            <p>Đăng nhập để chỉnh cấu hình bố cục.</p>
          </div>
          <div v-else class="layout-content">
            <p class="panel-hint">Bố cục tổng thể (đơn vị inch)</p>
            <div class="form-row">
              <div class="form-group">
                <label>Khoảng cách tầng</label>
                <input type="number" step="0.05" v-model.number="layoutTuningForm.layer_gap" />
              </div>
              <div class="form-group">
                <label>Khoảng cách thiết bị</label>
                <input type="number" step="0.05" v-model.number="layoutTuningForm.node_spacing" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Khoảng cách giữa các vùng</label>
                <input type="number" step="0.05" v-model.number="layoutTuningForm.area_gap" />
              </div>
              <div class="form-group">
                <label>Bù nhãn cổng</label>
                <input type="number" step="0.05" v-model.number="layoutTuningForm.port_label_band" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Lề trong của vùng</label>
                <input type="number" step="0.05" v-model.number="layoutTuningForm.area_padding" />
              </div>
              <div class="form-group">
                <label>Lề nhãn khu vực</label>
                <input type="number" step="0.05" v-model.number="layoutTuningForm.label_band" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Giới hạn độ rộng mỗi hàng</label>
                <input type="number" step="0.1" v-model.number="layoutTuningForm.max_row_width_base" />
              </div>
              <div class="form-group">
                <label>Tối đa node mỗi hàng</label>
                <input type="number" step="1" min="1" v-model.number="layoutTuningForm.max_nodes_per_row" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Khoảng cách giữa hàng</label>
                <input type="number" step="0.05" v-model.number="layoutTuningForm.row_gap" />
              </div>
              <div class="form-group">
                <label>Độ so‑le hàng (0‑1)</label>
                <input type="number" step="0.05" min="0" max="1" v-model.number="layoutTuningForm.row_stagger" />
              </div>
            </div>

            <div class="divider"></div>
            <p class="panel-hint">Đường nối & nhãn (px)</p>
            <div class="form-row">
              <div class="form-group">
                <label>Khoảng cách bó đường</label>
                <input type="number" step="1" v-model.number="renderTuningForm.bundle_gap" />
              </div>
              <div class="form-group">
                <label>Độ dài đuôi bó</label>
                <input type="number" step="1" v-model.number="renderTuningForm.bundle_stub" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Khoảng tránh vùng</label>
                <input type="number" step="1" v-model.number="renderTuningForm.area_clearance" />
              </div>
              <div class="form-group">
                <label>Đẩy điểm neo</label>
                <input type="number" step="1" v-model.number="renderTuningForm.area_anchor_offset" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Giãn nhãn ngang</label>
                <input type="number" step="1" v-model.number="renderTuningForm.label_gap_x" />
              </div>
              <div class="form-group">
                <label>Giãn nhãn dọc</label>
                <input type="number" step="1" v-model.number="renderTuningForm.label_gap_y" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Đẩy nhãn cổng</label>
                <input type="number" step="1" v-model.number="renderTuningForm.port_label_offset" />
              </div>
              <div class="form-group">
                <label>Khoảng cách hành lang</label>
                <input type="number" step="1" v-model.number="renderTuningForm.corridor_gap" />
              </div>
            </div>

            <button type="button" class="primary" :disabled="adminConfigSaving" @click="saveAdminConfig">
              {{ adminConfigSaving ? 'Đang lưu...' : 'Lưu cấu hình' }}
            </button>
            <button
              type="button"
              class="secondary"
              :disabled="autoLayoutManualApplying || !activeProject || !devices.length"
              @click="runAutoLayoutManual"
            >
              {{ autoLayoutManualApplying ? 'Đang chạy...' : 'Chạy lại auto-layout' }}
            </button>

            <div class="divider"></div>
            <div class="section">
              <h2>Phân bổ thiết bị vào area</h2>
              <div v-if="!areas.length || !devices.length" class="inspector-empty">
                <p>Chưa có area hoặc thiết bị để phân bổ.</p>
              </div>
              <div v-else class="device-area-list">
                <div v-for="device in devices" :key="device.id" class="device-area-row">
                  <div class="device-area-info">
                    <strong>{{ device.name }}</strong>
                    <span class="muted">{{ device.device_type }}</span>
                  </div>
                  <select
                    class="select"
                    :value="device.area_id"
                    @change="event => assignDeviceArea(device, (event.target as HTMLSelectElement).value)"
                  >
                    <option v-for="area in areas" :key="area.id" :value="area.id">
                      {{ area.name }}
                    </option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="!selectedObject" class="inspector-empty">
          <p>Chọn một đối tượng trên canvas để xem và chỉnh sửa thuộc tính.</p>
        </div>

        <div v-else class="inspector-content">
          <div class="inspector-type">
            {{ selectedObjectType }}
          </div>

          <!-- Area Properties -->
          <div v-if="selectedObjectType === 'Area' && selectedDraft" class="inspector-form">
            <div class="form-group">
              <label>Tên</label>
              <input type="text" v-model="selectedDraft.name" @change="handleSelectedObjectChange" />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Hàng lưới</label>
                <input type="number" v-model.number="selectedDraft.grid_row" @change="handleSelectedObjectChange" />
              </div>
              <div class="form-group">
                <label>Cột lưới</label>
                <input type="number" v-model.number="selectedDraft.grid_col" @change="handleSelectedObjectChange" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Tọa độ X (đv)</label>
                <input type="number" step="0.1" v-model.number="selectedDraft.position_x" @change="handleSelectedObjectChange" />
              </div>
              <div class="form-group">
                <label>Tọa độ Y (đv)</label>
                <input type="number" step="0.1" v-model.number="selectedDraft.position_y" @change="handleSelectedObjectChange" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Rộng (đv)</label>
                <input type="number" step="0.1" v-model.number="selectedDraft.width" @change="handleSelectedObjectChange" />
              </div>
              <div class="form-group">
                <label>Cao (đv)</label>
                <input type="number" step="0.1" v-model.number="selectedDraft.height" @change="handleSelectedObjectChange" />
              </div>
            </div>
          </div>

          <!-- Device Properties -->
          <div v-else-if="selectedObjectType === 'Device' && selectedDraft" class="inspector-form">
            <div class="form-group">
              <label>Tên thiết bị</label>
              <input type="text" v-model="selectedDraft.name" @change="handleSelectedObjectChange" />
            </div>
            <div class="form-group">
              <label>Area</label>
              <select v-model="selectedDraft.area_name" @change="handleSelectedObjectChange">
                <option v-for="area in areas" :key="area.id" :value="area.name">{{ area.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Loại thiết bị</label>
              <select v-model="selectedDraft.device_type" @change="handleSelectedObjectChange">
                <option v-for="type in deviceTypes" :key="type" :value="type">{{ type }}</option>
              </select>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>X (đv)</label>
                <input type="number" step="0.1" v-model.number="selectedDraft.position_x" @change="handleSelectedObjectChange" />
              </div>
              <div class="form-group">
                <label>Y (đv)</label>
                <input type="number" step="0.1" v-model.number="selectedDraft.position_y" @change="handleSelectedObjectChange" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Width (đv)</label>
                <input type="number" step="0.1" v-model.number="selectedDraft.width" @change="handleSelectedObjectChange" />
              </div>
              <div class="form-group">
                <label>Height (đv)</label>
                <input type="number" step="0.1" v-model.number="selectedDraft.height" @change="handleSelectedObjectChange" />
              </div>
            </div>
          </div>

          <!-- Link Properties -->
          <div v-else-if="selectedObjectType === 'Link' && selectedDraft" class="inspector-form">
            <div class="form-group">
              <label>Thiết bị nguồn</label>
              <select v-model="selectedDraft.from_device_name" @change="handleSelectedObjectChange">
                <option v-for="device in devices" :key="device.id" :value="device.name">{{ device.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Cổng nguồn</label>
              <input type="text" v-model="selectedDraft.from_port" @change="handleSelectedObjectChange" />
            </div>
            <div class="form-group">
              <label>Thiết bị đích</label>
              <select v-model="selectedDraft.to_device_name" @change="handleSelectedObjectChange">
                <option v-for="device in devices" :key="device.id" :value="device.name">{{ device.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Cổng đích</label>
              <input type="text" v-model="selectedDraft.to_port" @change="handleSelectedObjectChange" />
            </div>
            <div class="form-group">
              <label>Kiểu đường</label>
              <select v-model="selectedDraft.line_style" @change="handleSelectedObjectChange">
                <option value="solid">Solid</option>
                <option value="dashed">Dashed</option>
                <option value="dotted">Dotted</option>
              </select>
            </div>
            <div class="form-group">
              <label>Mục đích</label>
              <select v-model="selectedDraft.purpose" @change="handleSelectedObjectChange">
                <option v-for="purpose in linkPurposes" :key="purpose" :value="purpose">{{ purpose }}</option>
              </select>
            </div>
          </div>

          <div class="inspector-actions">
            <button
              type="button"
              class="secondary"
              :disabled="!selectedDraftDirty || selectedSavePending"
              @click="resetSelectedDraft"
            >
              Hủy thay đổi
            </button>
            <button
              type="button"
              class="primary"
              :disabled="!selectedDraftDirty || selectedSavePending"
              @click="saveSelectedObject"
            >
              {{ selectedSavePending ? 'Đang lưu...' : 'Lưu thay đổi' }}
            </button>
            <button type="button" class="danger" @click="handleSelectedObjectDelete">Xóa</button>
          </div>
        </div>

        <div v-if="rightPanelTab === 'properties'" class="hint">
          {{ activeProject ? 'Bảng thuộc tính' : 'Cần đăng nhập và chọn project' }}
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import CanvasStage from './components/CanvasStage.vue'
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
import { getAdminConfig, updateAdminConfig } from './services/adminConfig'
import type { AdminConfig, LayoutTuning, RenderTuning } from './services/adminConfig'

const UNIT_PX = 120
const GRID_FALLBACK_X = 4
const GRID_FALLBACK_Y = 2.5
const DEFAULT_LAYOUT_TUNING: LayoutTuning = {
  layer_gap: 1.5,
  node_spacing: 0.8,
  port_label_band: 0.2,
  area_gap: 1.1,
  area_padding: 0.35,
  label_band: 0.5,
  max_row_width_base: 12.0,
  max_nodes_per_row: 8,
  row_gap: 0.5,
  row_stagger: 0.5
}
const DEFAULT_RENDER_TUNING: RenderTuning = {
  port_edge_inset: 6,
  port_label_offset: 12,
  bundle_gap: 18,
  bundle_stub: 18,
  area_clearance: 18,
  area_anchor_offset: 18,
  label_gap_x: 8,
  label_gap_y: 6,
  corridor_gap: 40
}

const statusText = ref('đang kiểm tra...')
const notice = ref('')
const noticeType = ref<'info' | 'success' | 'error'>('info')

const authForm = reactive({
  email: '',
  password: ''
})
const currentUser = ref<UserRecord | null>(null)
const adminConfig = ref<AdminConfig>({})
const layoutTuningForm = reactive({ ...DEFAULT_LAYOUT_TUNING })
const renderTuningForm = reactive({ ...DEFAULT_RENDER_TUNING })
const adminConfigSaving = ref(false)
const autoLayoutManualApplying = ref(false)

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
const selectedDraft = ref<any>(null)
const selectedDraftDirty = ref(false)
const selectedSavePending = ref(false)
let syncingDraft = false

const viewport = reactive({
  scale: 1,
  offsetX: 0,
  offsetY: 0
})

const showRightPanel = ref(true)
const rightPanelWidth = ref(360)
const rightPanelTab = ref<'properties' | 'layout'>('properties')

const layoutMode = computed(() => activeProject.value?.layout_mode || 'cisco')
const layoutModeSelection = ref<'cisco' | 'iso' | 'custom'>('cisco')
const layoutModeUpdating = ref(false)
const layoutTuning = computed(() => ({
  ...DEFAULT_LAYOUT_TUNING,
  ...(adminConfig.value.layout_tuning || {})
}))
const renderTuning = computed(() => ({
  ...DEFAULT_RENDER_TUNING,
  ...(adminConfig.value.render_tuning || {})
}))

// View mode for canvas (L1/L2/L3)
type ViewMode = 'L1' | 'L2' | 'L3'
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

// Auto Layout (auto mode only - manual dialog removed)
const autoLayoutAutoApplying = ref(false)
const autoLayoutAutoAppliedProjects = new Set<string>()
let autoLayoutTimer: number | null = null

// Properties Inspector computed properties
const selectedObject = computed(() => {
  if (!selectedId.value) return null

  // Try to find in areas
  const area = areas.value.find(a => a.id === selectedId.value)
  if (area) return area

  // Try to find in devices
  const device = devices.value.find(d => d.id === selectedId.value)
  if (device) return device

  // Try to find in links
  const link = links.value.find(l => l.id === selectedId.value)
  if (link) return link

  return null
})

const selectedObjectType = computed(() => {
  if (!selectedObject.value) return null

  if (areas.value.some(a => a.id === selectedId.value)) return 'Area'
  if (devices.value.some(d => d.id === selectedId.value)) return 'Device'
  if (links.value.some(l => l.id === selectedId.value)) return 'Link'

  return null
})

function cloneRow<T>(row: T): T {
  return JSON.parse(JSON.stringify(row)) as T
}

function syncSelectedDraft() {
  syncingDraft = true
  if (!selectedObject.value) {
    selectedDraft.value = null
    selectedDraftDirty.value = false
    syncingDraft = false
    return
  }
  selectedDraft.value = cloneRow(selectedObject.value)
  selectedDraftDirty.value = false
  window.setTimeout(() => {
    syncingDraft = false
  }, 0)
}

watch(selectedId, () => {
  syncSelectedDraft()
})

watch(selectedObject, () => {
  if (!selectedDraftDirty.value) {
    syncSelectedDraft()
  }
})

watch(
  selectedDraft,
  () => {
    if (syncingDraft || !selectedDraft.value) return
    selectedDraftDirty.value = true
  },
  { deep: true }
)

function resetSelectedDraft() {
  syncSelectedDraft()
}

const selectedAreaName = computed(() => {
  if (!selectedObject.value) return null
  if (selectedObjectType.value === 'Area') {
    return (selectedObject.value as AreaRow).name
  }
  if (selectedObjectType.value === 'Device') {
    const device = selectedObject.value as DeviceRow
    const area = areas.value.find(a => a.id === device.area_id)
    return area?.name || null
  }
  return null
})

const deviceTypes = ['Router', 'Switch', 'Firewall', 'Server', 'AP', 'PC', 'Storage', 'Unknown']
const linkPurposes = ['DEFAULT', 'WAN', 'INTERNET', 'DMZ', 'LAN', 'MGMT', 'HA', 'STORAGE', 'BACKUP', 'VPN']

const defaultAreaStyle: AreaStyle = {
  fill_color_rgb: [240, 240, 240],
  stroke_color_rgb: [51, 51, 51],
  stroke_width: 1
}

const statusClass = computed(() => {
  if (statusText.value === 'healthy') return 'ok'
  if (statusText.value === 'không kết nối được') return 'error'
  if (statusText.value === 'lỗi kết nối') return 'error'
  return 'pending'
})

const viewModeLabel = computed(() => {
  const areaName = selectedAreaName.value
  if (viewMode.value === 'L1') return 'All Areas'
  if (viewMode.value === 'L2') return areaName || 'Focus on Area'
  if (viewMode.value === 'L3') {
    return areaName ? `All Areas · Focus: ${areaName}` : 'All Areas'
  }
  return ''
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
    const xUnits = area.position_x ?? (area.grid_col - 1) * GRID_FALLBACK_X
    const yUnits = area.position_y ?? (area.grid_row - 1) * GRID_FALLBACK_Y
    const widthUnits = area.width || 3
    const heightUnits = area.height || 1.5
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

// Auto-layout preview removed - auto mode applies directly to DB

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
  rightPanelTab.value = 'properties'
}

function assignDeviceArea(device: DeviceRow, areaId: string) {
  const area = areas.value.find(item => item.id === areaId)
  if (!area) return
  device.area_id = area.id
  device.area_name = area.name
  handleDeviceChange({ row: device })
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

function syncTuningForms(config: AdminConfig) {
  Object.assign(layoutTuningForm, { ...DEFAULT_LAYOUT_TUNING, ...(config.layout_tuning || {}) })
  Object.assign(renderTuningForm, { ...DEFAULT_RENDER_TUNING, ...(config.render_tuning || {}) })
}

async function loadAdminConfig() {
  if (!currentUser.value) return
  try {
    const config = await getAdminConfig()
    adminConfig.value = config
    syncTuningForms(config)
  } catch (error: any) {
    setNotice(error?.message || 'Không thể tải cấu hình layout.', 'error')
  }
}

async function saveAdminConfig() {
  if (adminConfigSaving.value) return
  adminConfigSaving.value = true
  try {
    const payload: AdminConfig = {
      layout_tuning: { ...layoutTuningForm },
      render_tuning: { ...renderTuningForm }
    }
    const updated = await updateAdminConfig(payload)
    adminConfig.value = updated
    syncTuningForms(updated)
    if (activeProject.value) {
      await runAutoLayoutAuto(activeProject.value.id, true)
    }
    setNotice('Đã lưu cấu hình layout.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Lưu cấu hình layout thất bại.', 'error')
  } finally {
    adminConfigSaving.value = false
  }
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
    await loadAdminConfig()
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
    await loadAdminConfig()
    await loadProjects()
    setNotice('Đăng nhập thành công.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Đăng nhập thất bại.', 'error')
  }
}

function handleLogout() {
  logoutUser()
  currentUser.value = null
  adminConfig.value = {}
  syncTuningForms({})
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

// Properties Inspector handlers
function handleSelectedObjectChange() {
  if (!selectedDraft.value || !selectedId.value) return
  selectedDraftDirty.value = true
}

async function saveSelectedObject() {
  if (!selectedDraft.value || !selectedId.value || !selectedProjectId.value) return
  if (selectedSavePending.value) return

  const projectId = selectedProjectId.value
  const objectType = selectedObjectType.value
  if (!objectType) return

  if (objectType === 'Device' && !selectedDraft.value.area_name) {
    setNotice('Cần chọn area cho device.', 'error')
    return
  }
  if (objectType === 'Link' && (!selectedDraft.value.from_device_name || !selectedDraft.value.to_device_name)) {
    setNotice('Cần chọn thiết bị đầu/cuối cho link.', 'error')
    return
  }

  selectedSavePending.value = true
  try {
    let updated: AreaRow | DeviceRow | LinkRow | null = null
    if (objectType === 'Area') {
      updated = await updateArea(projectId as string, selectedDraft.value.id, {
        name: selectedDraft.value.name,
        grid_row: selectedDraft.value.grid_row,
        grid_col: selectedDraft.value.grid_col,
        position_x: selectedDraft.value.position_x,
        position_y: selectedDraft.value.position_y,
        width: selectedDraft.value.width,
        height: selectedDraft.value.height,
        style: selectedDraft.value.style || undefined
      })
      const index = areas.value.findIndex(area => area.id === selectedDraft.value.id)
      if (index >= 0 && updated) areas.value[index] = updated as AreaRow
    } else if (objectType === 'Device') {
      updated = await updateDevice(projectId as string, selectedDraft.value.id, {
        name: selectedDraft.value.name,
        area_name: selectedDraft.value.area_name || undefined,
        device_type: selectedDraft.value.device_type,
        position_x: selectedDraft.value.position_x,
        position_y: selectedDraft.value.position_y,
        width: selectedDraft.value.width,
        height: selectedDraft.value.height,
        color_rgb: selectedDraft.value.color_rgb || undefined
      })
      const index = devices.value.findIndex(device => device.id === selectedDraft.value.id)
      if (index >= 0 && updated) devices.value[index] = updated as DeviceRow
    } else if (objectType === 'Link') {
      updated = await updateLink(projectId as string, selectedDraft.value.id, {
        from_device: selectedDraft.value.from_device_name || undefined,
        from_port: selectedDraft.value.from_port,
        to_device: selectedDraft.value.to_device_name || undefined,
        to_port: selectedDraft.value.to_port,
        purpose: selectedDraft.value.purpose || undefined,
        line_style: selectedDraft.value.line_style || undefined
      })
      const index = links.value.findIndex(link => link.id === selectedDraft.value.id)
      if (index >= 0 && updated) links.value[index] = updated as LinkRow
    }
    if (updated) {
      selectedDraft.value = cloneRow(updated)
      selectedDraftDirty.value = false
      setNotice('Đã lưu thay đổi.', 'success')
    }
  } catch (error: any) {
    setNotice(error?.message || 'Lưu thay đổi thất bại.', 'error')
  } finally {
    selectedSavePending.value = false
  }
}

async function handleSelectedObjectDelete() {
  if (!selectedObject.value || !selectedId.value) return
  if (!confirm('Bạn có chắc muốn xóa đối tượng này?')) return

  const objectType = selectedObjectType.value
  if (objectType === 'Area') {
    await handleAreaRemove(selectedObject.value as AreaRow)
  } else if (objectType === 'Device') {
    await handleDeviceRemove(selectedObject.value as DeviceRow)
  } else if (objectType === 'Link') {
    await handleLinkRemove(selectedObject.value as LinkRow)
  }

  // Clear selection after delete
  selectedId.value = null
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
    scheduleAutoLayout(projectId)
  } else {
    areas.value = []
    devices.value = []
    links.value = []
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
  const tuning = layoutTuning.value
  const layer_gap = Number((tuning.layer_gap ?? DEFAULT_LAYOUT_TUNING.layer_gap).toFixed(2))
  const node_spacing = Number((tuning.node_spacing ?? DEFAULT_LAYOUT_TUNING.node_spacing).toFixed(2))
  return { layer_gap, node_spacing }
}

function hasStoredLayout() {
  const epsilon = 0.0001
  const deviceHasLayout = devices.value.some(device =>
    Math.abs(device.position_x ?? 0) > epsilon || Math.abs(device.position_y ?? 0) > epsilon
  )
  const areaHasLayout = areas.value.some(area =>
    Math.abs(area.position_x ?? 0) > epsilon || Math.abs(area.position_y ?? 0) > epsilon
  )
  return deviceHasLayout || areaHasLayout
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
  if (!force && hasStoredLayout()) {
    autoLayoutAutoAppliedProjects.add(projectId)
    return
  }

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
      overview_mode: 'l1-only',
      normalize_topology: true
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

async function runAutoLayoutManual() {
  if (!activeProject.value || autoLayoutManualApplying.value) return
  if (!devices.value.length) {
    setNotice('Chưa có thiết bị để chạy auto-layout.', 'error')
    return
  }

  autoLayoutManualApplying.value = true
  const projectId = activeProject.value.id
  const hasAreas = areas.value.length > 0
  try {
    const tuning = computeAutoLayoutTuning()
    await autoLayout(projectId, {
      layer_gap: tuning.layer_gap,
      node_spacing: tuning.node_spacing,
      apply_to_db: true,
      group_by_area: hasAreas,
      layout_scope: 'project',
      anchor_routing: true,
      overview_mode: 'l1-only',
      normalize_topology: true
    })
    autoLayoutAutoAppliedProjects.add(projectId)
    await loadProjectData(projectId)
    await invalidateLayoutCache(projectId)
    setNotice('Đã chạy lại auto-layout.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Chạy lại auto-layout thất bại.', 'error')
  } finally {
    autoLayoutManualApplying.value = false
  }
}

// Manual auto-layout preview/apply functions removed - auto mode only

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

.secondary {
  background: #efe7df;
  color: #1c1c1c;
  border: 1px solid #dccfc4;
  border-radius: 12px;
  padding: 8px 12px;
  cursor: pointer;
}

.secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  min-width: 0;
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

.view-badge {
  font-size: 12px;
  color: var(--muted);
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px dashed rgba(28, 28, 28, 0.2);
  background: rgba(255, 255, 255, 0.75);
}

.toolbar-divider {
  width: 1px;
  height: 24px;
  background: rgba(28, 28, 28, 0.15);
  margin: 0 4px;
}

/* Properties Inspector */
.inspector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.inspector-tabs {
  display: flex;
  gap: 6px;
  background: #f5eee7;
  padding: 4px;
  border-radius: 12px;
}

.inspector-tabs button {
  border: none;
  background: transparent;
  padding: 6px 12px;
  border-radius: 10px;
  font-size: 12px;
  cursor: pointer;
  color: var(--muted);
}

.inspector-tabs button.active {
  background: #fff;
  color: var(--accent);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.inspector-header h3 {
  font-size: 16px;
  margin: 0;
  font-weight: 600;
}

.inspector-empty {
  padding: 40px 20px;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}

.inspector-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.layout-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.inspector-type {
  display: inline-block;
  padding: 6px 12px;
  background: var(--accent-soft);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  align-self: flex-start;
}

.inspector-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 12px;
  font-weight: 500;
  color: var(--muted);
}

.muted {
  color: var(--muted);
  font-size: 12px;
}

.form-group input,
.form-group select {
  padding: 8px 10px;
  border: 1px solid rgba(28, 28, 28, 0.12);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg);
  color: var(--fg);
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--accent);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.inspector-actions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(28, 28, 28, 0.08);
}

.inspector-actions button {
  flex: 1;
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

.device-area-list {
  display: grid;
  gap: 10px;
}

.device-area-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 10px;
  background: #faf6f2;
}

.device-area-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
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
</style>
