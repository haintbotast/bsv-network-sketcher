import { computed, type ComputedRef } from 'vue'
import type { LinkModel, L2AssignmentRecord, ViewMode } from '../../models/types'
import type { Rect, AnchorOverrideMap, RenderTuning, PortAnchorOverrideMap } from './linkRoutingTypes'
import { clamp, comparePorts, computePortAnchorFallback, computeSide } from './linkRoutingUtils'

export function usePortAnchors(deps: {
  props: {
    links: LinkModel[]
    l2Assignments?: L2AssignmentRecord[]
    viewMode?: ViewMode
  }
  renderTuning: ComputedRef<RenderTuning>
  deviceViewMap: ComputedRef<Map<string, Rect>>
  portAnchorOverrides?: ComputedRef<PortAnchorOverrideMap>
}) {
  const { props, renderTuning, deviceViewMap, portAnchorOverrides } = deps

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
      const fromSide = computeSide(fromRect, { x: toRect.x + toRect.width / 2, y: toRect.y + toRect.height / 2 })
      const toSide = computeSide(toRect, { x: fromRect.x + fromRect.width / 2, y: fromRect.y + fromRect.height / 2 })
      if (link.fromPort) bump(link.fromDeviceId, link.fromPort, fromSide)
      if (link.toPort) bump(link.toDeviceId, link.toPort, toSide)
    })

    const resolved = new Map<string, Map<string, string>>()
    map.forEach((portVotes, deviceId) => {
      const portSide = new Map<string, string>()
      portVotes.forEach((votes, port) => {
        const entries = Object.entries(votes) as Array<[string, number]>
        entries.sort((a, b) => b[1] - a[1])
        portSide.set(port, entries[0]?.[0] || 'right')
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

    devicePortList.value.forEach((ports, deviceId) => {
      const rect = deviceViewMap.value.get(deviceId)
      if (!rect || ports.length === 0) return
      const sideMap = devicePortSideMap.value.get(deviceId) || new Map<string, string>()
      const orderMap = devicePortOrder.value.get(deviceId) || new Map<string, number>()
      const neighborMap = devicePortNeighbors.value.get(deviceId) || new Map<string, { xSum: number; ySum: number; count: number }>()
      const buckets: Record<string, string[]> = { left: [], right: [], top: [], bottom: [] }

      ports.forEach(port => {
        const side = sideMap.get(port) || 'right'
        buckets[side].push(port)
      })

      // --- Port side capacity rebalancing ---
      // If too many ports assigned to one side, move excess to adjacent sides
      const baseSpacing = renderTuning.value.bundle_gap ?? 22
      const labelOffset = renderTuning.value.port_label_offset ?? 0
      const labelInset = 6
      const effectiveLabelOffset = Math.max(0, labelOffset - labelInset)
      const minSpacing = baseSpacing + effectiveLabelOffset
      const sideCap = (s: string) => {
        const len = (s === 'left' || s === 'right') ? rect.height : rect.width
        return Math.max(1, Math.floor((len - portEdgeInset * 2) / minSpacing))
      }
      const adjSides: Record<string, [string, string]> = {
        left: ['top', 'bottom'], right: ['top', 'bottom'],
        top: ['left', 'right'], bottom: ['left', 'right']
      }
      const sideAlign = (side: string, n: { xSum: number; ySum: number; count: number } | undefined) => {
        if (!n) return 0
        const cx = rect.x + rect.width / 2
        const cy = rect.y + rect.height / 2
        const nx = n.xSum / n.count
        const ny = n.ySum / n.count
        if (side === 'left') return -(nx - cx)
        if (side === 'right') return nx - cx
        if (side === 'top') return -(ny - cy)
        return ny - cy
      }
      for (const side of ['left', 'right', 'top', 'bottom']) {
        const list = buckets[side]
        const cap = sideCap(side)
        if (list.length <= cap) continue
        // Keep ports most aligned with this side, move the rest
        list.sort((a, b) => sideAlign(side, neighborMap.get(b)) - sideAlign(side, neighborMap.get(a)))
        const excess = list.splice(cap)
        const [adj0, adj1] = adjSides[side]
        for (const port of excess) {
          const s0 = sideCap(adj0) - buckets[adj0].length
          const s1 = sideCap(adj1) - buckets[adj1].length
          if (s0 <= 0 && s1 <= 0) { list.push(port); continue }
          if (s0 <= 0) { buckets[adj1].push(port); continue }
          if (s1 <= 0) { buckets[adj0].push(port); continue }
          // Both have space - pick side more aligned with port's neighbor
          const a0 = sideAlign(adj0, neighborMap.get(port))
          const a1 = sideAlign(adj1, neighborMap.get(port))
          buckets[a0 >= a1 ? adj0 : adj1].push(port)
        }
      }

      const anchors = new Map<string, { x: number; y: number; side: string }>()
      ;(['left', 'right'] as const).forEach(side => {
        const list = buckets[side]
        const count = list.length
        if (!count) return
        list.sort((a, b) => {
          const na = neighborMap.get(a)
          const nb = neighborMap.get(b)
          const ay = na ? na.ySum / na.count : rect.y + rect.height / 2
          const by = nb ? nb.ySum / nb.count : rect.y + rect.height / 2
          if (ay !== by) return ay - by
          return comparePorts(a, b)
        })
        const spacing = (rect.height - portEdgeInset * 2) / (count + 1)
        list.forEach((port, index) => {
          const y = rect.y + portEdgeInset + spacing * (index + 1)
          const x = side === 'left' ? rect.x : rect.x + rect.width
          anchors.set(port, { x, y, side })
        })
      })
      ;(['top', 'bottom'] as const).forEach(side => {
        const list = buckets[side]
        const count = list.length
        if (!count) return
        list.sort((a, b) => {
          const na = neighborMap.get(a)
          const nb = neighborMap.get(b)
          const ax = na ? na.xSum / na.count : rect.x + rect.width / 2
          const bx = nb ? nb.xSum / nb.count : rect.x + rect.width / 2
          if (ax !== bx) return ax - bx
          return comparePorts(a, b)
        })
        const spacing = (rect.width - portEdgeInset * 2) / (count + 1)
        list.forEach((port, index) => {
          const x = rect.x + portEdgeInset + spacing * (index + 1)
          const y = side === 'top' ? rect.y : rect.y + rect.height
          anchors.set(port, { x, y, side })
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
    if (portName) {
      const anchors = devicePortAnchors.value.get(deviceId)
      const anchor = anchors?.get(portName)
      if (anchor) return anchor
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
