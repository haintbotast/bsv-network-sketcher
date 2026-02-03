import { apiRequest } from './api'
import type { PortAnchorOverrideRecord } from '../models/api'

export type PortAnchorOverrideUpsert = {
  device_id: string
  port_name: string
  side: 'left' | 'right' | 'top' | 'bottom'
  offset_ratio: number | null
}

export async function listPortAnchorOverrides(projectId: string) {
  return apiRequest<PortAnchorOverrideRecord[]>(`/api/v1/projects/${projectId}/port-anchors`)
}

export async function upsertPortAnchorOverrides(projectId: string, overrides: PortAnchorOverrideUpsert[]) {
  return apiRequest<PortAnchorOverrideRecord[]>(`/api/v1/projects/${projectId}/port-anchors`, {
    method: 'PUT',
    body: JSON.stringify({ overrides })
  })
}

export async function deletePortAnchorOverride(projectId: string, deviceId: string, portName: string) {
  const params = new URLSearchParams({ device_id: deviceId, port_name: portName })
  return apiRequest<void>(`/api/v1/projects/${projectId}/port-anchors?${params.toString()}`, {
    method: 'DELETE'
  })
}
