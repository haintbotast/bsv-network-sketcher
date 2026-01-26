import type { LinkRecord } from '../models/api'
import { apiRequest } from './api'

export function listLinks(projectId: string) {
  return apiRequest<LinkRecord[]>(`/api/v1/projects/${projectId}/links`)
}

export function createLink(
  projectId: string,
  payload: {
    from_device: string
    from_port: string
    to_device: string
    to_port: string
    purpose?: string
    line_style?: 'solid' | 'dashed' | 'dotted'
  }
) {
  return apiRequest<LinkRecord>(`/api/v1/projects/${projectId}/links`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateLink(
  projectId: string,
  linkId: string,
  payload: {
    from_device?: string
    from_port?: string
    to_device?: string
    to_port?: string
    purpose?: string
    line_style?: 'solid' | 'dashed' | 'dotted'
  }
) {
  return apiRequest<LinkRecord>(`/api/v1/projects/${projectId}/links/${linkId}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function deleteLink(projectId: string, linkId: string) {
  return apiRequest<void>(`/api/v1/projects/${projectId}/links/${linkId}`, {
    method: 'DELETE'
  })
}
