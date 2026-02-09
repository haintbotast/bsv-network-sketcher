import type { AreaRecord, AreaStyle } from '../models/api'
import { apiRequest } from './api'

export function listAreas(projectId: string) {
  return apiRequest<AreaRecord[]>(`/api/v1/projects/${projectId}/areas`)
}

export function createArea(
  projectId: string,
  payload: {
    name: string
    grid_row: number
    grid_col: number
    grid_range?: string | null
    position_x?: number | null
    position_y?: number | null
    width: number
    height: number
    style?: AreaStyle | null
  }
) {
  return apiRequest<AreaRecord>(`/api/v1/projects/${projectId}/areas`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateArea(
  projectId: string,
  areaId: string,
  payload: {
    name?: string
    grid_row?: number
    grid_col?: number
    grid_range?: string | null
    position_x?: number | null
    position_y?: number | null
    width?: number
    height?: number
    style?: AreaStyle | null
  }
) {
  return apiRequest<AreaRecord>(`/api/v1/projects/${projectId}/areas/${areaId}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function deleteArea(projectId: string, areaId: string) {
  return apiRequest<void>(`/api/v1/projects/${projectId}/areas/${areaId}`, {
    method: 'DELETE'
  })
}
