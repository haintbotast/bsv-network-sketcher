<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-main">
        <div>
          <h1>BSV Network Sketcher</h1>
          <p>Port từ Network Sketcher gốc</p>
        </div>
        <div class="status">
          <span>Backend</span>
          <strong :class="statusClass">{{ statusText }}</strong>
        </div>
      </div>
      <nav class="topbar-nav">
        <button type="button" @click="handleZoomIn">Zoom +</button>
        <button type="button" @click="handleZoomOut">Zoom -</button>
        <button type="button" class="ghost" @click="handleResetViewport">Reset view</button>
        <button type="button" :class="{ active: positionEditEnabled }" @click="togglePositionEditMode">
          {{ positionEditEnabled ? 'Khóa vị trí' : 'Sửa vị trí' }}
        </button>
        <span class="toolbar-divider"></span>
        <button type="button" :class="{ active: viewMode === 'L1' }" @click="setViewMode('L1')">[L1]</button>
        <button type="button" :class="{ active: viewMode === 'L2' }" @click="setViewMode('L2')">[L2]</button>
        <button type="button" :class="{ active: viewMode === 'L3' }" @click="setViewMode('L3')">[L3]</button>
        <span class="view-badge">{{ viewModeLabel }}</span>
        <span class="toolbar-divider"></span>
        <button type="button" class="ghost" @click="toggleRightPanel">
          {{ showRightPanel ? 'Ẩn panel' : 'Hiện panel' }}
        </button>
      </nav>
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
                {{ project.name }}
              </option>
            </select>
            <div class="divider"></div>
            <input v-model="projectForm.name" type="text" placeholder="Tên project" class="input" />
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
        <!-- Viewport interaction không được trigger auto-layout. -->
        <CanvasStage
          :areas="canvasAreas"
          :devices="canvasDevices"
          :links="canvasLinks"
          :viewport="viewportState"
          :selected-id="selectedId"
          :view-mode="viewMode"
          :position-edit-enabled="positionEditEnabled"
          :l2-assignments="l2Assignments"
          :l3-addresses="l3Addresses"
          :port-anchor-overrides="effectivePortAnchorMap"
          :device-ports-map="devicePortMap"
          :render-tuning="renderTuning"
          @select="handleSelect"
          @update:viewport="handleViewportUpdate"
          @object:position-change="handleCanvasObjectPositionChange"
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
              :class="{ active: rightPanelTab === 'data' }"
              @click="rightPanelTab = 'data'"
            >
              Dữ liệu
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
            <p>Đăng nhập để sử dụng chức năng bố cục.</p>
          </div>
          <div v-else class="layout-content">
            <div class="layout-actions">
              <button
                type="button"
                class="primary"
                :disabled="autoLayoutManualApplying || !activeProject || !devices.length"
                @click="runAutoLayoutManual({ preserveExistingPositions: true })"
              >
                {{ autoLayoutManualApplying ? 'Đang chạy...' : 'Auto-layout (giữ vị trí đã lưu)' }}
              </button>
              <button
                type="button"
                class="ghost"
                :disabled="autoLayoutManualApplying || !activeProject || !devices.length"
                @click="runAutoLayoutManual({ preserveExistingPositions: false })"
              >
                Ghi đè toàn bộ vị trí
              </button>
            </div>
            <p class="hint-text">Khuyến nghị dùng chế độ giữ vị trí để không mất chỉnh tay trước đó.</p>

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

            <div class="divider"></div>
            <div class="section">
              <h2>Khai báo peer-control</h2>
              <p class="hint-text">Tạo nhanh kết nối <strong>HA / STACK / HSRP</strong> và xem chú giải màu/nét.</p>
              <div v-if="devices.length < 2" class="inspector-empty">
                <p>Cần ít nhất 2 thiết bị để khai báo kết nối peer-control.</p>
              </div>
              <div v-else class="peer-link-editor">
                <div class="form-row">
                  <div class="form-group">
                    <label>Thiết bị nguồn</label>
                    <select v-model="peerLinkDraft.fromDeviceId">
                      <option :value="null">-- Chọn --</option>
                      <option v-for="device in devices" :key="`peer-from-${device.id}`" :value="device.id">{{ device.name }}</option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label>Port nguồn</label>
                    <input v-model="peerLinkDraft.fromPort" type="text" placeholder="vd: HA 1 / Stack 1" />
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label>Thiết bị đích</label>
                    <select v-model="peerLinkDraft.toDeviceId">
                      <option :value="null">-- Chọn --</option>
                      <option
                        v-for="device in devices"
                        :key="`peer-to-${device.id}`"
                        :value="device.id"
                        :disabled="device.id === peerLinkDraft.fromDeviceId"
                      >
                        {{ device.name }}
                      </option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label>Port đích</label>
                    <input v-model="peerLinkDraft.toPort" type="text" placeholder="vd: HA 1 / Stack 1" />
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label>Loại kết nối</label>
                    <select v-model="peerLinkDraft.purpose">
                      <option v-for="purpose in peerControlPurposes" :key="`peer-purpose-${purpose}`" :value="purpose">
                        {{ purpose }}
                      </option>
                    </select>
                  </div>
                  <div class="form-group peer-link-actions">
                    <label>&nbsp;</label>
                    <button type="button" class="primary" @click="createPeerControlLink">
                      Tạo kết nối peer-control
                    </button>
                  </div>
                </div>

                <div class="peer-legend">
                  <div v-for="item in peerLegendItems" :key="`peer-legend-${item.purpose}`" class="peer-legend-row">
                    <span class="peer-legend-line" :style="item.swatchStyle"></span>
                    <span class="peer-legend-title">{{ item.purpose }}</span>
                    <span class="peer-legend-note">{{ item.note }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="rightPanelTab === 'data'" class="inspector-content">
          <div v-if="!currentUser" class="inspector-empty">
            <p>Đăng nhập để quản lý dữ liệu.</p>
          </div>
          <div v-else-if="!activeProject" class="inspector-empty">
            <p>Chọn project để thêm/xóa dữ liệu.</p>
          </div>
          <div v-else class="data-content">
            <DataGrid
              title="Areas"
              :columns="areaColumns"
              :rows="areas"
              :default-row="defaultAreaRow"
              @update:rows="updateAreaRows"
              @row:add="handleAreaAdd"
              @row:change="payload => handleAreaChange({ row: payload.row })"
              @row:remove="handleAreaRemove"
            />
            <DataGrid
              title="Devices"
              :columns="deviceColumns"
              :rows="devices"
              :default-row="defaultDeviceRow"
              :show-add="canAddDevice"
              @update:rows="updateDeviceRows"
              @row:add="handleDeviceAdd"
              @row:change="payload => handleDeviceChange({ row: payload.row })"
              @row:remove="handleDeviceRemove"
            />
            <DataGrid
              title="Links"
              :columns="linkColumns"
              :rows="links"
              :default-row="defaultLinkRow"
              :show-add="canAddLink"
              @update:rows="updateLinkRows"
              @row:add="handleLinkAdd"
              @row:change="payload => handleLinkChange({ row: payload.row })"
              @row:remove="handleLinkRemove"
            />
          </div>
        </div>

        <template v-else>
          <div v-if="!selectedObject" class="inspector-empty">
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
            <div class="form-group">
              <label>Grid range (Excel)</label>
              <input type="text" v-model="selectedDraft.grid_range" placeholder="vd: A1:L8" @change="handleSelectedObjectChange" />
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
                <input type="number" :step="POSITION_STANDARD_STEP_UNITS" v-model.number="selectedDraft.position_x" @change="handleSelectedObjectChange" />
              </div>
              <div class="form-group">
                <label>Tọa độ Y (đv)</label>
                <input type="number" :step="POSITION_STANDARD_STEP_UNITS" v-model.number="selectedDraft.position_y" @change="handleSelectedObjectChange" />
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
            <div class="form-group">
              <label>Grid range (Excel)</label>
              <input type="text" v-model="selectedDraft.grid_range" placeholder="vd: B10:F12" @change="handleSelectedObjectChange" />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>X (đv)</label>
                <input type="number" :step="POSITION_STANDARD_STEP_UNITS" v-model.number="selectedDraft.position_x" @change="handleSelectedObjectChange" />
              </div>
              <div class="form-group">
                <label>Y (đv)</label>
                <input type="number" :step="POSITION_STANDARD_STEP_UNITS" v-model.number="selectedDraft.position_y" @change="handleSelectedObjectChange" />
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
            <div class="form-group">
              <label>Port của thiết bị</label>
              <div class="port-editor">
                <div v-if="selectedDevicePortRows.length === 0" class="hint small">
                  Chưa có port. Thêm port trước khi tạo link.
                </div>
                <div v-else class="port-editor-list">
                  <div v-for="port in selectedDevicePortRows" :key="port.id" class="port-editor-row">
                    <template v-if="portDrafts[port.id]">
                      <input
                        type="text"
                        v-model="portDrafts[port.id].name"
                        placeholder="Tên port (vd: Gi 0/1)"
                      />
                      <select v-model="portDrafts[port.id].side">
                        <option value="top">top</option>
                        <option value="bottom">bottom</option>
                        <option value="left">left</option>
                        <option value="right">right</option>
                      </select>
                      <button type="button" class="secondary" @click="saveDevicePort(port.id)">
                        Lưu port
                      </button>
                      <button type="button" class="ghost" @click="removeDevicePort(port.id)">
                        Xóa
                      </button>
                    </template>
                  </div>
                </div>
                <div class="port-editor-create">
                  <input type="text" v-model="newPortDraft.name" placeholder="Port mới (vd: Gi 0/24)" />
                  <select v-model="newPortDraft.side">
                    <option value="top">top</option>
                    <option value="bottom">bottom</option>
                    <option value="left">left</option>
                    <option value="right">right</option>
                  </select>
                  <button type="button" class="primary" @click="createDevicePortEntry">
                    Thêm port
                  </button>
                </div>
              </div>
            </div>
            <div class="form-group">
              <label>Anchor port (override)</label>
              <div v-if="selectedDevicePorts.length === 0" class="hint small">
                Chưa có port để chỉnh.
              </div>
              <div v-else class="anchor-override-list">
                <div v-for="port in selectedDevicePorts" :key="port" class="anchor-override-row">
                  <div class="anchor-port-name">
                    <span>{{ port }}</span>
                    <span v-if="hasAnchorOverride(port)" class="badge">override</span>
                  </div>
                  <div v-if="anchorDrafts[port]" class="anchor-controls">
                    <select v-model="anchorDrafts[port].side">
                      <option value="left">left</option>
                      <option value="right">right</option>
                      <option value="top">top</option>
                      <option value="bottom">bottom</option>
                    </select>
                    <label class="anchor-auto">
                      <input type="checkbox" v-model="anchorDrafts[port].autoOffset" />
                      Auto offset
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      v-model.number="anchorDrafts[port].offsetRatio"
                      :disabled="anchorDrafts[port].autoOffset"
                    />
                    <button type="button" class="secondary" @click="saveAnchorOverride(port)">
                      Lưu
                    </button>
                    <button type="button" class="ghost" @click="clearAnchorOverride(port)">
                      Reset
                    </button>
                  </div>
                  <div v-if="anchorDrafts[port]" class="anchor-swap-controls">
                    <select v-model="anchorSwapTargets[port]">
                      <option value="">-- Chọn port để đổi vị trí --</option>
                      <option
                        v-for="candidate in getAnchorSwapCandidates(port)"
                        :key="`${port}-${candidate}`"
                        :value="candidate"
                      >
                        {{ candidate }}
                      </option>
                    </select>
                    <button
                      type="button"
                      class="ghost"
                      :disabled="!canSwapAnchorWith(port)"
                      @click="swapAnchorWith(port)"
                    >
                      Đổi vị trí với port đã chọn
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div class="form-group">
              <label>Kết nối theo port (L1)</label>
              <div v-if="selectedDeviceLinkEntries.length === 0" class="hint small">
                Chưa có kết nối L1 cho thiết bị này.
              </div>
              <div v-else class="port-link-list">
                <div v-for="entry in selectedDeviceLinkEntries" :key="entry.port" class="port-link-group">
                  <div class="port-link-header">
                    <span>{{ entry.port }}</span>
                    <span class="muted">{{ entry.links.length }} link</span>
                  </div>
                  <div
                    v-for="conn in entry.links"
                    :key="conn.linkId"
                    class="port-link-row"
                  >
                    <div v-if="linkDrafts[conn.linkId]" class="port-link-controls">
                      <select v-model="linkDrafts[conn.linkId].targetDeviceId">
                        <option :value="null">-- Chọn thiết bị đích --</option>
                        <option v-for="device in targetDeviceOptions" :key="device.id" :value="device.id">
                          {{ device.name }}
                        </option>
                      </select>
                      <input
                        type="text"
                        v-model="linkDrafts[conn.linkId].targetPort"
                        placeholder="Port đích (vd: Gi 0/24)"
                      />
                      <select v-model="linkDrafts[conn.linkId].purpose">
                        <option v-for="purpose in linkPurposes" :key="purpose" :value="purpose">{{ purpose }}</option>
                      </select>
                      <select v-model="linkDrafts[conn.linkId].lineStyle">
                        <option v-for="style in linkLineStyles" :key="style" :value="style">{{ style }}</option>
                      </select>
                    </div>
                    <div class="port-link-actions">
                      <button type="button" class="secondary" @click="savePortLink(conn)">
                        Lưu
                      </button>
                      <button type="button" class="ghost" @click="removePortLink(conn)">
                        Xóa
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="form-group">
              <label>Thêm kết nối L1</label>
              <div class="new-link-controls">
                <input
                  type="text"
                  v-model="newLinkDraft.port"
                  placeholder="Port nguồn (vd: Gi 0/1)"
                />
                <select v-model="newLinkDraft.targetDeviceId">
                  <option :value="null">-- Chọn thiết bị đích --</option>
                  <option v-for="device in targetDeviceOptions" :key="device.id" :value="device.id">
                    {{ device.name }}
                  </option>
                </select>
                <input
                  type="text"
                  v-model="newLinkDraft.targetPort"
                  placeholder="Port đích (vd: Gi 0/24)"
                />
                <select v-model="newLinkDraft.purpose">
                  <option v-for="purpose in linkPurposes" :key="purpose" :value="purpose">{{ purpose }}</option>
                </select>
                <select v-model="newLinkDraft.lineStyle">
                  <option v-for="style in linkLineStyles" :key="style" :value="style">{{ style }}</option>
                </select>
                <button type="button" class="primary" @click="createPortLink">
                  Tạo link
                </button>
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

          <div class="hint">
            {{ activeProject ? 'Bảng thuộc tính' : 'Cần đăng nhập và chọn project' }}
          </div>
        </template>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import CanvasStage from './components/CanvasStage.vue'
import DataGrid, { type ColumnDef } from './components/DataGrid.vue'
import { updateArea } from './services/areas'
import { updateDevice } from './services/devices'
import { createLink, deleteLink, updateLink } from './services/links'
import {
  UNIT_PX,
  POSITION_STANDARD_STEP_UNITS,
  snapUnitsToStandard,
  deviceTypes,
  linkPurposes,
} from './composables/canvasConstants'
import { comparePorts, extractPortIndex } from './components/canvas/linkRoutingUtils'
import { formatExcelCell } from './utils/excelGrid'
import { useViewport } from './composables/useViewport'
import { useAuth } from './composables/useAuth'
import { useProjects } from './composables/useProjects'
import { useCanvasData } from './composables/useCanvasData'
import type { AreaRow, DevicePortRow, DeviceRow, LinkRow } from './composables/useCanvasData'
import { useAutoLayout } from './composables/useAutoLayout'
import type { ScheduleAutoLayoutOptions } from './composables/useAutoLayout'
import { useViewMode } from './composables/useViewMode'
import { useLayoutConfig } from './composables/useLayoutConfig'
import type { Viewport } from './models/types'

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
  layoutTuning,
  renderTuning,
  loadAdminConfig,
} = useLayoutConfig(currentUser)

