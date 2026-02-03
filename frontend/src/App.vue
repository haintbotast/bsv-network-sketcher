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
import { computed, onMounted, ref, watch } from 'vue'
import CanvasStage from './components/CanvasStage.vue'
import { updateArea } from './services/areas'
import { updateDevice } from './services/devices'
import { updateLink } from './services/links'
import { deviceTypes, linkPurposes } from './composables/canvasConstants'
import { useViewport } from './composables/useViewport'
import { useAuth } from './composables/useAuth'
import { useProjects } from './composables/useProjects'
import { useCanvasData } from './composables/useCanvasData'
import type { AreaRow, DeviceRow, LinkRow } from './composables/useCanvasData'
import { useAutoLayout } from './composables/useAutoLayout'
import { useViewMode } from './composables/useViewMode'
import { useLayoutConfig } from './composables/useLayoutConfig'

const {
  statusText,
  notice,
  noticeType,
  authForm,
  currentUser,
  statusClass,
  setNotice,
  fetchHealth,
  initAuth,
  handleLogin: authLogin,
  handleLogout: authLogout,
} = useAuth()

const {
  adminConfig,
  layoutTuningForm,
  renderTuningForm,
  adminConfigSaving,
  layoutTuning,
  renderTuning,
  loadAdminConfig,
  saveAdminConfig,
  resetConfig: resetLayoutConfig,
} = useLayoutConfig(
  setNotice,
  currentUser,
  () => {
    if (activeProject.value) {
      scheduleAutoLayout(activeProject.value.id, true)
    }
  },
)

const {
  projects,
  selectedProjectId,
  projectForm,
  activeProject,
  layoutMode,
  layoutModeSelection,
  layoutModeUpdating,
  loadProjects,
  handleCreateProject,
  handleLayoutModeChange,
} = useProjects(setNotice)

// useCanvasData needs scheduleAutoLayout which is defined later - use forwarding wrapper
const canvasData = useCanvasData(
  selectedProjectId,
  setNotice,
  (projectId, force) => scheduleAutoLayout(projectId, force),
)
const {
  areas, devices, links,
  canvasAreas, canvasDevices, canvasLinks,
  loadProjectData,
  handleAreaAdd, handleAreaChange, handleAreaRemove,
  handleDeviceAdd, handleDeviceChange, handleDeviceRemove,
  handleLinkAdd, handleLinkChange, handleLinkRemove,
  assignDeviceArea,
} = canvasData

const selectedId = ref<string | null>(null)
const selectedDraft = ref<any>(null)
const selectedDraftDirty = ref(false)
const selectedSavePending = ref(false)
let syncingDraft = false

// Viewport state (from composable)
const {
  viewport,
  viewportState,
  showRightPanel,
  rightPanelWidth,
  rightPanelTab,
  updateViewport,
  zoomIn,
  zoomOut,
  resetViewport,
  toggleRightPanel,
} = useViewport()

// View mode - _selectedAreaNameRef synced via watch after selectedAreaName is defined
const _selectedAreaNameRef = ref<string | null>(null)
const {
  viewMode,
  l2Assignments,
  l3Addresses,
  l2Loaded,
  l3Loaded,
  viewModeLabel,
  setViewMode,
  resetViewModeData,
} = useViewMode(selectedProjectId, _selectedAreaNameRef)

// Auto Layout composable
const {
  autoLayoutAutoApplying,
  autoLayoutManualApplying,
  scheduleAutoLayout,
  runAutoLayoutManual,
} = useAutoLayout({
  areas,
  devices,
  links,
  activeProject,
  layoutTuning,
  setNotice,
  loadProjectData,
})

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

watch(selectedAreaName, (v) => { _selectedAreaNameRef.value = v })

function handleSelect(payload: { id: string; type?: 'device' | 'area' }) {
  selectedId.value = payload.id
  rightPanelTab.value = 'properties'
}

async function onAuthSuccess() {
  await loadAdminConfig()
  await loadProjects()
}

function handleLogin() {
  authLogin({ onSuccess: onAuthSuccess })
}

function handleLogout() {
  authLogout({
    onLogout: () => {
      resetLayoutConfig()
      projects.value = []
      selectedProjectId.value = null
      areas.value = []
      devices.value = []
      links.value = []
    }
  })
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
  resetViewModeData()

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
  await handleLayoutModeChange(value, (projectId) => {
    scheduleAutoLayout(projectId, true)
  })
})

onMounted(() => {
  fetchHealth()
  initAuth({ onSuccess: onAuthSuccess })
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
