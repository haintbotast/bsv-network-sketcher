import type { DeviceModel } from '../../models/types'
import { extractPortIndex } from './linkRoutingUtils'

const normalize = (value: string) => value.trim().toLowerCase()

function resolveDeviceTier(type: string, name: string) {
  const normalizedType = normalize(type)
  const normalizedName = normalize(name)

  if (['cloud', 'cloud-network', 'cloud-security', 'cloud-service'].includes(normalizedType)) return 0
  if (normalizedType === 'router' || /(router|rtr|edge|wan|internet|isp)/.test(normalizedName)) return 0
  if (normalizedType === 'firewall' || /(firewall|fw|security|ids|ips|vpn|waf)/.test(normalizedName)) return 1
  if (/(core)/.test(normalizedName)) return 2
  if (/(distribution|dist|ds\d*)/.test(normalizedName)) return 3
  if (/(access|acc|asw)/.test(normalizedName)) return 4
  if (normalizedType === 'switch' && /(server|srv|storage|nas|san|sv\d*)/.test(normalizedName)) return 5
  if (normalizedType === 'server' || normalizedType === 'storage' || /(server|srv|app|web|db|nas|san|storage|backup)/.test(normalizedName)) return 6
  if (['pc', 'printer', 'camera', 'phone', 'ipphone', 'endpoint', 'ap'].includes(normalizedType)) return 7
  if (/(pc|printer|prn|cam|cctv|phone|ipphone|endpoint|client|terminal|ap)/.test(normalizedName)) return 7
  return 5
}

export function buildDeviceTierMap(devices?: DeviceModel[]) {
  const map = new Map<string, { type: string; name: string; tier: number }>()
  ;(devices || []).forEach(device => {
    const type = device.type || ''
    const name = device.name || ''
    map.set(device.id, { type, name, tier: resolveDeviceTier(type, name) })
  })
  return map
}

export function isUplinkPortName(portName?: string) {
  const index = extractPortIndex(portName)
  return index === 1
}

export function resolveAutoPortSide(
  deviceId: string,
  neighborId: string,
  portName: string | undefined,
  deviceTierMap: Map<string, { type: string; name: string; tier: number }>
): 'top' | 'bottom' {
  const info = deviceTierMap.get(deviceId)
  const neighbor = deviceTierMap.get(neighborId)

  if (info && neighbor && info.tier !== neighbor.tier) {
    return info.tier > neighbor.tier ? 'top' : 'bottom'
  }
  if (isUplinkPortName(portName)) return 'top'
  return 'bottom'
}