const {
  projects,
  selectedProjectId,
  projectForm,
  activeProject,
  loadProjects,
  handleCreateProject,
} = useProjects(setNotice)

// useCanvasData needs scheduleAutoLayout which is defined later - use forwarding wrapper
const canvasData = useCanvasData(
  selectedProjectId,
  setNotice,
  (projectId: string, options: ScheduleAutoLayoutOptions) => scheduleAutoLayout(projectId, options),
)
const {
  areas, devices, devicePorts, devicePortMap, links,
  portAnchorOverrides, portAnchorOverrideMap,
  canvasAreas, canvasDevices, canvasLinks,
  loadProjectData,
  handleAreaAdd, handleAreaChange, handleAreaRemove,
  handleDeviceAdd, handleDeviceChange, handleDeviceRemove,
  createDevicePortRow, updateDevicePortRow, deleteDevicePortRow,
  handleLinkAdd, handleLinkChange, handleLinkRemove,
  upsertAnchorOverride, removeAnchorOverride,
  assignDeviceArea,
  saveAreaPosition,
  saveDevicePosition,
} = canvasData

const selectedId = ref<string | null>(null)
const selectedDraft = ref<any>(null)
const selectedDraftDirty = ref(false)
const selectedSavePending = ref(false)
let syncingDraft = false

