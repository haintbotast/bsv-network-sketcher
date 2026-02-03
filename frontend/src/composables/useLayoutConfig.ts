import { computed, reactive, ref } from 'vue'
import { getAdminConfig, updateAdminConfig } from '../services/adminConfig'
import type { AdminConfig } from '../services/adminConfig'
import { DEFAULT_LAYOUT_TUNING, DEFAULT_RENDER_TUNING } from './canvasConstants'

export function useLayoutConfig(
  setNotice: (msg: string, type: 'info' | 'success' | 'error') => void,
  currentUser: { value: any },
  onSaved?: () => void,
) {
  const adminConfig = ref<AdminConfig>({})
  const layoutTuningForm = reactive({ ...DEFAULT_LAYOUT_TUNING })
  const renderTuningForm = reactive({ ...DEFAULT_RENDER_TUNING })
  const adminConfigSaving = ref(false)

  const layoutTuning = computed(() => ({
    ...DEFAULT_LAYOUT_TUNING,
    ...(adminConfig.value.layout_tuning || {})
  }))
  const renderTuning = computed(() => ({
    ...DEFAULT_RENDER_TUNING,
    ...(adminConfig.value.render_tuning || {})
  }))

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
      onSaved?.()
      setNotice('Đã lưu cấu hình layout.', 'success')
    } catch (error: any) {
      setNotice(error?.message || 'Lưu cấu hình layout thất bại.', 'error')
    } finally {
      adminConfigSaving.value = false
    }
  }

  function resetConfig() {
    adminConfig.value = {}
    syncTuningForms({})
  }

  return {
    adminConfig,
    layoutTuningForm,
    renderTuningForm,
    adminConfigSaving,
    layoutTuning,
    renderTuning,
    syncTuningForms,
    loadAdminConfig,
    saveAdminConfig,
    resetConfig,
  }
}
