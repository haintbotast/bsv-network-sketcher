import { computed, reactive, ref } from 'vue'
import type { Viewport } from '../models/types'

export function useViewport() {
  const viewport = reactive({
    scale: 1,
    offsetX: 0,
    offsetY: 0
  })

  const showRightPanel = ref(true)
  const rightPanelWidth = ref(360)
  const rightPanelTab = ref<'properties' | 'layout'>('properties')

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

  function zoomIn() {
    viewport.scale = Math.min(viewport.scale + 0.1, 3)
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

  return {
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
  }
}