type AnchorDraft = {
  side: 'left' | 'right' | 'top' | 'bottom'
  offsetRatio: number
  autoOffset: boolean
}

const anchorDrafts = ref<Record<string, AnchorDraft>>({})
const anchorSwapTargets = ref<Record<string, string>>({})
const positionEditEnabled = ref(false)
const positionSaveSeq = new Map<string, number>()

const effectivePortAnchorMap = computed(() => {
  const map = new Map<string, Map<string, { side: 'left' | 'right' | 'top' | 'bottom'; offsetRatio: number | null }>>()
  devicePorts.value.forEach(port => {
    const deviceMap = map.get(port.device_id) || new Map()
    deviceMap.set(port.name, { side: port.side, offsetRatio: port.offset_ratio ?? null })
    map.set(port.device_id, deviceMap)
  })
  portAnchorOverrideMap.value.forEach((ports, deviceId) => {
    const deviceMap = map.get(deviceId) || new Map()
    ports.forEach((override, portName) => {
      deviceMap.set(portName, override)
    })
    map.set(deviceId, deviceMap)
  })
  return map
})


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

// Viewport interaction không được trigger auto-layout, chỉ cập nhật trạng thái hiển thị.
function handleViewportUpdate(value: Viewport) {
  updateViewport(value)
}

function handleZoomIn() {
  zoomIn()
}

function handleZoomOut() {
  zoomOut()
}

function handleResetViewport() {
  resetViewport()
}

function togglePositionEditMode() {
  const enabled = !positionEditEnabled.value
  positionEditEnabled.value = enabled
  setNotice(
    enabled
      ? 'Đã bật chế độ Sửa vị trí. Kéo-thả đối tượng để lưu vị trí trực tiếp.'
      : 'Đã tắt chế độ Sửa vị trí.',
    'info'
  )
}

function normalizePositionUnits(value: number) {
  return snapUnitsToStandard(value)
}

async function handleCanvasObjectPositionChange(payload: { id: string; type: 'device' | 'area'; x: number; y: number }) {
  if (!selectedProjectId.value) return
  if (!Number.isFinite(payload.x) || !Number.isFinite(payload.y)) return
  const positionX = normalizePositionUnits(payload.x / UNIT_PX)
  const positionY = normalizePositionUnits(payload.y / UNIT_PX)
  const key = `${payload.type}:${payload.id}`
  const seq = (positionSaveSeq.get(key) || 0) + 1
  positionSaveSeq.set(key, seq)

  try {
    if (payload.type === 'area') {
      await saveAreaPosition(payload.id, positionX, positionY)
    } else {
      await saveDevicePosition(payload.id, positionX, positionY)
    }

    if (positionSaveSeq.get(key) !== seq) return
    if (selectedId.value === payload.id && selectedDraft.value && !selectedDraftDirty.value) {
      selectedDraft.value.position_x = positionX
      selectedDraft.value.position_y = positionY
    }
    const objectLabel = payload.type === 'area' ? 'khu vực' : 'thiết bị'
    setNotice(`Đã lưu vị trí ${objectLabel}.`, 'success')
  } catch (error: any) {
    if (positionSaveSeq.get(key) === seq) {
      setNotice(error?.message || 'Lưu vị trí thủ công thất bại.', 'error')
    }
  }
}

const AREA_POSITION_ONLY_KEYS = new Set(['position_x', 'position_y', 'grid_range'])
const DEVICE_POSITION_ONLY_KEYS = new Set(['position_x', 'position_y', 'grid_range'])

function normalizeComparableValue(key: string, value: unknown) {
  if (value == null || value === '') return null
  if (key === 'position_x' || key === 'position_y') {
    const num = Number(value)
    return Number.isFinite(num) ? num : null
  }
  return value
}

function collectChangedKeysForSave(
  objectType: 'Area' | 'Device',
  original: Record<string, any>,
  draft: Record<string, any>,
) {
  const keys = objectType === 'Area'
    ? ['name', 'grid_row', 'grid_col', 'grid_range', 'position_x', 'position_y', 'width', 'height']
    : ['name', 'area_name', 'device_type', 'grid_range', 'position_x', 'position_y', 'width', 'height']

  return keys.filter(key => {
    const left = normalizeComparableValue(key, original[key])
    const right = normalizeComparableValue(key, draft[key])
    return left !== right
  })
}

function isPositionOnlySave(
  objectType: 'Area' | 'Device',
  original: Record<string, any>,
  draft: Record<string, any>,
) {
  const changedKeys = collectChangedKeysForSave(objectType, original, draft)
  if (!changedKeys.length) return true
  const allowSet = objectType === 'Area' ? AREA_POSITION_ONLY_KEYS : DEVICE_POSITION_ONLY_KEYS
  return changedKeys.every(key => allowSet.has(key))
}

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

