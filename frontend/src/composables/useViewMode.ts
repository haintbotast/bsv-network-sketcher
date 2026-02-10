import { computed, ref, type Ref } from 'vue'
import { getToken } from '../services/api'
import type { L2AssignmentRecord, L3AddressRecord } from '../models/types'

export type { L2AssignmentRecord, L3AddressRecord }

export type ViewMode = 'L1' | 'L2' | 'L3'

export function useViewMode(
  selectedProjectId: Ref<string | null>,
  selectedAreaName: Ref<string | null>,
) {
  const viewMode = ref<ViewMode>('L1')
  const l2Assignments = ref<L2AssignmentRecord[]>([])
  const l3Addresses = ref<L3AddressRecord[]>([])
  const l2Loaded = ref(false)
  const l3Loaded = ref(false)

  const viewModeLabel = computed(() => {
    const areaName = selectedAreaName.value
    if (viewMode.value === 'L1') return 'All Areas'
    if (viewMode.value === 'L2') return areaName || 'Focus on Area'
    if (viewMode.value === 'L3') {
      return areaName ? `All Areas · Focus: ${areaName}` : 'All Areas'
    }
    return ''
  })

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

  async function setViewMode(mode: ViewMode) {
    viewMode.value = mode
    if (!selectedProjectId.value) return
    if (mode === 'L2' && !l2Loaded.value) {
      await fetchL2Data()
    }
    if (mode === 'L3' && !l3Loaded.value) {
      await fetchL3Data()
    }
  }

  function resetViewModeData() {
    l2Loaded.value = false
    l3Loaded.value = false
    l2Assignments.value = []
    l3Addresses.value = []
    viewMode.value = 'L1'
  }

  return {
    viewMode,
    l2Assignments,
    l3Addresses,
    l2Loaded,
    l3Loaded,
    viewModeLabel,
    setViewMode,
    resetViewModeData,
  }
}
