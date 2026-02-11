import { computed, onBeforeUnmount, ref } from 'vue'
import type { AreaModel, DeviceModel, LinkModel } from '../models/types'
import type {
  AreaRecord,
  DevicePortRecord,
  DeviceRecord,
  LinkRecord,
  PortAnchorOverrideRecord,
} from '../models/api'
import { listAreas, createArea, updateArea, deleteArea } from '../services/areas'
import { listDevices, createDevice, updateDevice, deleteDevice } from '../services/devices'
import {
  listProjectPorts,
  createDevicePort,
  updateDevicePort,
  deleteDevicePort,
} from '../services/devicePorts'
import { listLinks, createLink, updateLink, deleteLink } from '../services/links'
import { listPortAnchorOverrides, upsertPortAnchorOverrides, deletePortAnchorOverride } from '../services/portAnchors'
import {
  UNIT_PX,
  GRID_FALLBACK_X,
  GRID_FALLBACK_Y,
  snapUnitsToStandard,
  defaultAreaStyle,
  rgbToHex,
} from './canvasConstants'
import { excelRangeToRectUnits, rectUnitsToExcelRange } from '../utils/excelGrid'

export type AreaRow = AreaRecord & { __temp?: boolean }
export type DeviceRow = DeviceRecord & { __temp?: boolean }
export type DevicePortRow = DevicePortRecord & { __temp?: boolean }
export type LinkRow = LinkRecord & { __temp?: boolean }