const selectedDevicePorts = computed(() => {
  if (selectedObjectType.value !== 'Device' || !selectedObject.value) return []
  const deviceId = (selectedObject.value as DeviceRow).id
  const ports = new Set<string>()
  ;(devicePortMap.value.get(deviceId) || []).forEach(port => ports.add(port.name))
  links.value.forEach(link => {
    if (link.from_device_id === deviceId && link.from_port) ports.add(link.from_port)
    if (link.to_device_id === deviceId && link.to_port) ports.add(link.to_port)
  })
  return Array.from(ports).sort(comparePorts)
})

const selectedDeviceOverrideMap = computed(() => {
  if (selectedObjectType.value !== 'Device' || !selectedObject.value) {
    return new Map<string, { side: 'left' | 'right' | 'top' | 'bottom'; offsetRatio: number | null }>()
  }
  const deviceId = (selectedObject.value as DeviceRow).id
  const map = new Map<string, { side: 'left' | 'right' | 'top' | 'bottom'; offsetRatio: number | null }>()
  portAnchorOverrides.value
    .filter(item => item.device_id === deviceId)
    .forEach(item => {
      map.set(item.port_name, { side: item.side, offsetRatio: item.offset_ratio })
    })
  return map
})

const selectedDevicePortDefinitionMap = computed(() => {
  const map = new Map<string, { side: 'left' | 'right' | 'top' | 'bottom'; offsetRatio: number | null }>()
  if (selectedObjectType.value !== 'Device' || !selectedObject.value) {
    return map
  }
  const deviceId = (selectedObject.value as DeviceRow).id
  const ports = devicePortMap.value.get(deviceId) || []
  ports.forEach(port => {
    map.set(port.name, {
      side: port.side,
      offsetRatio: port.offset_ratio ?? null,
    })
  })
  return map
})

watch([selectedDevicePorts, selectedDeviceOverrideMap, selectedDevicePortDefinitionMap], () => {
  if (selectedDevicePorts.value.length === 0) {
    anchorDrafts.value = {}
    anchorSwapTargets.value = {}
    return
  }
  const next: Record<string, AnchorDraft> = {}
  selectedDevicePorts.value.forEach(port => {
    const existing = selectedDeviceOverrideMap.value.get(port) || selectedDevicePortDefinitionMap.value.get(port)
    if (existing) {
      next[port] = {
        side: existing.side,
        offsetRatio: existing.offsetRatio ?? 0.5,
        autoOffset: existing.offsetRatio == null
      }
    } else {
      next[port] = { side: 'right', offsetRatio: 0.5, autoOffset: true }
    }
  })
  anchorDrafts.value = next
  const swapNext: Record<string, string> = {}
  selectedDevicePorts.value.forEach(port => {
    const currentTarget = anchorSwapTargets.value[port]
    swapNext[port] = currentTarget && currentTarget !== port && !!next[currentTarget]
      ? currentTarget
      : ''
  })
  anchorSwapTargets.value = swapNext
})

const hasAnchorOverride = (port: string) => selectedDeviceOverrideMap.value.has(port)
const getAnchorSwapCandidates = (port: string) => selectedDevicePorts.value.filter(candidate => candidate !== port)

function normalizeAnchorOffsetRatio(value: number) {
  if (!Number.isFinite(value)) return 0.5
  if (value < 0) return 0
  if (value > 1) return 1
  return value
}

function buildAnchorOverridePayload(deviceId: string, portName: string, draft: AnchorDraft) {
  return {
    device_id: deviceId,
    port_name: portName,
    side: draft.side,
    offset_ratio: draft.autoOffset ? null : normalizeAnchorOffsetRatio(draft.offsetRatio),
  }
}

function computeAutoAnchorSlotRatios() {
  const buckets: Record<'left' | 'right' | 'top' | 'bottom', string[]> = {
    left: [],
    right: [],
    top: [],
    bottom: [],
  }
  selectedDevicePorts.value.forEach(port => {
    const draft = anchorDrafts.value[port]
    if (!draft) return
    buckets[draft.side].push(port)
  })
  ;(['left', 'right', 'top', 'bottom'] as const).forEach(side => {
    buckets[side].sort(comparePorts)
  })
  const ratioMap = new Map<string, number>()
  ;(['left', 'right', 'top', 'bottom'] as const).forEach(side => {
    const list = buckets[side]
    const total = list.length
    if (!total) return
    list.forEach((port, index) => {
      ratioMap.set(port, (index + 1) / (total + 1))
    })
  })
  return ratioMap
}

function resolveSwapPosition(port: string, slotRatios: Map<string, number>) {
  const draft = anchorDrafts.value[port]
  if (!draft) return null
  if (!draft.autoOffset) {
    return {
      side: draft.side,
      ratio: normalizeAnchorOffsetRatio(draft.offsetRatio),
    }
  }
  return {
    side: draft.side,
    ratio: normalizeAnchorOffsetRatio(slotRatios.get(port) ?? 0.5),
  }
}

const canSwapAnchorWith = (port: string) => {
  const target = anchorSwapTargets.value[port]
  return !!target && target !== port && !!anchorDrafts.value[port] && !!anchorDrafts.value[target]
}

async function swapAnchorWith(port: string) {
  if (!selectedProjectId.value || selectedObjectType.value !== 'Device' || !selectedObject.value) return
  const targetPort = (anchorSwapTargets.value[port] || '').trim()
  if (!targetPort || targetPort === port) {
    setNotice('Cần chọn port đích để đổi vị trí.', 'error')
    return
  }

  const sourceDraft = anchorDrafts.value[port]
  const targetDraft = anchorDrafts.value[targetPort]
  if (!sourceDraft || !targetDraft) {
    setNotice('Không tìm thấy dữ liệu anchor của 2 port cần đổi.', 'error')
    return
  }

  const deviceId = (selectedObject.value as DeviceRow).id
  const previousSource = { ...sourceDraft }
  const previousTarget = { ...targetDraft }
  const slotRatios = computeAutoAnchorSlotRatios()
  const sourcePosition = resolveSwapPosition(port, slotRatios)
  const targetPosition = resolveSwapPosition(targetPort, slotRatios)
  if (!sourcePosition || !targetPosition) {
    setNotice('Không thể xác định vị trí hiện tại của port để đổi.', 'error')
    return
  }
  const nextSource: AnchorDraft = {
    side: targetPosition.side,
    offsetRatio: targetPosition.ratio,
    autoOffset: false,
  }
  const nextTarget: AnchorDraft = {
    side: sourcePosition.side,
    offsetRatio: sourcePosition.ratio,
    autoOffset: false,
  }

  anchorDrafts.value[port] = nextSource
  anchorDrafts.value[targetPort] = nextTarget

  try {
    await upsertAnchorOverride(selectedProjectId.value, buildAnchorOverridePayload(deviceId, port, nextSource))
    try {
      await upsertAnchorOverride(selectedProjectId.value, buildAnchorOverridePayload(deviceId, targetPort, nextTarget))
    } catch (error) {
      await upsertAnchorOverride(selectedProjectId.value, buildAnchorOverridePayload(deviceId, port, previousSource)).catch(() => {})
      throw error
    }

    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'anchor-crud' })
    anchorSwapTargets.value[port] = ''
    anchorSwapTargets.value[targetPort] = ''
    setNotice(`Đã đổi vị trí anchor giữa '${port}' và '${targetPort}'.`, 'success')
  } catch (error: any) {
    anchorDrafts.value[port] = previousSource
    anchorDrafts.value[targetPort] = previousTarget
    setNotice(error?.message || 'Đổi vị trí anchor thất bại.', 'error')
  }
}

