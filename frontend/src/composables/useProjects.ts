import { computed, reactive, ref } from 'vue'
import type { ProjectRecord } from '../models/api'
import { listProjects, createProject, updateProject } from '../services/projects'

export function useProjects(setNotice: (msg: string, type: 'info' | 'success' | 'error') => void) {
  const projects = ref<ProjectRecord[]>([])
  const selectedProjectId = ref<string | null>(null)
  const projectForm = reactive({
    name: '',
    description: '',
    layoutMode: 'cisco' as 'cisco' | 'iso' | 'custom'
  })

  const activeProject = computed(() =>
    projects.value.find(p => p.id === selectedProjectId.value) || null
  )

  const layoutMode = computed(() => activeProject.value?.layout_mode || 'cisco')

  const layoutModeSelection = ref<'cisco' | 'iso' | 'custom'>('cisco')
  const layoutModeUpdating = ref(false)

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

  async function handleLayoutModeChange(
    value: 'cisco' | 'iso' | 'custom',
    onSuccess: (projectId: string) => void
  ) {
    if (!activeProject.value) return
    if (layoutModeUpdating.value) return
    if (activeProject.value.layout_mode === value) return
    layoutModeUpdating.value = true
    try {
      const updated = await updateProject(activeProject.value.id, { layout_mode: value })
      projects.value = projects.value.map(project => (project.id === updated.id ? updated : project))
      setNotice('Đã cập nhật layout mode.', 'success')
      onSuccess(updated.id)
    } catch (error: any) {
      setNotice(error?.message || 'Cập nhật layout mode thất bại.', 'error')
      layoutModeSelection.value = activeProject.value.layout_mode
    } finally {
      layoutModeUpdating.value = false
    }
  }

  return {
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
  }
}
