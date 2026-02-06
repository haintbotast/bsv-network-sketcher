import { computed, reactive, ref } from 'vue'
import type { ProjectRecord } from '../models/api'
import { listProjects, createProject } from '../services/projects'

export function useProjects(setNotice: (msg: string, type: 'info' | 'success' | 'error') => void) {
  const projects = ref<ProjectRecord[]>([])
  const selectedProjectId = ref<string | null>(null)
  const projectForm = reactive({
    name: '',
    description: ''
  })

  const activeProject = computed(() =>
    projects.value.find(p => p.id === selectedProjectId.value) || null
  )

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
        description: projectForm.description || undefined
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

  return {
    projects,
    selectedProjectId,
    projectForm,
    activeProject,
    loadProjects,
    handleCreateProject
  }
}
