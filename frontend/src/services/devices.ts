import type { DeviceRecord } from '../models/api'
import { apiRequest } from './api'

export function listDevices(projectId: string) {
  return apiRequest<DeviceRecord[]>(`/api/v1/projects/${projectId}/devices`)
}

export function createDevice(
  projectId: string,
  payload: {
    name: string
    area_name: string
    device_type: string
    position_x?: number | null
    position_y?: number | null
    width: number
    height: number
    color_rgb?: [number, number, number] | null
  }
) {
  return apiRequest<DeviceRecord>(`/api/v1/projects/${projectId}/devices`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateDevice(
  projectId: string,
  deviceId: string,
  payload: {
    name?: string
    area_name?: string
    device_type?: string
    position_x?: number | null
    position_y?: number | null
    width?: number
    height?: number
    color_rgb?: [number, number, number] | null
  }
) {
  return apiRequest<DeviceRecord>(`/api/v1/projects/${projectId}/devices/${deviceId}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function deleteDevice(projectId: string, deviceId: string) {
  return apiRequest<void>(`/api/v1/projects/${projectId}/devices/${deviceId}`, {
    method: 'DELETE'
  })
}