async function saveAnchorOverride(port: string) {
  if (!selectedProjectId.value || selectedObjectType.value !== 'Device' || !selectedObject.value) return
  const deviceId = (selectedObject.value as DeviceRow).id
  const draft = anchorDrafts.value[port]
  if (!draft) return
  try {
    await upsertAnchorOverride(selectedProjectId.value, buildAnchorOverridePayload(deviceId, port, draft))
    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'anchor-crud' })
    setNotice('Đã lưu override anchor.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Lưu override anchor thất bại.', 'error')
  }
}

async function clearAnchorOverride(port: string) {
  if (!selectedProjectId.value || selectedObjectType.value !== 'Device' || !selectedObject.value) return
  const deviceId = (selectedObject.value as DeviceRow).id
  try {
    await removeAnchorOverride(selectedProjectId.value, deviceId, port)
    const base = selectedDevicePortDefinitionMap.value.get(port)
    anchorDrafts.value[port] = {
      side: base?.side || 'right',
      offsetRatio: base?.offsetRatio ?? 0.5,
      autoOffset: base?.offsetRatio == null
    }
    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'anchor-crud' })
    setNotice('Đã xóa override anchor.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Xóa override anchor thất bại.', 'error')
  }
}

async function createDevicePortEntry() {
  if (!selectedProjectId.value || !selectedDeviceId.value) return
  const name = newPortDraft.value.name.trim()
  if (!name) {
    setNotice('Cần nhập tên port.', 'error')
    return
  }
  const duplicated = selectedDevicePortRows.value.some(port => port.name === name)
  if (duplicated) {
    setNotice(`Port '${name}' đã tồn tại trên thiết bị.`, 'error')
    return
  }
  try {
    await createDevicePortRow(selectedProjectId.value, selectedDeviceId.value, {
      name,
      side: newPortDraft.value.side,
      offset_ratio: null,
    })
    newPortDraft.value = { name: '', side: 'bottom' }
    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'device-crud' })
    setNotice('Đã thêm port.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Thêm port thất bại.', 'error')
  }
}

async function saveDevicePort(portId: string) {
  if (!selectedProjectId.value || !selectedDeviceId.value) return
  const draft = portDrafts.value[portId]
  if (!draft) return
  const name = draft.name.trim()
  if (!name) {
    setNotice('Tên port không được để trống.', 'error')
    return
  }
  const duplicated = selectedDevicePortRows.value.some(port => port.id !== portId && port.name === name)
  if (duplicated) {
    setNotice(`Port '${name}' đã tồn tại trên thiết bị.`, 'error')
    return
  }
  try {
    await updateDevicePortRow(selectedProjectId.value, selectedDeviceId.value, portId, {
      name,
      side: draft.side,
      offset_ratio: null,
    })
    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'device-crud' })
    setNotice('Đã lưu port.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Lưu port thất bại.', 'error')
  }
}

async function removeDevicePort(portId: string) {
  if (!selectedProjectId.value || !selectedDeviceId.value) return
  if (!confirm('Bạn có chắc muốn xóa port này?')) return
  try {
    await deleteDevicePortRow(selectedProjectId.value, selectedDeviceId.value, portId)
    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'device-crud' })
    setNotice('Đã xóa port.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Xóa port thất bại.', 'error')
  }
}

type PortLinkDirection = 'from' | 'to'
type PortLinkEntry = {
  port: string
  links: Array<{
    linkId: string
    direction: PortLinkDirection
    otherDeviceId: string
    otherPort: string
    purpose: string
    lineStyle: 'solid' | 'dashed' | 'dotted'
  }>
}

const selectedDeviceId = computed(() => {
  if (selectedObjectType.value !== 'Device' || !selectedObject.value) return null
  return (selectedObject.value as DeviceRow).id
})

const selectedDeviceName = computed(() => {
  if (selectedObjectType.value !== 'Device' || !selectedObject.value) return null
  return (selectedObject.value as DeviceRow).name
})

const selectedDevicePortRows = computed<DevicePortRow[]>(() => {
  if (!selectedDeviceId.value) return []
  return devicePortMap.value.get(selectedDeviceId.value) || []
})

const portDrafts = ref<Record<string, { name: string; side: 'top' | 'bottom' | 'left' | 'right' }>>({})
const newPortDraft = ref<{ name: string; side: 'top' | 'bottom' | 'left' | 'right' }>({
  name: '',
  side: 'bottom',
})

watch(selectedDevicePortRows, rows => {
  const next: Record<string, { name: string; side: 'top' | 'bottom' | 'left' | 'right' }> = {}
  rows.forEach(port => {
    next[port.id] = {
      name: port.name,
      side: port.side,
    }
  })
  portDrafts.value = next
})

const deviceNameById = computed(() => {
  return new Map(devices.value.map(device => [device.id, device.name]))
})

const linkLineStyles: Array<'solid' | 'dashed' | 'dotted'> = ['solid', 'dashed', 'dotted']
const peerControlPurposes = ['STACK', 'HA', 'HSRP'] as const
type PeerControlPurpose = (typeof peerControlPurposes)[number]
const peerControlVisualMap: Record<PeerControlPurpose, { color: string; lineStyle: 'solid' | 'dashed' | 'dotted'; note: string }> = {
  STACK: {
    color: '#2d8cf0',
    lineStyle: 'solid',
    note: 'Kết nối stack/stackwise giữa cặp thiết bị',
  },
  HA: {
    color: '#16a085',
    lineStyle: 'dashed',
    note: 'Heartbeat / đồng bộ HA',
  },
  HSRP: {
    color: '#9b59b6',
    lineStyle: 'dotted',
    note: 'Kết nối điều khiển HSRP',
  },
}

const deviceIdByName = computed(() => {
  return new Map(devices.value.map(device => [device.name, device.id]))
})

const areaNameOptions = computed(() =>
  areas.value.map(area => ({ value: area.name, label: area.name }))
)
const deviceNameOptions = computed(() =>
  devices.value.map(device => ({ value: device.name, label: device.name }))
)
const deviceTypeOptions = deviceTypes.map(type => ({ value: type, label: type }))
const linkPurposeOptions = linkPurposes.map(purpose => ({ value: purpose, label: purpose }))
const linkLineStyleOptions = linkLineStyles.map(style => ({ value: style, label: style }))

const areaColumns: ColumnDef[] = [
  { key: 'name', label: 'Tên' },
  { key: 'grid_range', label: 'Grid range', width: '160px' },
  { key: 'grid_row', label: 'Hàng', type: 'number', width: '72px' },
  { key: 'grid_col', label: 'Cột', type: 'number', width: '72px' },
  { key: 'width', label: 'Rộng', type: 'number', width: '80px' },
  { key: 'height', label: 'Cao', type: 'number', width: '80px' },
]

const deviceColumns = computed<ColumnDef[]>(() => [
  { key: 'name', label: 'Tên' },
  { key: 'area_name', label: 'Area', type: 'select', options: areaNameOptions.value },
  { key: 'device_type', label: 'Loại', type: 'select', options: deviceTypeOptions },
  { key: 'grid_range', label: 'Grid range', width: '160px' },
  { key: 'width', label: 'Rộng', type: 'number', width: '80px' },
  { key: 'height', label: 'Cao', type: 'number', width: '80px' },
])

