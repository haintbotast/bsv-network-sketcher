import { computed, ref } from 'vue'
import { getAdminConfig } from '../services/adminConfig'
import type { AdminConfig } from '../services/adminConfig'
import { DEFAULT_LAYOUT_TUNING, DEFAULT_RENDER_TUNING } from './canvasConstants'

export function useLayoutConfig(
  setNotice: (msg: string, type: 'info' | 'success' | 'error') => void,
  currentUser: { value: any },
) {
  const adminConfig = ref<AdminConfig>({})

  const layoutTuning = computed(() => ({
    ...DEFAULT_LAYOUT_TUNING,
    ...(adminConfig.value.layout_tuning || {})
  }))

  const renderTuning = computed(() => ({
    ...DEFAULT_RENDER_TUNING,
    ...(adminConfig.value.render_tuning || {})
  }))

  async function loadAdminConfig() {
    if (!currentUser.value) return
    try {
      const config = await getAdminConfig()
      adminConfig.value = config
    } catch (error: any) {
      // Silently use defaults if config load fails
      adminConfig.value = {}
    }
  }

  return {
    layoutTuning,
    renderTuning,
    loadAdminConfig,
  }
}
