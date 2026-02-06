import { ref, type Ref, type ComputedRef } from 'vue'
import { autoLayout, invalidateLayoutCache } from '../services/layout'
import { DEFAULT_LAYOUT_TUNING } from './canvasConstants'
import type { AreaRow, DeviceRow } from './useCanvasData'

export function useAutoLayout(deps: {
  areas: Ref<AreaRow[]>
  devices: Ref<DeviceRow[]>
  links: Ref<{ id: string }[]>
  activeProject: ComputedRef<{ id: string } | null>
  layoutTuning: ComputedRef<Record<string, any>>
  setNotice: (msg: string, type: 'info' | 'success' | 'error') => void
  loadProjectData: (projectId: string) => Promise<void>
}) {
  const autoLayoutAutoApplying = ref(false)
  const autoLayoutManualApplying = ref(false)
  const autoLayoutAutoAppliedProjects = new Set<string>()
  let autoLayoutTimer: number | null = null

  function computeAutoLayoutTuning() {
    const tuning = deps.layoutTuning.value
    const layer_gap = Number((tuning.layer_gap ?? DEFAULT_LAYOUT_TUNING.layer_gap).toFixed(2))
    const node_spacing = Number((tuning.node_spacing ?? DEFAULT_LAYOUT_TUNING.node_spacing).toFixed(2))
    return { layer_gap, node_spacing }
  }

  function hasStoredLayout() {
    const epsilon = 0.0001
    const deviceHasLayout = deps.devices.value.some(device =>
      Math.abs(device.position_x ?? 0) > epsilon || Math.abs(device.position_y ?? 0) > epsilon
    )
    const areaHasLayout = deps.areas.value.some(area =>
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
    if (!deps.devices.value.length) return
    if (!force && hasStoredLayout()) {
      autoLayoutAutoAppliedProjects.add(projectId)
      return
    }

    const hasAreas = deps.areas.value.length > 0
    if (!hasAreas && !deps.links.value.length) return

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
        normalize_topology: false
      })
      autoLayoutAutoAppliedProjects.add(projectId)
      await deps.loadProjectData(projectId)
      await invalidateLayoutCache(projectId)
      deps.setNotice('Auto-layout đã được áp dụng tự động.', 'success')
    } catch (error: any) {
      deps.setNotice(error?.message || 'Auto-layout tự động thất bại.', 'error')
    } finally {
      autoLayoutAutoApplying.value = false
    }
  }

  async function runAutoLayoutManual() {
    if (!deps.activeProject.value || autoLayoutManualApplying.value) return
    if (!deps.devices.value.length) {
      deps.setNotice('Chưa có thiết bị để chạy auto-layout.', 'error')
      return
    }

    autoLayoutManualApplying.value = true
    const projectId = deps.activeProject.value.id
    const hasAreas = deps.areas.value.length > 0
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
        normalize_topology: false
      })
      autoLayoutAutoAppliedProjects.add(projectId)
      await deps.loadProjectData(projectId)
      await invalidateLayoutCache(projectId)
      deps.setNotice('Đã chạy lại auto-layout.', 'success')
    } catch (error: any) {
      deps.setNotice(error?.message || 'Chạy lại auto-layout thất bại.', 'error')
    } finally {
      autoLayoutManualApplying.value = false
    }
  }

  return {
    autoLayoutAutoApplying,
    autoLayoutManualApplying,
    scheduleAutoLayout,
    runAutoLayoutAuto,
    runAutoLayoutManual,
  }
}