const linkColumns = computed<ColumnDef[]>(() => [
  { key: 'from_device_name', label: 'Nguồn', type: 'select', options: deviceNameOptions.value },
  { key: 'from_port', label: 'Port nguồn' },
  { key: 'to_device_name', label: 'Đích', type: 'select', options: deviceNameOptions.value },
  { key: 'to_port', label: 'Port đích' },
  { key: 'purpose', label: 'Mục đích', type: 'select', options: linkPurposeOptions },
  { key: 'line_style', label: 'Kiểu', type: 'select', options: linkLineStyleOptions },
])

const nextPortForDevice = (deviceId: string, offset = 0) => {
  const declared = (devicePortMap.value.get(deviceId) || []).map(port => port.name).sort(comparePorts)
  if (declared.length > 0) {
    const used = new Set<string>()
    links.value.forEach(link => {
      if (link.from_device_id === deviceId) used.add(link.from_port)
      if (link.to_device_id === deviceId) used.add(link.to_port)
    })
    const available = declared.filter(port => !used.has(port))
    if (available.length > 0) {
      return available[Math.min(offset, available.length - 1)]
    }
    return declared[Math.min(offset, declared.length - 1)]
  }

  let maxIndex = 0
  links.value.forEach(link => {
    if (link.from_device_id === deviceId) {
      const idx = extractPortIndex(link.from_port)
      if (idx && idx > maxIndex) maxIndex = idx
    }
    if (link.to_device_id === deviceId) {
      const idx = extractPortIndex(link.to_port)
      if (idx && idx > maxIndex) maxIndex = idx
    }
  })
  const nextIndex = Math.max(1, maxIndex + 1 + offset)
  return `Gi 0/${nextIndex}`
}

const defaultAreaRow = computed(() => ({
  ...(function () {
    const row = Math.max(1, areas.value.length + 1)
    const start = formatExcelCell(1, row)
    const end = formatExcelCell(14, row + 5)
    return { grid_range: `${start}:${end}` }
  })(),
  name: `Area ${areas.value.length + 1}`,
  grid_row: Math.max(1, areas.value.length + 1),
  grid_col: 1,
  width: 3,
  height: 1.5,
  __temp: true
}))

const defaultDeviceRow = computed(() => ({
  ...(function () {
    const idx = devices.value.length
    const colStart = 1 + (idx % 8) * 3
    const rowStart = 1 + Math.floor(idx / 8) * 3
    const start = formatExcelCell(colStart, rowStart)
    const end = formatExcelCell(colStart + 3, rowStart + 1)
    return { grid_range: `${start}:${end}` }
  })(),
  name: `Device ${devices.value.length + 1}`,
  area_name: areas.value[0]?.name || '',
  device_type: 'Switch',
  width: 1.2,
  height: 0.5,
  __temp: true
}))

const defaultLinkRow = computed(() => {
  const fromName = devices.value[0]?.name || ''
  const toName = devices.value[1]?.name || devices.value[0]?.name || ''
  const fromId = deviceIdByName.value.get(fromName)
  const toId = deviceIdByName.value.get(toName)
  const fromPort = fromId ? nextPortForDevice(fromId) : 'Gi 0/1'
  const toPort = toId ? nextPortForDevice(toId, fromId === toId ? 1 : 0) : 'Gi 0/2'
  return {
    from_device_name: fromName,
    from_port: fromPort,
    to_device_name: toName,
    to_port: toPort,
    purpose: 'DEFAULT',
    line_style: 'solid',
    __temp: true
  }
})

const canAddDevice = computed(() => areas.value.length > 0)
const canAddLink = computed(() => devices.value.length > 1)

const updateAreaRows = (rows: AreaRow[]) => { areas.value = rows }
const updateDeviceRows = (rows: DeviceRow[]) => { devices.value = rows }
const updateLinkRows = (rows: LinkRow[]) => { links.value = rows }

const targetDeviceOptions = computed(() => {
  if (!selectedDeviceId.value) return devices.value
  return devices.value.filter(device => device.id !== selectedDeviceId.value)
})

const selectedDeviceLinkEntries = computed<PortLinkEntry[]>(() => {
  if (!selectedDeviceId.value) return []
  const map = new Map<string, PortLinkEntry>()
  links.value.forEach(link => {
    if (link.from_device_id === selectedDeviceId.value) {
      const entry = map.get(link.from_port) || { port: link.from_port, links: [] }
      entry.links.push({
        linkId: link.id,
        direction: 'from',
        otherDeviceId: link.to_device_id,
        otherPort: link.to_port,
        purpose: link.purpose || 'DEFAULT',
        lineStyle: (link.line_style || 'solid') as 'solid' | 'dashed' | 'dotted'
      })
      map.set(link.from_port, entry)
      return
    }
    if (link.to_device_id === selectedDeviceId.value) {
      const entry = map.get(link.to_port) || { port: link.to_port, links: [] }
      entry.links.push({
        linkId: link.id,
        direction: 'to',
        otherDeviceId: link.from_device_id,
        otherPort: link.from_port,
        purpose: link.purpose || 'DEFAULT',
        lineStyle: (link.line_style || 'solid') as 'solid' | 'dashed' | 'dotted'
      })
      map.set(link.to_port, entry)
    }
  })
  return Array.from(map.values()).sort((a, b) => comparePorts(a.port, b.port))
})

const linkDrafts = ref<Record<string, {
  targetDeviceId: string | null
  targetPort: string
  purpose: string
  lineStyle: 'solid' | 'dashed' | 'dotted'
}>>({})

const newLinkDraft = ref({
  port: '',
  targetDeviceId: null as string | null,
  targetPort: '',
  purpose: 'DEFAULT',
  lineStyle: 'solid' as 'solid' | 'dashed' | 'dotted'
})

const peerLinkDraft = ref<{
  fromDeviceId: string | null
  fromPort: string
  toDeviceId: string | null
  toPort: string
  purpose: PeerControlPurpose
}>({
  fromDeviceId: null,
  fromPort: '',
  toDeviceId: null,
  toPort: '',
  purpose: 'STACK',
})

const peerLegendItems = computed(() =>
  peerControlPurposes.map(purpose => {
    const visual = peerControlVisualMap[purpose]
    return {
      purpose,
      note: visual.note,
      swatchStyle: {
        '--peer-color': visual.color,
        '--peer-dash': visual.lineStyle === 'solid' ? 'none' : (visual.lineStyle === 'dashed' ? 'dashed' : 'dotted'),
      } as Record<string, string>,
    }
  })
)

watch(selectedDeviceLinkEntries, () => {
  const next: Record<string, { targetDeviceId: string | null; targetPort: string; purpose: string; lineStyle: 'solid' | 'dashed' | 'dotted' }> = {}
  selectedDeviceLinkEntries.value.forEach(entry => {
    entry.links.forEach(link => {
      next[link.linkId] = {
        targetDeviceId: link.otherDeviceId,
        targetPort: link.otherPort,
        purpose: link.purpose || 'DEFAULT',
        lineStyle: link.lineStyle || 'solid'
      }
    })
  })
  linkDrafts.value = next
})

watch(selectedDeviceId, () => {
  newLinkDraft.value = {
    port: '',
    targetDeviceId: null,
    targetPort: '',
    purpose: 'DEFAULT',
    lineStyle: 'solid'
  }
  newPortDraft.value = {
    name: '',
    side: 'bottom'
  }
})

function isPortInUse(deviceId: string, port: string, excludeLinkId?: string) {
  const normalized = port.trim()
  return links.value.some(link => {
    if (excludeLinkId && link.id === excludeLinkId) return false
    if (link.from_device_id === deviceId && link.from_port === normalized) return true
    return link.to_device_id === deviceId && link.to_port === normalized
  })
}

