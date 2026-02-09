import type { DevicePortRecord } from '../models/api'
import { apiRequest } from './api'

export function listProjectPorts(projectId: string) {
  return apiRequest<DevicePortRecord[]>(`/api/v1/projects/${projectId}/ports`)
}

export function listDevicePorts(projectId: string, deviceId: string) {
  return apiRequest<DevicePortRecord[]>(`/api/v1/projects/${projectId}/devices/${deviceId}/ports`)
}

export function createDevicePort(
  projectId: string,
  deviceId: string,
  payload: {
    name: string
    side?: 'top' | 'bottom' | 'left' | 'right'
    offset_ratio?: number | null
  }
) {
  return apiRequest<DevicePortRecord>(`/api/v1/projects/${projectId}/devices/${deviceId}/ports`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateDevicePort(
  projectId: string,
  deviceId: string,
  portId: string,
  payload: {
    name?: string
    side?: 'top' | 'bottom' | 'left' | 'right'
    offset_ratio?: number | null
  }
) {
  return apiRequest<DevicePortRecord>(`/api/v1/projects/${projectId}/devices/${deviceId}/ports/${portId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteDevicePort(projectId: string, deviceId: string, portId: string) {
  return apiRequest<void>(`/api/v1/projects/${projectId}/devices/${deviceId}/ports/${portId}`, {
    method: 'DELETE',
  })
}