function resolveGridRect(gridRange?: string | null) {
  if (!gridRange) return null
  try {
    return excelRangeToRectUnits(gridRange)
  } catch {
    return null
  }
}

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
  const devicePorts = ref<DevicePortRow[]>([])
  const links = ref<LinkRow[]>([])
  const portAnchorOverrides = ref<PortAnchorOverrideRecord[]>([])

  const devicePortMap = computed(() => {
    const map = new Map<string, DevicePortRow[]>()
    devicePorts.value.forEach(port => {
      const list = map.get(port.device_id) || []
      list.push(port)
      map.set(port.device_id, list)
    })
    map.forEach((list, deviceId) => {
      list.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }))
      map.set(deviceId, list)
    })
    return map
  })

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
      const rect = resolveGridRect(area.grid_range)
      const xUnits = rect?.x ?? area.position_x ?? (area.grid_col - 1) * GRID_FALLBACK_X
      const yUnits = rect?.y ?? area.position_y ?? (area.grid_row - 1) * GRID_FALLBACK_Y
      const widthUnits = rect?.width ?? area.width ?? 3
      const heightUnits = rect?.height ?? area.height ?? 1.5
      return {
        id: area.id,
        name: area.name,
        x: xUnits * UNIT_PX,
        y: yUnits * UNIT_PX,
        width: widthUnits * UNIT_PX,
        height: heightUnits * UNIT_PX,
        fill: rgbToHex(style.fill_color_rgb),
        stroke: rgbToHex(style.stroke_color_rgb),
        strokeWidth: style.stroke_width
      }
    })
  })

  const canvasDevices = computed<DeviceModel[]>(() => {
    return devices.value.map(device => {
      const rect = resolveGridRect(device.grid_range)
      const xUnits = rect?.x ?? device.position_x ?? 0
      const yUnits = rect?.y ?? device.position_y ?? 0
      const widthUnits = rect?.width ?? device.width ?? 1.2
      const heightUnits = rect?.height ?? device.height ?? 0.5
      return {
        id: device.id,
        areaId: device.area_id,
        name: device.name,
        x: xUnits * UNIT_PX,
        y: yUnits * UNIT_PX,
        width: widthUnits * UNIT_PX,
        height: heightUnits * UNIT_PX,
        type: device.device_type || 'Unknown',
        color: device.color_rgb ? rgbToHex(device.color_rgb) : null
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
          style: (link.line_style || 'solid') as 'solid' | 'dashed' | 'dotted',
          color: link.color_rgb ? rgbToHex(link.color_rgb) : null
        }
      })
      .filter(Boolean) as LinkModel[]
  })

  async function loadProjectData(projectId: string) {
    try {
      const [areasData, devicesData, portsData, linksData, overridesData] = await Promise.all([
        listAreas(projectId),
        listDevices(projectId),
        listProjectPorts(projectId),
        listLinks(projectId),
        listPortAnchorOverrides(projectId)
      ])
      areas.value = areasData
      devices.value = devicesData
      devicePorts.value = portsData
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
        grid_range: row.grid_range || undefined,
        position_x: row.position_x,
        position_y: row.position_y,
        width: row.width,
        height: row.height,
        style: row.style || defaultAreaStyle
      })
      const index = areas.value.findIndex(area => area.id === row.id)
      if (index >= 0) areas.value[index] = created
      scheduleAutoLayout(projectId, { force: true, reason: 'area-crud' })
      setNotice(`Đã tạo area '${created.name}'.`, 'success')
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
          grid_range: payload.row.grid_range || undefined,
          position_x: payload.row.position_x,
          position_y: payload.row.position_y,
          width: payload.row.width,
          height: payload.row.height,
          style: payload.row.style || undefined
        })
        const index = areas.value.findIndex(area => area.id === payload.row.id)
        if (index >= 0) areas.value[index] = updated
        scheduleAutoLayout(projectId, { force: true, reason: 'area-crud' })
        setNotice(`Đã cập nhật area '${updated.name}'.`, 'success')
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
      setNotice(`Đã xóa area '${row.name}'.`, 'success')
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
        grid_range: row.grid_range || undefined,
        position_x: row.position_x,
        position_y: row.position_y,
        width: row.width,
        height: row.height,
        color_rgb: row.color_rgb || undefined
      })
      const index = devices.value.findIndex(device => device.id === row.id)
      if (index >= 0) devices.value[index] = created
      scheduleAutoLayout(projectId, { force: true, reason: 'device-crud' })
      setNotice(`Đã tạo thiết bị '${created.name}'.`, 'success')
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
          grid_range: payload.row.grid_range || undefined,
          position_x: payload.row.position_x,
          position_y: payload.row.position_y,
          width: payload.row.width,
          height: payload.row.height,
          color_rgb: payload.row.color_rgb || undefined
        })
        const index = devices.value.findIndex(device => device.id === payload.row.id)
        if (index >= 0) devices.value[index] = updated
        scheduleAutoLayout(projectId, { force: true, reason: 'device-crud' })
        setNotice(`Đã cập nhật thiết bị '${updated.name}'.`, 'success')
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
      devicePorts.value = devicePorts.value.filter(port => port.device_id !== row.id)
      portAnchorOverrides.value = portAnchorOverrides.value.filter(override => override.device_id !== row.id)
      scheduleAutoLayout(projectId, { force: true, reason: 'device-crud' })
      setNotice(`Đã xóa thiết bị '${row.name}'.`, 'success')
    } catch (error: any) {
      setNotice(error?.message || 'Xóa device thất bại.', 'error')
    }
  }

  async function createDevicePortRow(
    projectId: string,
    deviceId: string,
    payload: {
      name: string
      side?: 'top' | 'bottom' | 'left' | 'right'
      offset_ratio?: number | null
    }
  ) {
    const created = await createDevicePort(projectId, deviceId, payload)
    devicePorts.value.push(created)
    return created
  }

  async function updateDevicePortRow(
    projectId: string,
    deviceId: string,
    portId: string,
    payload: {
      name?: string
      side?: 'top' | 'bottom' | 'left' | 'right'
      offset_ratio?: number | null
    }
  ) {
    const updated = await updateDevicePort(projectId, deviceId, portId, payload)
    const index = devicePorts.value.findIndex(port => port.id === portId)
    if (index >= 0) devicePorts.value[index] = updated
    return updated
  }

  async function deleteDevicePortRow(projectId: string, deviceId: string, portId: string) {
    const port = devicePorts.value.find(item => item.id === portId)
    await deleteDevicePort(projectId, deviceId, portId)
    devicePorts.value = devicePorts.value.filter(item => item.id !== portId)
    if (port) {
      portAnchorOverrides.value = portAnchorOverrides.value.filter(
        item => !(item.device_id === deviceId && item.port_name === port.name)
      )
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
      setNotice('Đã tạo link.', 'success')
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
        setNotice('Đã cập nhật link.', 'success')
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
      setNotice('Đã xóa link.', 'success')
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

  async function saveAreaPosition(areaId: string, positionX: number, positionY: number) {
    if (!selectedProjectId.value) return
    const projectId = selectedProjectId.value
    const index = areas.value.findIndex(area => area.id === areaId)
    if (index < 0) return
    const normalizedX = snapUnitsToStandard(positionX)
    const normalizedY = snapUnitsToStandard(positionY)

    const previous = areas.value[index]
    const optimisticGridRange = rectUnitsToExcelRange(normalizedX, normalizedY, previous.width || 3, previous.height || 1.5)
    const optimistic: AreaRow = {
      ...previous,
      position_x: normalizedX,
      position_y: normalizedY,
      grid_range: optimisticGridRange,
    }
    areas.value[index] = optimistic

    try {
      const updated = await updateArea(projectId, areaId, {
        position_x: normalizedX,
        position_y: normalizedY,
        grid_range: optimisticGridRange,
      })
      const nextIndex = areas.value.findIndex(area => area.id === areaId)
      if (nextIndex >= 0) {
        areas.value[nextIndex] = {
          ...(areas.value[nextIndex].__temp ? { __temp: true } : {}),
          ...updated,
        }
      }
    } catch (error) {
      const nextIndex = areas.value.findIndex(area => area.id === areaId)
      if (nextIndex >= 0) areas.value[nextIndex] = previous
      throw error
    }
  }

  async function saveDevicePosition(deviceId: string, positionX: number, positionY: number) {
    if (!selectedProjectId.value) return
    const projectId = selectedProjectId.value
    const index = devices.value.findIndex(device => device.id === deviceId)
    if (index < 0) return
    const normalizedX = snapUnitsToStandard(positionX)
    const normalizedY = snapUnitsToStandard(positionY)

    const previous = devices.value[index]
    const optimisticGridRange = rectUnitsToExcelRange(normalizedX, normalizedY, previous.width || 1.2, previous.height || 0.5)
    const optimistic: DeviceRow = {
      ...previous,
      position_x: normalizedX,
      position_y: normalizedY,
      grid_range: optimisticGridRange,
    }
    devices.value[index] = optimistic

    try {
      const updated = await updateDevice(projectId, deviceId, {
        position_x: normalizedX,
        position_y: normalizedY,
        grid_range: optimisticGridRange,
      })
      const nextIndex = devices.value.findIndex(device => device.id === deviceId)
      if (nextIndex >= 0) {
        devices.value[nextIndex] = {
          ...(devices.value[nextIndex].__temp ? { __temp: true } : {}),
          ...updated,
        }
      }
    } catch (error) {
      const nextIndex = devices.value.findIndex(device => device.id === deviceId)
      if (nextIndex >= 0) devices.value[nextIndex] = previous
      throw error
    }
  }

  return {
    areas,
    devices,
    devicePorts,
    devicePortMap,
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
    createDevicePortRow,
    updateDevicePortRow,
    deleteDevicePortRow,
    handleLinkAdd,
    handleLinkChange,
    handleLinkRemove,
    upsertAnchorOverride,
    removeAnchorOverride,
    assignDeviceArea,
    saveAreaPosition,
    saveDevicePosition,
  }
}