function isDuplicateLink(
  fromDeviceId: string,
  fromPort: string,
  toDeviceId: string,
  toPort: string,
  excludeLinkId?: string
) {
  const fromPortNorm = fromPort.trim()
  const toPortNorm = toPort.trim()
  return links.value.some(link => {
    if (excludeLinkId && link.id === excludeLinkId) return false
    const direct = link.from_device_id === fromDeviceId
      && link.from_port === fromPortNorm
      && link.to_device_id === toDeviceId
      && link.to_port === toPortNorm
    const reverse = link.from_device_id === toDeviceId
      && link.from_port === toPortNorm
      && link.to_device_id === fromDeviceId
      && link.to_port === fromPortNorm
    return direct || reverse
  })
}

function validatePortFormat(port: string) {
  return /^[A-Za-z][A-Za-z0-9 _./-]*$/.test(port.trim())
}

function isDeclaredPort(deviceId: string, port: string) {
  const normalized = port.trim()
  const declared = devicePortMap.value.get(deviceId) || []
  return declared.some(item => item.name === normalized)
}

function validateLinkDraft(params: {
  fromDeviceId: string
  fromPort: string
  toDeviceId: string | null
  toPort: string
  excludeLinkId?: string
}) {
  const { fromDeviceId, fromPort, toDeviceId, toPort, excludeLinkId } = params
  if (!toDeviceId) return 'Cần chọn thiết bị đích.'
  if (!fromPort.trim()) return 'Cần nhập port nguồn.'
  if (!toPort.trim()) return 'Cần nhập port đích.'
  if (!validatePortFormat(fromPort)) return 'Port nguồn không hợp lệ (vd: Gi 0/1).'
  if (!validatePortFormat(toPort)) return 'Port đích không hợp lệ (vd: Gi 0/24).'
  if (!isDeclaredPort(fromDeviceId, fromPort)) {
    return `Port nguồn '${fromPort.trim()}' chưa khai báo trên thiết bị.`
  }
  if (!isDeclaredPort(toDeviceId, toPort)) {
    return `Port đích '${toPort.trim()}' chưa khai báo trên thiết bị.`
  }
  if (fromDeviceId === toDeviceId && fromPort.trim() === toPort.trim()) {
    return 'Không thể nối cùng một port.'
  }
  if (isDuplicateLink(fromDeviceId, fromPort, toDeviceId, toPort, excludeLinkId)) {
    return 'Link đã tồn tại.'
  }
  if (isPortInUse(fromDeviceId, fromPort, excludeLinkId)) {
    return `Port '${fromPort.trim()}' trên thiết bị nguồn đã được sử dụng.`
  }
  if (isPortInUse(toDeviceId, toPort, excludeLinkId)) {
    return `Port '${toPort.trim()}' trên thiết bị đích đã được sử dụng.`
  }
  return null
}

async function savePortLink(entry: { linkId: string; direction: PortLinkDirection; port: string }) {
  if (!selectedProjectId.value || !selectedDeviceId.value || !selectedDeviceName.value) return
  const draft = linkDrafts.value[entry.linkId]
  if (!draft) return
  const error = validateLinkDraft({
    fromDeviceId: selectedDeviceId.value,
    fromPort: entry.port,
    toDeviceId: draft.targetDeviceId,
    toPort: draft.targetPort,
    excludeLinkId: entry.linkId
  })
  if (error) {
    setNotice(error, 'error')
    return
  }

  const targetName = draft.targetDeviceId ? deviceNameById.value.get(draft.targetDeviceId) : null
  if (!targetName) {
    setNotice('Không tìm thấy thiết bị đích.', 'error')
    return
  }

  const payload: Record<string, any> = {
    purpose: draft.purpose || 'DEFAULT',
    line_style: draft.lineStyle || 'solid'
  }
  if (entry.direction === 'from') {
    payload.to_device = targetName
    payload.to_port = draft.targetPort.trim()
  } else {
    payload.from_device = targetName
    payload.from_port = draft.targetPort.trim()
  }

  try {
    const updated = await updateLink(selectedProjectId.value, entry.linkId, payload)
    const index = links.value.findIndex(link => link.id === updated.id)
    if (index >= 0) links.value[index] = updated
    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'port-link-crud' })
    setNotice('Đã cập nhật link.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Cập nhật link thất bại.', 'error')
  }
}

async function removePortLink(entry: { linkId: string }) {
  if (!selectedProjectId.value) return
  if (!confirm('Bạn có chắc muốn xóa link này?')) return
  try {
    await deleteLink(selectedProjectId.value, entry.linkId)
    links.value = links.value.filter(link => link.id !== entry.linkId)
    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'port-link-crud' })
    setNotice('Đã xóa link.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Xóa link thất bại.', 'error')
  }
}

async function createPortLink() {
  if (!selectedProjectId.value || !selectedDeviceId.value || !selectedDeviceName.value) return
  const draft = newLinkDraft.value
  const error = validateLinkDraft({
    fromDeviceId: selectedDeviceId.value,
    fromPort: draft.port,
    toDeviceId: draft.targetDeviceId,
    toPort: draft.targetPort,
  })
  if (error) {
    setNotice(error, 'error')
    return
  }

  const targetName = draft.targetDeviceId ? deviceNameById.value.get(draft.targetDeviceId) : null
  if (!targetName) {
    setNotice('Không tìm thấy thiết bị đích.', 'error')
    return
  }

  try {
    const created = await createLink(selectedProjectId.value, {
      from_device: selectedDeviceName.value,
      from_port: draft.port.trim(),
      to_device: targetName,
      to_port: draft.targetPort.trim(),
      purpose: draft.purpose || 'DEFAULT',
      line_style: draft.lineStyle || 'solid'
    })
    links.value.push(created)
    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'port-link-crud' })
    newLinkDraft.value = {
      port: '',
      targetDeviceId: null,
      targetPort: '',
      purpose: 'DEFAULT',
      lineStyle: 'solid'
    }
    setNotice('Đã tạo link.', 'success')
  } catch (error: any) {
    setNotice(error?.message || 'Tạo link thất bại.', 'error')
  }
}

async function createPeerControlLink() {
  if (!selectedProjectId.value) {
    setNotice('Vui lòng chọn project trước.', 'error')
    return
  }

  const draft = peerLinkDraft.value
  const fromDeviceId = draft.fromDeviceId
  const toDeviceId = draft.toDeviceId
  if (!fromDeviceId || !toDeviceId) {
    setNotice('Cần chọn đủ thiết bị nguồn/đích.', 'error')
    return
  }

  const error = validateLinkDraft({
    fromDeviceId,
    fromPort: draft.fromPort,
    toDeviceId,
    toPort: draft.toPort,
  })
  if (error) {
    setNotice(error, 'error')
    return
  }

  const fromName = deviceNameById.value.get(fromDeviceId)
  const toName = deviceNameById.value.get(toDeviceId)
  if (!fromName || !toName) {
    setNotice('Không tìm thấy thiết bị nguồn/đích.', 'error')
    return
  }

  const visual = peerControlVisualMap[draft.purpose]
  try {
    const created = await createLink(selectedProjectId.value, {
      from_device: fromName,
      from_port: draft.fromPort.trim(),
      to_device: toName,
      to_port: draft.toPort.trim(),
      purpose: draft.purpose,
      line_style: visual.lineStyle,
    })
    links.value.push(created)
    scheduleAutoLayout(selectedProjectId.value, { force: true, reason: 'link-crud' })
    setNotice(`Đã tạo kết nối ${draft.purpose}.`, 'success')
    peerLinkDraft.value = {
      fromDeviceId: fromDeviceId,
      fromPort: '',
      toDeviceId: toDeviceId,
      toPort: '',
      purpose: draft.purpose,
    }
  } catch (error: any) {
    setNotice(error?.message || 'Tạo kết nối peer-control thất bại.', 'error')
  }
}

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

