import { computed, ref, onBeforeUnmount } from 'vue'
import type { AreaModel, DeviceModel, LinkModel } from '../models/types'
import type { AreaRecord, DeviceRecord, LinkRecord, PortAnchorOverrideRecord } from '../models/api'
import { listAreas, createArea, updateArea, deleteArea } from '../services/areas'
import { listDevices, createDevice, updateDevice, deleteDevice } from '../services/devices'
import { listLinks, createLink, updateLink, deleteLink } from '../services/links'
import { listPortAnchorOverrides, upsertPortAnchorOverrides, deletePortAnchorOverride } from '../services/portAnchors'
import {
  UNIT_PX,
  GRID_FALLBACK_X,
  GRID_FALLBACK_Y,
  defaultAreaStyle,
  rgbToHex,
} from './canvasConstants'

export type AreaRow = AreaRecord & { __temp?: boolean }
export type DeviceRow = DeviceRecord & { __temp?: boolean }
export type LinkRow = LinkRecord & { __temp?: boolean }

export function useCanvasData(
  selectedProjectId: { value: string | null },
  setNotice: (msg: string, type: 'info' | 'success' | 'error') => void,
  scheduleAutoLayout: (
    projectId: string,
    options: { force?: boolean; reason: 'area-crud' | 'device-crud' | 'link-crud' }
  ) => void,
) {
  const areas = ref<AreaRow[]>([])
  const devices = ref<DeviceRow[]>([])
  const links = ref<LinkRow[]>([])
  const portAnchorOverrides = ref<PortAnchorOverrideRecord[]>([])

  const portAnchorOverrideMap = computed(() => {
    const map = new Map<string, Map<string, { side: 'left' | 'right' | 'top' | 'bottom'; offsetRatio: number | null }>>()
    portAnchorOverrides.value.forEach(override => {
      const deviceMap = map.get(override.device_id) || new Map()
      deviceMap.set(override.port_name, {
        side: override.side,
        offsetRatio: override.offset_ratio
      })
      map.set(override.device_id, deviceMap)
    })
    return map
  })

  const canvasAreas = computed<AreaModel[]>(() => {
    return areas.value.map(area => {
      const style = area.style || defaultAreaStyle
      const xUnits = area.position_x ?? (area.grid_col - 1) * GRID_FALLBACK_X
      const yUnits = area.position_y ?? (area.grid_row - 1) * GRID_FALLBACK_Y
      const widthUnits = area.width || 3
      const heightUnits = area.height || 1.5
      return {
        id: area.id,
        name: area.name,
        x: xUnits * UNIT_PX,
        y: yUnits * UNIT_PX,
        width: widthUnits * UNIT_PX,
        height: heightUnits * UNIT_PX,
        fill: rgbToHex(style.fill_color_rgb),
        stroke: rgbToHex(style.stroke_color_rgb)
      }
    })
  })

  const canvasDevices = computed<DeviceModel[]>(() => {
    return devices.value.map(device => {
      const xUnits = device.position_x ?? 0
      const yUnits = device.position_y ?? 0
      return {
        id: device.id,
        areaId: device.area_id,
        name: device.name,
        x: xUnits * UNIT_PX,
        y: yUnits * UNIT_PX,
        width: (device.width || 1.2) * UNIT_PX,
        height: (device.height || 0.5) * UNIT_PX,
        type: device.device_type || 'Unknown'
      }
    })
  })

  const canvasLinks = computed<LinkModel[]>(() => {
    const byName = new Map(devices.value.map(device => [device.name, device]))
    const byId = new Map(devices.value.map(device => [device.id, device]))
    return links.value
      .map(link => {
        const from = link.from_device_name ? byName.get(link.from_device_name) : byId.get(link.from_device_id)
        const to = link.to_device_name ? byName.get(link.to_device_name) : byId.get(link.to_device_id)
        if (!from || !to) return null
        return {
          id: link.id,
          fromDeviceId: from.id,
          toDeviceId: to.id,
          fromPort: link.from_port,
          toPort: link.to_port,
          purpose: link.purpose || undefined,
          style: (link.line_style || 'solid') as 'solid' | 'dashed' | 'dotted'
        }
      })
      .filter(Boolean) as LinkModel[]
  })

  async function loadProjectData(projectId: string) {
    try {
      const [areasData, devicesData, linksData, overridesData] = await Promise.all([
        listAreas(projectId),
        listDevices(projectId),
        listLinks(projectId),
        listPortAnchorOverrides(projectId)
      ])
      areas.value = areasData
      devices.value = devicesData
      links.value = linksData
      portAnchorOverrides.value = overridesData
    } catch (error: any) {
      setNotice(error?.message || 'Không tải được dữ liệu project.', 'error')
    }
  }

  // Debounce timers for updates
  const areaUpdateTimers = new Map<string, number>()
  const deviceUpdateTimers = new Map<string, number>()
  const linkUpdateTimers = new Map<string, number>()

  function scheduleUpdate(map: Map<string, number>, key: string, handler: () => void) {
    const existing = map.get(key)
    if (existing) window.clearTimeout(existing)
    const timer = window.setTimeout(() => {
      map.delete(key)
      handler()
    }, 600)
    map.set(key, timer)
  }

  // Cleanup all pending timers when component unmounts
  onBeforeUnmount(() => {
    areaUpdateTimers.forEach(t => window.clearTimeout(t))
    deviceUpdateTimers.forEach(t => window.clearTimeout(t))
    linkUpdateTimers.forEach(t => window.clearTimeout(t))
  })

  async function handleAreaAdd(row: AreaRow) {
    if (!selectedProjectId.value) {
      setNotice('Vui lòng chọn project trước.', 'error')
      return
    }
    const projectId = selectedProjectId.value
    try {
      const created = await createArea(projectId, {
        name: row.name,
        grid_row: row.grid_row,
        grid_col: row.grid_col,
        position_x: row.position_x,
        position_y: row.position_y,
        width: row.width,
        height: row.height,
        style: row.style || defaultAreaStyle
      })
      const index = areas.value.findIndex(area => area.id === row.id)
      if (index >= 0) areas.value[index] = created
      scheduleAutoLayout(projectId, { force: true, reason: 'area-crud' })
    } catch (error: any) {
      if (row.__temp) {
        areas.value = areas.value.filter(area => area.id !== row.id)
      }
      setNotice(error?.message || 'Tạo area thất bại.', 'error')
    }
  }

  function handleAreaChange(payload: { row: AreaRow }) {
    if (!selectedProjectId.value) return
    const projectId = selectedProjectId.value
    if (payload.row.__temp) return
    scheduleUpdate(areaUpdateTimers, payload.row.id, async () => {
      try {
        const updated = await updateArea(projectId as string, payload.row.id, {
          name: payload.row.name,
          grid_row: payload.row.grid_row,
          grid_col: payload.row.grid_col,
          position_x: payload.row.position_x,
          position_y: payload.row.position_y,
          width: payload.row.width,
          height: payload.row.height,
          style: payload.row.style || undefined
        })
        const index = areas.value.findIndex(area => area.id === payload.row.id)
        if (index >= 0) areas.value[index] = updated
        scheduleAutoLayout(projectId, { force: true, reason: 'area-crud' })
      } catch (error: any) {
        setNotice(error?.message || 'Cập nhật area thất bại.', 'error')
      }
    })
  }

  async function handleAreaRemove(row: AreaRow) {
    if (!selectedProjectId.value) return
    const projectId = selectedProjectId.value
    if (row.__temp) return
    try {
      await deleteArea(projectId, row.id)
      scheduleAutoLayout(projectId, { force: true, reason: 'area-crud' })
    } catch (error: any) {
      setNotice(error?.message || 'Xóa area thất bại.', 'error')
    }
  }

  async function handleDeviceAdd(row: DeviceRow) {
    if (!selectedProjectId.value) {
      setNotice('Vui lòng chọn project trước.', 'error')
      return
    }
    const projectId = selectedProjectId.value
    if (!row.area_name) {
      setNotice('Cần chọn area cho device.', 'error')
      return
    }
    try {
      const created = await createDevice(projectId, {
        name: row.name,
        area_name: row.area_name,
        device_type: row.device_type,
        position_x: row.position_x,
        position_y: row.position_y,
        width: row.width,
        height: row.height,
        color_rgb: row.color_rgb || undefined
      })
      const index = devices.value.findIndex(device => device.id === row.id)
      if (index >= 0) devices.value[index] = created
      scheduleAutoLayout(projectId, { force: true, reason: 'device-crud' })
    } catch (error: any) {
      if (row.__temp) {
        devices.value = devices.value.filter(device => device.id !== row.id)
      }
      setNotice(error?.message || 'Tạo device thất bại.', 'error')
    }
  }

  function handleDeviceChange(payload: { row: DeviceRow }) {
    if (!selectedProjectId.value) return
    const projectId = selectedProjectId.value
    if (payload.row.__temp) return
    scheduleUpdate(deviceUpdateTimers, payload.row.id, async () => {
      try {
        const updated = await updateDevice(projectId as string, payload.row.id, {
          name: payload.row.name,
          area_name: payload.row.area_name || undefined,
          device_type: payload.row.device_type,
          position_x: payload.row.position_x,
          position_y: payload.row.position_y,
          width: payload.row.width,
          height: payload.row.height,
          color_rgb: payload.row.color_rgb || undefined
        })
        const index = devices.value.findIndex(device => device.id === payload.row.id)
        if (index >= 0) devices.value[index] = updated
        scheduleAutoLayout(projectId, { force: true, reason: 'device-crud' })
      } catch (error: any) {
        setNotice(error?.message || 'Cập nhật device thất bại.', 'error')
      }
    })
  }

  async function handleDeviceRemove(row: DeviceRow) {
    if (!selectedProjectId.value) return
    const projectId = selectedProjectId.value
    if (row.__temp) return
    try {
      await deleteDevice(projectId, row.id)
      scheduleAutoLayout(projectId, { force: true, reason: 'device-crud' })
    } catch (error: any) {
      setNotice(error?.message || 'Xóa device thất bại.', 'error')
    }
  }

  async function handleLinkAdd(row: LinkRow) {
    if (!selectedProjectId.value) {
      setNotice('Vui lòng chọn project trước.', 'error')
      return
    }
    const projectId = selectedProjectId.value
    if (!row.from_device_name || !row.to_device_name) {
      setNotice('Cần chọn thiết bị đầu/cuối cho link.', 'error')
      return
    }
    try {
      const created = await createLink(projectId, {
        from_device: row.from_device_name,
        from_port: row.from_port,
        to_device: row.to_device_name,
        to_port: row.to_port,
        purpose: row.purpose || undefined,
        line_style: row.line_style || 'solid'
      })
      const index = links.value.findIndex(link => link.id === row.id)
      if (index >= 0) links.value[index] = created
      scheduleAutoLayout(projectId, { force: true, reason: 'link-crud' })
    } catch (error: any) {
      if (row.__temp) {
        links.value = links.value.filter(link => link.id !== row.id)
      }
      setNotice(error?.message || 'Tạo link thất bại.', 'error')
    }
  }

  function handleLinkChange(payload: { row: LinkRow }) {
    if (!selectedProjectId.value) return
    const projectId = selectedProjectId.value
    if (payload.row.__temp) return
    scheduleUpdate(linkUpdateTimers, payload.row.id, async () => {
      try {
        const updated = await updateLink(projectId as string, payload.row.id, {
          from_device: payload.row.from_device_name || undefined,
          from_port: payload.row.from_port,
          to_device: payload.row.to_device_name || undefined,
          to_port: payload.row.to_port,
          purpose: payload.row.purpose || undefined,
          line_style: payload.row.line_style || undefined
        })
        const index = links.value.findIndex(link => link.id === payload.row.id)
        if (index >= 0) links.value[index] = updated
        scheduleAutoLayout(projectId, { force: true, reason: 'link-crud' })
      } catch (error: any) {
        setNotice(error?.message || 'Cập nhật link thất bại.', 'error')
      }
    })
  }

  async function handleLinkRemove(row: LinkRow) {
    if (!selectedProjectId.value) return
    const projectId = selectedProjectId.value
    if (row.__temp) return
    try {
      await deleteLink(projectId, row.id)
      scheduleAutoLayout(projectId, { force: true, reason: 'link-crud' })
    } catch (error: any) {
      setNotice(error?.message || 'Xóa link thất bại.', 'error')
    }
  }

  async function upsertAnchorOverride(
    projectId: string,
    payload: { device_id: string; port_name: string; side: 'left' | 'right' | 'top' | 'bottom'; offset_ratio: number | null }
  ) {
    const [saved] = await upsertPortAnchorOverrides(projectId, [payload])
    if (!saved) return
    const index = portAnchorOverrides.value.findIndex(
      item => item.device_id === saved.device_id && item.port_name === saved.port_name
    )
    if (index >= 0) {
      portAnchorOverrides.value[index] = saved
    } else {
      portAnchorOverrides.value.push(saved)
    }
  }

  async function removeAnchorOverride(projectId: string, deviceId: string, portName: string) {
    await deletePortAnchorOverride(projectId, deviceId, portName)
    portAnchorOverrides.value = portAnchorOverrides.value.filter(
      item => !(item.device_id === deviceId && item.port_name === portName)
    )
  }

  function assignDeviceArea(device: DeviceRow, areaId: string) {
    const area = areas.value.find(item => item.id === areaId)
    if (!area) return
    device.area_id = area.id
    device.area_name = area.name
    handleDeviceChange({ row: device })
  }

  return {
    areas,
    devices,
    links,
    portAnchorOverrides,
    portAnchorOverrideMap,
    canvasAreas,
    canvasDevices,
    canvasLinks,
    loadProjectData,
    handleAreaAdd,
    handleAreaChange,
    handleAreaRemove,
    handleDeviceAdd,
    handleDeviceChange,
    handleDeviceRemove,
    handleLinkAdd,
    handleLinkChange,
    handleLinkRemove,
    upsertAnchorOverride,
    removeAnchorOverride,
    assignDeviceArea,
  }
}
