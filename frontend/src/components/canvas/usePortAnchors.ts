import { computed, type ComputedRef } from 'vue'
import type { DeviceModel, LinkModel, L2AssignmentRecord, ViewMode } from '../../models/types'
import type { Rect, AnchorOverrideMap, RenderTuning, PortAnchorOverrideMap } from './linkRoutingTypes'
import { clamp, comparePorts, computePortAnchorFallback, computeSide, extractPortIndex } from './linkRoutingUtils'
import { buildDeviceTierMap, isUplinkPortName, resolveAutoPortSide } from './portSidePolicy'

const DEVICE_PORT_CELL_MIN_WIDTH = 30
const DEVICE_PORT_CELL_GAP = 2
const DEVICE_PORT_BAND_PADDING_X = 6
const DEVICE_PORT_FONT_SIZE = 10

function estimatePortCellWidth(portName: string) {
  const text = portName.trim()
  const charWidth = DEVICE_PORT_FONT_SIZE * 0.62
  return Math.max(DEVICE_PORT_CELL_MIN_WIDTH, Math.ceil(text.length * charWidth + 10))
}

export function usePortAnchors(deps: {
  props: {
    links: LinkModel[]
    devices?: DeviceModel[]
    l2Assignments?: L2AssignmentRecord[]
    viewMode?: ViewMode
  }
  renderTuning: ComputedRef<RenderTuning>
  deviceViewMap: ComputedRef<Map<string, Rect>>
  portAnchorOverrides?: ComputedRef<PortAnchorOverrideMap>
}) {
  const { props, renderTuning, deviceViewMap, portAnchorOverrides } = deps

  const deviceInfoMap = computed(() => {
    return buildDeviceTierMap((props as { devices?: DeviceModel[] }).devices)
  })

  const resolveAutoSide = (
    deviceId: string,
    neighborId: string,
    port: string | undefined,
  ): 'top' | 'bottom' => {
    return resolveAutoPortSide(deviceId, neighborId, port, deviceInfoMap.value)
  }

  const devicePortList = computed(() => {
    const map = new Map<string, string[]>()
    const addPort = (deviceId?: string | null, port?: string | null) => {
      if (!deviceId || !port) return
      const list = map.get(deviceId) || []
      if (!list.includes(port)) list.push(port)
      map.set(deviceId, list)
    }

    const isL1 = (props.viewMode || 'L1') === 'L1'
    props.links.forEach(link => {
      addPort(link.fromDeviceId, link.fromPort)
      addPort(link.toDeviceId, link.toPort)
    })

    if (!isL1) {
      props.l2Assignments?.forEach(assign => {
        addPort(assign.device_id, assign.interface_name)
      })
    }

    if (portAnchorOverrides?.value) {
      portAnchorOverrides.value.forEach((ports, deviceId) => {
        ports.forEach((_override, port) => {
          addPort(deviceId, port)
        })
      })
    }

    map.forEach((ports, deviceId) => {
      ports.sort(comparePorts)
      map.set(deviceId, ports)
    })
    return map
  })

  const devicePortOrder = computed(() => {
    const map = new Map<string, Map<string, number>>()
    devicePortList.value.forEach((ports, deviceId) => {
      const order = new Map<string, number>()
      ports.forEach((port, index) => {
        order.set(port, index)
      })
      map.set(deviceId, order)
    })
    return map
  })

  const devicePortNeighbors = computed(() => {
    const map = new Map<string, Map<string, { xSum: number; ySum: number; count: number }>>()

    const add = (deviceId: string, port: string, neighbor: { x: number; y: number }) => {
      const deviceMap = map.get(deviceId) || new Map<string, { xSum: number; ySum: number; count: number }>()
      const entry = deviceMap.get(port) || { xSum: 0, ySum: 0, count: 0 }
      entry.xSum += neighbor.x
      entry.ySum += neighbor.y
      entry.count += 1
      deviceMap.set(port, entry)
      map.set(deviceId, deviceMap)
    }

    props.links.forEach(link => {
      const fromRect = deviceViewMap.value.get(link.fromDeviceId)
      const toRect = deviceViewMap.value.get(link.toDeviceId)
      if (!fromRect || !toRect) return
      const fromCenter = { x: fromRect.x + fromRect.width / 2, y: fromRect.y + fromRect.height / 2 }
      const toCenter = { x: toRect.x + toRect.width / 2, y: toRect.y + toRect.height / 2 }
      if (link.fromPort) add(link.fromDeviceId, link.fromPort, toCenter)
      if (link.toPort) add(link.toDeviceId, link.toPort, fromCenter)
    })

    return map
  })

  const devicePortSideMap = computed(() => {
    const map = new Map<string, Map<string, Record<string, number>>>()

    const bump = (deviceId: string, port: string, side: string) => {
      const deviceMap = map.get(deviceId) || new Map<string, Record<string, number>>()
      const record = deviceMap.get(port) || { left: 0, right: 0, top: 0, bottom: 0 }
      record[side] = (record[side] || 0) + 1
      deviceMap.set(port, record)
      map.set(deviceId, deviceMap)
    }

    props.links.forEach(link => {
      const fromRect = deviceViewMap.value.get(link.fromDeviceId)
      const toRect = deviceViewMap.value.get(link.toDeviceId)
      if (!fromRect || !toRect) return
      const fromSide = resolveAutoSide(link.fromDeviceId, link.toDeviceId, link.fromPort)
      const toSide = resolveAutoSide(link.toDeviceId, link.fromDeviceId, link.toPort)
      if (link.fromPort) bump(link.fromDeviceId, link.fromPort, fromSide)
      if (link.toPort) bump(link.toDeviceId, link.toPort, toSide)
    })

    const resolved = new Map<string, Map<string, string>>()
    map.forEach((portVotes, deviceId) => {
      const portSide = new Map<string, string>()
      portVotes.forEach((votes, port) => {
        const entries = Object.entries(votes) as Array<[string, number]>
        entries.sort((a, b) => b[1] - a[1])
        portSide.set(port, entries[0]?.[0] || 'bottom')
      })
      resolved.set(deviceId, portSide)
    })

    if (portAnchorOverrides?.value) {
      portAnchorOverrides.value.forEach((ports, deviceId) => {
        const portSide = resolved.get(deviceId) || new Map<string, string>()
        ports.forEach((override, port) => {
          portSide.set(port, override.side)
        })
        resolved.set(deviceId, portSide)
      })
    }

    return resolved
  })

  const devicePortAnchors = computed(() => {
    const map = new Map<string, Map<string, { x: number; y: number; side: string }>>()
    const portEdgeInset = renderTuning.value.port_edge_inset ?? 0

    const resolveSidePortOrder = (deviceId: string, ports: string[]) => {
      const ordered = [...ports].sort(comparePorts)
      const overrides = portAnchorOverrides?.value?.get(deviceId)
      if (!overrides || overrides.size === 0) return ordered

      const total = ordered.length
      const effectiveRatio = new Map<string, number>()
      ordered.forEach((port, index) => {
        const override = overrides.get(port)
        if (override?.offsetRatio != null) {
          effectiveRatio.set(port, clamp(override.offsetRatio, 0, 1))
          return
        }
        effectiveRatio.set(port, (index + 1) / (total + 1))
      })

      ordered.sort((a, b) => {
        const delta = (effectiveRatio.get(a) ?? 0.5) - (effectiveRatio.get(b) ?? 0.5)
        if (Math.abs(delta) > 1e-6) return delta
        return comparePorts(a, b)
      })
      return ordered
    }

    devicePortList.value.forEach((ports, deviceId) => {
      const rect = deviceViewMap.value.get(deviceId)
      if (!rect || ports.length === 0) return
      const sideMap = devicePortSideMap.value.get(deviceId) || new Map<string, string>()
      const neighborMap = devicePortNeighbors.value.get(deviceId) || new Map<string, { xSum: number; ySum: number; count: number }>()
      const buckets: Record<string, string[]> = { left: [], right: [], top: [], bottom: [] }

      ports.forEach(port => {
        const side = sideMap.get(port) || 'bottom'
        buckets[side].push(port)
      })

      const anchors = new Map<string, { x: number; y: number; side: string }>()
      ;(['left', 'right'] as const).forEach(side => {
        const list = buckets[side]
        const count = list.length
        if (!count) return
        list.sort((a, b) => {
          const byPort = comparePorts(a, b)
          if (byPort !== 0) return byPort
          const na = neighborMap.get(a)
          const nb = neighborMap.get(b)
          const ay = na ? na.ySum / na.count : rect.y + rect.height / 2
          const by = nb ? nb.ySum / nb.count : rect.y + rect.height / 2
          if (ay !== by) return ay - by
          return 0
        })
        const spacing = (rect.height - portEdgeInset * 2) / (count + 1)
        list.forEach((port, index) => {
          const y = rect.y + portEdgeInset + spacing * (index + 1)
          const x = side === 'left' ? rect.x : rect.x + rect.width
          anchors.set(port, { x, y, side })
        })
      })
      ;(['top', 'bottom'] as const).forEach(side => {
        const list = resolveSidePortOrder(deviceId, buckets[side])
        const count = list.length
        if (!count) return
        const cellWidths = list.map(estimatePortCellWidth)
        const totalWidth = cellWidths.reduce((sum, width) => sum + width, 0) + DEVICE_PORT_CELL_GAP * Math.max(count - 1, 0)
        let cursorX = Math.max(DEVICE_PORT_BAND_PADDING_X, (rect.width - totalWidth) / 2)
        list.forEach((port, index) => {
          const width = cellWidths[index]
          const x = rect.x + cursorX + width / 2
          const y = side === 'top' ? rect.y : rect.y + rect.height
          anchors.set(port, { x, y, side })
          cursorX += width + DEVICE_PORT_CELL_GAP
        })
      })

      map.set(deviceId, anchors)
    })

    return map
  })

  function resolvePortAnchor(
    deviceId: string,
    rect: Rect,
    target: { x: number; y: number },
    portName?: string
  ) {
    const resolveTopBottomFallback = (port: string) => {
      const inset = renderTuning.value.port_edge_inset ?? 0
      const usableWidth = Math.max(rect.width - inset * 2, 1)
      const index = extractPortIndex(port)
      const ratio = index == null || Number.isNaN(index)
        ? clamp((target.x - rect.x - inset) / usableWidth, 0.1, 0.9)
        : ((index % 12) + 0.5) / 12
      const x = rect.x + inset + usableWidth * ratio
      const isTop = isUplinkPortName(port)
      const y = isTop ? rect.y : rect.y + rect.height
      return { x, y, side: isTop ? 'top' : 'bottom' }
    }

    if (portName) {
      const anchors = devicePortAnchors.value.get(deviceId)
      const anchor = anchors?.get(portName)
      if (anchor) return anchor
      return resolveTopBottomFallback(portName)
    }
    return {
      ...computePortAnchorFallback(rect, target, portName, renderTuning.value.port_edge_inset ?? 0),
      side: computeSide(rect, target)
    }
  }

  function resolvePortAnchorWithOverrides(
    deviceId: string,
    rect: Rect,
    target: { x: number; y: number },
    portName: string | undefined,
    overrides?: AnchorOverrideMap
  ) {
    if (portName && portAnchorOverrides?.value) {
      const deviceOverrides = portAnchorOverrides.value.get(deviceId)
      const override = deviceOverrides?.get(portName)
      if (override) {
        if (overrides) {
          const autoAnchor = overrides.get(deviceId)?.get(portName)
          if (autoAnchor && autoAnchor.side === override.side) return autoAnchor
        }
        const inset = renderTuning.value.port_edge_inset ?? 0
        const usableWidth = Math.max(rect.width - inset * 2, 1)
        const usableHeight = Math.max(rect.height - inset * 2, 1)
        if (override.offsetRatio == null) {
          const anchors = devicePortAnchors.value.get(deviceId)
          const autoAnchor = anchors?.get(portName)
          if (autoAnchor) return autoAnchor
          if (override.side === 'left' || override.side === 'right') {
            const ratio = clamp((target.y - rect.y - inset) / usableHeight, 0.1, 0.9)
            const y = rect.y + inset + usableHeight * ratio
            const x = override.side === 'left' ? rect.x : rect.x + rect.width
            return { x, y, side: override.side }
          }
          const ratio = clamp((target.x - rect.x - inset) / usableWidth, 0.1, 0.9)
          const x = rect.x + inset + usableWidth * ratio
          const y = override.side === 'top' ? rect.y : rect.y + rect.height
          return { x, y, side: override.side }
        }
        const ratio = clamp(override.offsetRatio, 0, 1)
        if (override.side === 'left' || override.side === 'right') {
          const y = rect.y + inset + usableHeight * ratio
          const x = override.side === 'left' ? rect.x : rect.x + rect.width
          return { x, y, side: override.side }
        }
        const x = rect.x + inset + usableWidth * ratio
        const y = override.side === 'top' ? rect.y : rect.y + rect.height
        return { x, y, side: override.side }
      }
    }
    if (portName && overrides) {
      const deviceOverrides = overrides.get(deviceId)
      const anchor = deviceOverrides?.get(portName)
      if (anchor) return anchor
    }
    return resolvePortAnchor(deviceId, rect, target, portName)
  }

  return {
    devicePortList,
    devicePortOrder,
    devicePortNeighbors,
    devicePortSideMap,
    devicePortAnchors,
    resolvePortAnchor,
    resolvePortAnchorWithOverrides,
  }
}
