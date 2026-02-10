import { onBeforeUnmount, ref, type Ref, type ComputedRef } from 'vue'
import { autoLayout, invalidateLayoutCache } from '../services/layout'
import { DEFAULT_LAYOUT_TUNING } from './canvasConstants'
import type { AreaRow, DeviceRow } from './useCanvasData'

export type AutoLayoutReason =
  | 'project-open'
  | 'area-crud'
  | 'device-crud'
  | 'link-crud'
  | 'port-link-crud'
  | 'anchor-crud'
  | 'manual'

export type ScheduleAutoLayoutOptions = {
  reason: AutoLayoutReason | string
  force?: boolean
}

type AutoLayoutRequest = {
  reason: AutoLayoutReason
  force: boolean
  preserveExistingPositions?: boolean
}

const AUTO_LAYOUT_REASONS = new Set<AutoLayoutReason>([
  'project-open',
  'area-crud',
  'device-crud',
  'link-crud',
  'port-link-crud',
  'anchor-crud',
  'manual',
])

function isAutoLayoutReason(value: string): value is AutoLayoutReason {
  return AUTO_LAYOUT_REASONS.has(value as AutoLayoutReason)
}

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
  const autoLayoutRunningProjects = new Set<string>()
  const autoLayoutDebounceTimers = new Map<string, number>()
  const autoLayoutLatestRequests = new Map<string, AutoLayoutRequest>()
  const autoLayoutPendingReruns = new Map<string, AutoLayoutRequest>()

  function computeAutoLayoutTuning() {
    const tuning = deps.layoutTuning.value
    const layer_gap = Number((tuning.layer_gap ?? DEFAULT_LAYOUT_TUNING.layer_gap).toFixed(2))
    const node_spacing = Number((tuning.node_spacing ?? DEFAULT_LAYOUT_TUNING.node_spacing).toFixed(2))
    return { layer_gap, node_spacing }
  }

  function clearDebounceTimer(projectId: string) {
    const timer = autoLayoutDebounceTimers.get(projectId)
    if (!timer) return
    window.clearTimeout(timer)
    autoLayoutDebounceTimers.delete(projectId)
  }

  async function executeAutoLayout(projectId: string, request: AutoLayoutRequest) {
    if (!deps.devices.value.length) return false

    const hasAreas = deps.areas.value.length > 0
    if (!hasAreas && !deps.links.value.length) return false

    const tuning = computeAutoLayoutTuning()
    await autoLayout(projectId, {
      layer_gap: tuning.layer_gap,
      node_spacing: tuning.node_spacing,
      apply_to_db: true,
      group_by_area: hasAreas,
      layout_scope: 'project',
      anchor_routing: true,
      overview_mode: 'l1-only',
      normalize_topology: false,
      preserve_existing_positions: !!request.preserveExistingPositions,
    })
    await deps.loadProjectData(projectId)
    await invalidateLayoutCache(projectId)
    return true
  }

  async function flushAutoLayout(projectId: string) {
    const request = autoLayoutLatestRequests.get(projectId)
    if (!request) return

    if (autoLayoutRunningProjects.has(projectId)) {
      autoLayoutPendingReruns.set(projectId, request)
      return
    }
    autoLayoutLatestRequests.delete(projectId)
    autoLayoutRunningProjects.add(projectId)
    autoLayoutAutoApplying.value = true

    try {
      await runAutoLayoutAuto(projectId, request)
    } finally {
      autoLayoutRunningProjects.delete(projectId)
      autoLayoutAutoApplying.value = autoLayoutRunningProjects.size > 0
    }

    const rerunRequest = autoLayoutPendingReruns.get(projectId) || autoLayoutLatestRequests.get(projectId)
    if (!rerunRequest) return

    autoLayoutPendingReruns.delete(projectId)
    autoLayoutLatestRequests.set(projectId, rerunRequest)
    void flushAutoLayout(projectId)
  }

  function scheduleAutoLayout(projectId: string, options: ScheduleAutoLayoutOptions) {
    if (!isAutoLayoutReason(options.reason)) return

    const request: AutoLayoutRequest = {
      reason: options.reason,
      force: options.force ?? false,
    }
    autoLayoutLatestRequests.set(projectId, request)
    clearDebounceTimer(projectId)

    const timer = window.setTimeout(() => {
      autoLayoutDebounceTimers.delete(projectId)
      void flushAutoLayout(projectId)
    }, 800)
    autoLayoutDebounceTimers.set(projectId, timer)
  }

  async function runAutoLayoutAuto(projectId: string, request: AutoLayoutRequest) {
    try {
      await executeAutoLayout(projectId, request)
    } catch (error: any) {
      const suffix = request.force ? '' : ` (${request.reason})`
      deps.setNotice(error?.message || `Auto-layout tự động thất bại${suffix}.`, 'error')
    }
  }

  async function runAutoLayoutManual(options?: { preserveExistingPositions?: boolean }) {
    if (!deps.activeProject.value || autoLayoutManualApplying.value) return
    if (!deps.devices.value.length) {
      deps.setNotice('Chưa có thiết bị để chạy auto-layout.', 'error')
      return
    }

    autoLayoutManualApplying.value = true
    const projectId = deps.activeProject.value.id
    const preserveExistingPositions = options?.preserveExistingPositions ?? true
    try {
      const applied = await executeAutoLayout(projectId, {
        force: true,
        reason: 'manual',
        preserveExistingPositions,
      })
      if (applied) {
        deps.setNotice(
          preserveExistingPositions
            ? 'Đã chạy auto-layout và giữ vị trí đã lưu.'
            : 'Đã chạy auto-layout và ghi đè toàn bộ vị trí.',
          'success'
        )
      }
    } catch (error: any) {
      deps.setNotice(error?.message || 'Chạy lại auto-layout thất bại.', 'error')
    } finally {
      autoLayoutManualApplying.value = false
    }
  }

  onBeforeUnmount(() => {
    autoLayoutDebounceTimers.forEach(timer => window.clearTimeout(timer))
    autoLayoutDebounceTimers.clear()
    autoLayoutLatestRequests.clear()
    autoLayoutPendingReruns.clear()
    autoLayoutRunningProjects.clear()
  })

  return {
    autoLayoutAutoApplying,
    autoLayoutManualApplying,
    scheduleAutoLayout,
    runAutoLayoutManual,
  }
}
