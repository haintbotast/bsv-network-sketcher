import type { ProjectRecord } from '../models/api'
import { apiRequest } from './api'

export function listProjects() {
  return apiRequest<ProjectRecord[]>('/api/v1/projects')
}

export function createProject(payload: { name: string; description?: string; layout_mode?: 'standard' }) {
  return apiRequest<ProjectRecord>('/api/v1/projects', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateProject(projectId: string, payload: { name?: string; description?: string; layout_mode?: 'standard' }) {
  return apiRequest<ProjectRecord>(`/api/v1/projects/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}