function hasStableProjectLayout() {
  if (!devices.value.length) return false
  const areaStable = areas.value.every(area =>
    !!area.grid_range || (area.position_x != null && area.position_y != null)
  )
  const deviceStable = devices.value.every(device =>
    !!device.grid_range || (device.position_x != null && device.position_y != null)
  )
  return areaStable && deviceStable
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
      positionEditEnabled.value = false
      positionSaveSeq.clear()
      peerLinkDraft.value = {
        fromDeviceId: null,
        fromPort: '',
        toDeviceId: null,
        toPort: '',
        purpose: 'STACK',
      }
      resetLayoutConfig()
      projects.value = []
      selectedProjectId.value = null
      areas.value = []
      devices.value = []
      devicePorts.value = []
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
  const originalObject = selectedObject.value ? cloneRow(selectedObject.value) : null
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
      const normalizedPositionX = normalizePositionUnits(Number(selectedDraft.value.position_x || 0))
      const normalizedPositionY = normalizePositionUnits(Number(selectedDraft.value.position_y || 0))
      updated = await updateArea(projectId as string, selectedDraft.value.id, {
        name: selectedDraft.value.name,
        grid_row: selectedDraft.value.grid_row,
        grid_col: selectedDraft.value.grid_col,
        grid_range: selectedDraft.value.grid_range || undefined,
        position_x: normalizedPositionX,
        position_y: normalizedPositionY,
        width: selectedDraft.value.width,
        height: selectedDraft.value.height,
        style: selectedDraft.value.style || undefined
      })
      const index = areas.value.findIndex(area => area.id === selectedDraft.value.id)
      if (index >= 0 && updated) areas.value[index] = updated as AreaRow
    } else if (objectType === 'Device') {
      const normalizedPositionX = normalizePositionUnits(Number(selectedDraft.value.position_x || 0))
      const normalizedPositionY = normalizePositionUnits(Number(selectedDraft.value.position_y || 0))
      updated = await updateDevice(projectId as string, selectedDraft.value.id, {
        name: selectedDraft.value.name,
        area_name: selectedDraft.value.area_name || undefined,
        device_type: selectedDraft.value.device_type,
        grid_range: selectedDraft.value.grid_range || undefined,
        position_x: normalizedPositionX,
        position_y: normalizedPositionY,
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
      let shouldRunAutoLayout = objectType === 'Link'
      if ((objectType === 'Area' || objectType === 'Device') && originalObject) {
        shouldRunAutoLayout = !isPositionOnlySave(
          objectType as 'Area' | 'Device',
          originalObject as Record<string, any>,
          selectedDraft.value as Record<string, any>
        )
      }
      if (shouldRunAutoLayout) {
        const reasonByType = {
          Area: 'area-crud',
          Device: 'device-crud',
          Link: 'link-crud',
        } as const
        scheduleAutoLayout(projectId, { force: true, reason: reasonByType[objectType as 'Area' | 'Device' | 'Link'] })
      }
      selectedDraft.value = cloneRow(updated)
      selectedDraftDirty.value = false
      setNotice(
        shouldRunAutoLayout ? 'Đã lưu thay đổi. Bố cục sẽ được cập nhật tự động.' : 'Đã lưu thay đổi.',
        'success'
      )
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
  positionEditEnabled.value = false
  positionSaveSeq.clear()
  peerLinkDraft.value = {
    fromDeviceId: null,
    fromPort: '',
    toDeviceId: null,
    toPort: '',
    purpose: 'STACK',
  }

  if (projectId) {
    await loadProjectData(projectId)
    if (!hasStableProjectLayout()) {
      scheduleAutoLayout(projectId, { force: true, reason: 'project-open' })
    }
  } else {
    areas.value = []
    devices.value = []
    devicePorts.value = []
    links.value = []
  }
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
  display: grid;
  gap: 12px;
  background: var(--panel);
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  padding: 18px 22px;
  box-shadow: var(--shadow);
}

.topbar-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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

.topbar-nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px;
  background: #faf6f2;
  border-radius: 12px;
  border: 1px solid rgba(28, 28, 28, 0.1);
  width: fit-content;
  max-width: 100%;
  margin: 0 auto;
}

.topbar-nav button {
  border-radius: 10px;
  border: 1px solid transparent;
  padding: 6px 10px;
  cursor: pointer;
  background: #efe7df;
  font-size: 12px;
}

.topbar-nav .ghost {
  background: transparent;
  border-color: #dccfc4;
}

.topbar-nav button.active {
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

.layout-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.layout-actions button {
  width: 100%;
}

.data-content {
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

.hint.small {
  margin-top: 6px;
  padding: 6px 8px;
  font-size: 12px;
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

.peer-link-editor {
  display: grid;
  gap: 10px;
}

.peer-link-actions {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.peer-link-actions button {
  width: 100%;
}

.peer-legend {
  display: grid;
  gap: 8px;
  padding: 10px;
  border-radius: 10px;
  background: #f6f2ef;
}

.peer-legend-row {
  display: grid;
  grid-template-columns: 46px 64px 1fr;
  align-items: center;
  gap: 8px;
}

.peer-legend-line {
  display: inline-block;
  width: 42px;
  height: 0;
  border-top: 2px var(--peer-dash, solid) var(--peer-color, #2b2a28);
}

.peer-legend-title {
  font-size: 12px;
  font-weight: 600;
  color: #303030;
}

.peer-legend-note {
  font-size: 12px;
  color: var(--muted);
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

.port-editor {
  display: grid;
  gap: 10px;
}

.port-editor-list {
  display: grid;
  gap: 8px;
}

.port-editor-row {
  display: grid;
  grid-template-columns: 1fr 120px auto auto;
  gap: 8px;
  align-items: center;
}

.port-editor-create {
  display: grid;
  grid-template-columns: 1fr 120px auto;
  gap: 8px;
  align-items: center;
}

.anchor-override-list {
  display: grid;
  gap: 8px;
}

.anchor-override-row {
  display: grid;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f6f2ef;
}

.anchor-port-name {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--muted);
}

.anchor-controls {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto auto;
  gap: 8px;
  align-items: center;
}

.anchor-swap-controls {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: center;
}

.anchor-auto {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--muted);
}

.port-link-list {
  display: grid;
  gap: 10px;
}

.port-link-group {
  display: grid;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f6f2ef;
}

.port-link-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--muted);
}

.port-link-row {
  display: grid;
  gap: 6px;
}

.port-link-controls {
  display: grid;
  grid-template-columns: 1.2fr 1fr 0.9fr 0.8fr;
  gap: 8px;
  align-items: center;
}

.port-link-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.new-link-controls {
  display: grid;
  grid-template-columns: 1fr 1.2fr 1fr 0.9fr 0.8fr auto;
  gap: 8px;
  align-items: center;
}

.badge {
  padding: 2px 6px;
  border-radius: 8px;
  background: #f3d7b8;
  color: #5a3b1d;
  font-size: 10px;
  text-transform: uppercase;
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
