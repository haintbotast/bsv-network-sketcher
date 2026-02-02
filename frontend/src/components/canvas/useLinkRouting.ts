import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { AreaModel, DeviceModel, L2AssignmentRecord, LinkModel, ViewMode, Viewport } from '../../models/types'
import { addOccupancy, buildGridSpec, connectOrthogonal, routeOrthogonalPath, simplifyOrthogonalPath } from '../../utils/link_routing'
import { computeCrossings, drawPolylineWithJumps } from '../../utils/line_crossings'
import type { Crossing } from '../../utils/line_crossings'

export type Rect = { x: number; y: number; width: number; height: number }

type RenderLink = {
  id: string
  fromAnchor: { x: number; y: number; side?: string }
  toAnchor: { x: number; y: number; side?: string }
  fromCenter: { x: number; y: number }
  toCenter: { x: number; y: number }
  points: number[]
  config: Record<string, unknown>
}

type AnchorOverrideMap = Map<string, Map<string, { x: number; y: number; side: string }>>

type RenderTuning = {
  port_edge_inset?: number
  port_label_offset?: number
  bundle_gap?: number
  bundle_stub?: number
  area_clearance?: number
  area_anchor_offset?: number
  label_gap_x?: number
  label_gap_y?: number
  corridor_gap?: number
}

type UseLinkRoutingParams = {
  props: {
    links: LinkModel[]
    areas: AreaModel[]
    devices: DeviceModel[]
    viewMode?: ViewMode
    l2Assignments?: L2AssignmentRecord[]
  }
  layoutViewport: Ref<Viewport>
  renderTuning: ComputedRef<RenderTuning>
  deviceViewMap: ComputedRef<Map<string, Rect>>
  areaViewMap: ComputedRef<Map<string, Rect>>
  deviceAreaMap: ComputedRef<Map<string, string>>
  areaBounds: ComputedRef<{ minX: number; minY: number; maxX: number; maxY: number } | null>
  isPanning: Ref<boolean>
}

function clamp(value: number, min: number, max: number) {
  if (Number.isNaN(value)) return min
  if (value < min) return min
  if (value > max) return max
  return value
}

function comparePorts(a: string, b: string) {
  const normalize = (value: string) => value.trim().toLowerCase()
  const na = normalize(a)
  const nb = normalize(b)
  if (na === nb) return 0
  const prefixMatchA = na.match(/^([a-z\-]+)\s*/)
  const prefixMatchB = nb.match(/^([a-z\-]+)\s*/)
  const prefixA = prefixMatchA ? prefixMatchA[1] : na
  const prefixB = prefixMatchB ? prefixMatchB[1] : nb
  if (prefixA !== prefixB) return prefixA.localeCompare(prefixB)
  const numsA = na.match(/\d+/g)?.map(Number) || []
  const numsB = nb.match(/\d+/g)?.map(Number) || []
  const len = Math.max(numsA.length, numsB.length)
  for (let i = 0; i < len; i += 1) {
    const va = numsA[i] ?? -1
    const vb = numsB[i] ?? -1
    if (va !== vb) return va - vb
  }
  return na.localeCompare(nb)
}

function extractPortIndex(portName?: string) {
  if (!portName) return null
  const match = portName.match(/(\d+)(?!.*\d)/)
  if (!match) return null
  return Number.parseInt(match[1], 10)
}

function computePortAnchorFallback(
  rect: Rect,
  target: { x: number; y: number },
  portName: string | undefined,
  portEdgeInset: number
) {
  const center = { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 }
  const dx = target.x - center.x
  const dy = target.y - center.y
  const index = extractPortIndex(portName)
  const usableHeight = Math.max(rect.height - portEdgeInset * 2, 1)
  const usableWidth = Math.max(rect.width - portEdgeInset * 2, 1)
  const ratioFromTargetY = clamp((target.y - rect.y - portEdgeInset) / usableHeight, 0.1, 0.9)
  const ratioFromTargetX = clamp((target.x - rect.x - portEdgeInset) / usableWidth, 0.1, 0.9)
  const ratio = index == null || Number.isNaN(index)
    ? (Math.abs(dx) >= Math.abs(dy) ? ratioFromTargetY : ratioFromTargetX)
    : ((index % 12) + 0.5) / 12
  if (Math.abs(dx) >= Math.abs(dy)) {
    const x = dx >= 0 ? rect.x + rect.width : rect.x
    const y = rect.y + portEdgeInset + usableHeight * ratio
    return { x, y }
  }
  const y = dy >= 0 ? rect.y + rect.height : rect.y
  const x = rect.x + portEdgeInset + usableWidth * ratio
  return { x, y }
}

function computeSide(rect: Rect, target: { x: number; y: number }) {
  const center = { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 }
  const dx = target.x - center.x
  const dy = target.y - center.y
  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx >= 0 ? 'right' : 'left'
  }
  return dy >= 0 ? 'bottom' : 'top'
}

function computePortLabelPlacement(
  anchor: { x: number; y: number },
  center: { x: number; y: number },
  textWidth: number,
  labelHeight: number,
  labelOffset: number
) {
  const dx = anchor.x - center.x
  const dy = anchor.y - center.y
  if (Math.abs(dx) >= Math.abs(dy)) {
    const x = dx >= 0 ? anchor.x + labelOffset : anchor.x - textWidth - labelOffset
    const y = anchor.y - labelHeight / 2
    return { x, y }
  }
  const x = anchor.x - textWidth / 2
  const y = dy >= 0 ? anchor.y + labelOffset : anchor.y - labelHeight - labelOffset
  return { x, y }
}

function normalizeVector(dx: number, dy: number) {
  const len = Math.hypot(dx, dy)
  if (!len) return { x: 0, y: 0 }
  return { x: dx / len, y: dy / len }
}

function offsetFromAnchor(anchor: { x: number; y: number; side?: string }, distance: number) {
  const side = anchor.side || 'right'
  if (side === 'left') return { x: anchor.x - distance, y: anchor.y }
  if (side === 'right') return { x: anchor.x + distance, y: anchor.y }
  if (side === 'top') return { x: anchor.x, y: anchor.y - distance }
  return { x: anchor.x, y: anchor.y + distance }
}

function pointInRect(point: { x: number; y: number }, rect: Rect, margin = 0) {
  return (
    point.x >= rect.x - margin &&
    point.x <= rect.x + rect.width + margin &&
    point.y >= rect.y - margin &&
    point.y <= rect.y + rect.height + margin
  )
}

function segmentIntersectsRect(
  p1: { x: number; y: number },
  p2: { x: number; y: number },
  rect: Rect,
  margin = 0
) {
  if (pointInRect(p1, rect, margin) || pointInRect(p2, rect, margin)) return true

  const left = rect.x - margin
  const right = rect.x + rect.width + margin
  const top = rect.y - margin
  const bottom = rect.y + rect.height + margin

  const edges = [
    [{ x: left, y: top }, { x: right, y: top }],
    [{ x: right, y: top }, { x: right, y: bottom }],
    [{ x: right, y: bottom }, { x: left, y: bottom }],
    [{ x: left, y: bottom }, { x: left, y: top }]
  ]

  const ccw = (a: any, b: any, c: any) => (c.y - a.y) * (b.x - a.x) > (b.y - a.y) * (c.x - a.x)
  const intersects = (a: any, b: any, c: any, d: any) => ccw(a, c, d) !== ccw(b, c, d) && ccw(a, b, c) !== ccw(a, b, d)

  return edges.some(([a, b]) => intersects(p1, p2, a, b))
}

function computeAreaAnchor(
  areaRect: Rect,
  fromPoint: { x: number; y: number },
  targetPoint: { x: number; y: number },
  shift = 0,
  edgeOffset = 0
) {
  const dx = targetPoint.x - fromPoint.x
  const dy = targetPoint.y - fromPoint.y
  const inset = 4
  if (Math.abs(dx) >= Math.abs(dy)) {
    const x = dx >= 0 ? areaRect.x + areaRect.width + edgeOffset : areaRect.x - edgeOffset
    // Clamp base position first, then apply shift outside area bounds to preserve separation
    const baseY = clamp(fromPoint.y, areaRect.y + inset, areaRect.y + areaRect.height - inset)
    const y = baseY + shift
    return { x, y }
  }
  const y = dy >= 0 ? areaRect.y + areaRect.height + edgeOffset : areaRect.y - edgeOffset
  const baseX = clamp(fromPoint.x, areaRect.x + inset, areaRect.x + areaRect.width - inset)
  const x = baseX + shift
  return { x, y }
}

export function useLinkRouting(params: UseLinkRoutingParams) {
  const { props, layoutViewport, renderTuning, deviceViewMap, areaViewMap, deviceAreaMap, areaBounds, isPanning } = params

  const linkRouteCache = ref(new Map<string, {
    points: number[]
    fromAnchor: { x: number; y: number; side?: string }
    toAnchor: { x: number; y: number; side?: string }
    fromCenter: { x: number; y: number }
    toCenter: { x: number; y: number }
  }>())
  const linkRouteCacheViewport = ref<Viewport | null>(null)
  const visibleLinkCache = ref<RenderLink[]>([])

  const PORT_LABEL_HEIGHT = 16
  const PORT_LABEL_PADDING = 8
  const LABEL_SCALE_MIN = 0.6
  const LABEL_SCALE_MAX = 1.15
  const ARC_RADIUS = 5

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
          return (orderMap.get(a) ?? 0) - (orderMap.get(b) ?? 0)
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
          return (orderMap.get(a) ?? 0) - (orderMap.get(b) ?? 0)
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
    if (portName && overrides) {
      const deviceOverrides = overrides.get(deviceId)
      const anchor = deviceOverrides?.get(portName)
      if (anchor) return anchor
    }
    return resolvePortAnchor(deviceId, rect, target, portName)
  }

  const linkBundleIndex = computed(() => {
    const map = new Map<string, { index: number; total: number }>()
    const grouped = new Map<string, string[]>()

    const linkKey = (link: LinkModel) => {
      const from = link.fromDeviceId
      const to = link.toDeviceId
      return from < to ? `${from}|${to}` : `${to}|${from}`
    }

    props.links.forEach(link => {
      const key = linkKey(link)
      const list = grouped.get(key) || []
      list.push(link.id)
      grouped.set(key, list)
    })

    grouped.forEach(list => {
      list.sort()
      list.forEach((id, idx) => {
        map.set(id, { index: idx, total: list.length })
      })
    })
    return map
  })

  const areaBundleIndex = computed(() => {
    const map = new Map<string, { index: number; total: number }>()
    const grouped = new Map<string, string[]>()

    const areaKey = (fromArea: string, toArea: string) =>
      fromArea < toArea ? `${fromArea}|${toArea}` : `${toArea}|${fromArea}`

    props.links.forEach(link => {
      const fromArea = deviceAreaMap.value.get(link.fromDeviceId)
      const toArea = deviceAreaMap.value.get(link.toDeviceId)
      if (!fromArea || !toArea || fromArea === toArea) return
      const key = areaKey(fromArea, toArea)
      const list = grouped.get(key) || []
      list.push(link.id)
      grouped.set(key, list)
    })

    grouped.forEach(list => {
      list.sort()
      list.forEach((id, idx) => {
        map.set(id, { index: idx, total: list.length })
      })
    })

    return map
  })

  const waypointAreaMap = computed(() => {
    const map = new Map<string, { cx: number; cy: number; rect: Rect }>()
    const wpAreas = props.areas.filter(a => a.name.endsWith('_wp_'))
    if (wpAreas.length === 0) return map

    const nonWpAreas = props.areas.filter(a => !a.name.endsWith('_wp_'))
    const areaKey = (a: string, b: string) => a < b ? `${a}|${b}` : `${b}|${a}`

    for (const wp of wpAreas) {
      const rect = areaViewMap.value.get(wp.id)
      if (!rect) continue
      for (let i = 0; i < nonWpAreas.length; i += 1) {
        for (let j = i + 1; j < nonWpAreas.length; j += 1) {
          const names = [nonWpAreas[i].name, nonWpAreas[j].name].sort()
          if (wp.name === `${names[0]}_${names[1]}_wp_`) {
            map.set(areaKey(nonWpAreas[i].id, nonWpAreas[j].id), {
              cx: rect.x + rect.width / 2,
              cy: rect.y + rect.height / 2,
              rect
            })
          }
        }
      }
    }
    return map
  })

  const buildVisibleLinks = (useCache: boolean) => {
    const scale = clamp(layoutViewport.value.scale, LABEL_SCALE_MIN, LABEL_SCALE_MAX)
    if (useCache) {
      const cachedViewport = linkRouteCacheViewport.value
      if (cachedViewport && cachedViewport.scale === layoutViewport.value.scale) {
        const cached = linkRouteCache.value
        const dx = layoutViewport.value.offsetX - cachedViewport.offsetX
        const dy = layoutViewport.value.offsetY - cachedViewport.offsetY
        let canUseCache = cached.size === props.links.length && cached.size > 0
        const shifted = props.links
          .map(link => {
            const entry = cached.get(link.id)
            if (!entry) {
              canUseCache = false
              return null
            }
            const points = entry.points.map((value, idx) => value + (idx % 2 === 0 ? dx : dy))
            return {
              id: link.id,
              fromAnchor: { x: entry.fromAnchor.x + dx, y: entry.fromAnchor.y + dy, side: entry.fromAnchor.side },
              toAnchor: { x: entry.toAnchor.x + dx, y: entry.toAnchor.y + dy, side: entry.toAnchor.side },
              fromCenter: { x: entry.fromCenter.x + dx, y: entry.fromCenter.y + dy },
              toCenter: { x: entry.toCenter.x + dx, y: entry.toCenter.y + dy },
              points,
              config: {
                points,
                stroke: '#2b2a28',
                strokeWidth: 1.5,
                lineCap: 'round',
                lineJoin: 'round',
                dash: link.style === 'dashed' ? [8, 6] : link.style === 'dotted' ? [2, 4] : [],
                opacity: 0.8
              }
            }
          })
          .filter(Boolean) as RenderLink[]

        if (canUseCache) return { links: shifted, cache: null }
      }
    }

    const isL1View = (props.viewMode || 'L1') === 'L1'
    const clearance = (renderTuning.value.area_clearance ?? 0) * scale
    const gridBase = Math.max(6, Math.round((renderTuning.value.area_clearance ?? 0) * 0.5 * scale))
    const minSegment = Math.max(4, Math.round(6 * scale))
    const maxRouteLinks = 400
    const maxGridNodes = 30000

    let minX = Number.POSITIVE_INFINITY
    let minY = Number.POSITIVE_INFINITY
    let maxX = Number.NEGATIVE_INFINITY
    let maxY = Number.NEGATIVE_INFINITY

    areaViewMap.value.forEach(rect => {
      minX = Math.min(minX, rect.x)
      minY = Math.min(minY, rect.y)
      maxX = Math.max(maxX, rect.x + rect.width)
      maxY = Math.max(maxY, rect.y + rect.height)
    })
    deviceViewMap.value.forEach(rect => {
      minX = Math.min(minX, rect.x)
      minY = Math.min(minY, rect.y)
      maxX = Math.max(maxX, rect.x + rect.width)
      maxY = Math.max(maxY, rect.y + rect.height)
    })

    const padding = (renderTuning.value.corridor_gap ?? 0) * scale + clearance + gridBase * 2
    const grid = Number.isFinite(minX)
      ? buildGridSpec(
        { minX: minX - padding, minY: minY - padding, maxX: maxX + padding, maxY: maxY + padding },
        gridBase
      )
      : null

    const areaRects = Array.from(areaViewMap.value.entries()).map(([id, rect]) => ({ id, rect }))
    const deviceRects = Array.from(deviceViewMap.value.entries()).map(([id, rect]) => ({ id, rect }))

    const appendPoints = (arr: { x: number; y: number }[], points: { x: number; y: number }[]) => {
      points.forEach(point => {
        const last = arr[arr.length - 1]
        if (last && last.x === point.x && last.y === point.y) return
        arr.push(point)
      })
    }

    const gridNodeCount = grid ? grid.cols * grid.rows : 0
    const allowAStar = isL1View && grid && props.links.length <= maxRouteLinks && gridNodeCount > 0 && gridNodeCount <= maxGridNodes

    const areaCenters = new Map<string, { x: number; y: number }>()
    areaRects.forEach(({ id, rect }) => {
      areaCenters.set(id, { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 })
    })

    const laneAxisByPair = new Map<string, 'x' | 'y'>()

    const getPairKey = (fromArea: string, toArea: string) =>
      fromArea < toArea ? `${fromArea}|${toArea}` : `${toArea}|${fromArea}`

    const resolveLaneAxis = (fromAreaId: string, toAreaId: string) => {
      const key = getPairKey(fromAreaId, toAreaId)
      const cached = laneAxisByPair.get(key)
      if (cached) return cached
      const fromCenter = areaCenters.get(fromAreaId)
      const toCenter = areaCenters.get(toAreaId)
      if (!fromCenter || !toCenter) return 'y'
      const dx = toCenter.x - fromCenter.x
      const dy = toCenter.y - fromCenter.y
      const axis = Math.abs(dx) >= Math.abs(dy) ? 'y' : 'x'
      laneAxisByPair.set(key, axis)
      return axis
    }

    const buildLinkMetaData = (anchorOverrides?: AnchorOverrideMap) => {
      const laneGroups = new Map<string, Array<{ id: string; order: number; portBias: number }>>()
      const linkMetas = props.links.map(link => {
        const fromView = deviceViewMap.value.get(link.fromDeviceId)
        const toView = deviceViewMap.value.get(link.toDeviceId)
        if (!fromView || !toView) return null
        const fromCenter = { x: fromView.x + fromView.width / 2, y: fromView.y + fromView.height / 2 }
        const toCenter = { x: toView.x + toView.width / 2, y: toView.y + toView.height / 2 }
        const fromAnchor = resolvePortAnchorWithOverrides(link.fromDeviceId, fromView, toCenter, link.fromPort, anchorOverrides)
        const toAnchor = resolvePortAnchorWithOverrides(link.toDeviceId, toView, fromCenter, link.toPort, anchorOverrides)
        const fromAreaId = deviceAreaMap.value.get(link.fromDeviceId)
        const toAreaId = deviceAreaMap.value.get(link.toDeviceId)
        const fromArea = fromAreaId ? areaViewMap.value.get(fromAreaId) : null
        const toArea = toAreaId ? areaViewMap.value.get(toAreaId) : null

        if (fromAreaId && toAreaId && fromAreaId !== toAreaId && fromArea && toArea) {
          const axis = resolveLaneAxis(fromAreaId, toAreaId)
          const order = axis === 'y'
            ? (fromAnchor.y + toAnchor.y) / 2
            : (fromAnchor.x + toAnchor.x) / 2
          const fromOrder = link.fromPort
            ? devicePortOrder.value.get(link.fromDeviceId)?.get(link.fromPort)
            : null
          const toOrder = link.toPort
            ? devicePortOrder.value.get(link.toDeviceId)?.get(link.toPort)
            : null
          const fromCount = link.fromPort
            ? (devicePortList.value.get(link.fromDeviceId)?.length ?? 0)
            : 0
          const toCount = link.toPort
            ? (devicePortList.value.get(link.toDeviceId)?.length ?? 0)
            : 0
          const fromNorm = fromOrder != null && fromCount > 1 ? fromOrder / (fromCount - 1) : null
          const toNorm = toOrder != null && toCount > 1 ? toOrder / (toCount - 1) : null
          const portBias = ((fromNorm ?? 0.5) + (toNorm ?? 0.5)) / 2
          const key = getPairKey(fromAreaId, toAreaId)
          const list = laneGroups.get(key) || []
          list.push({ id: link.id, order, portBias })
          laneGroups.set(key, list)
        }

        return {
          link,
          fromView,
          toView,
          fromCenter,
          toCenter,
          fromAnchor,
          toAnchor,
          fromAreaId,
          toAreaId,
          fromArea,
          toArea
        }
      })

      const labelObstacles: Array<{ linkId: string; rect: Rect }> = []
      if (isL1View) {
        const labelScale = clamp(layoutViewport.value.scale, LABEL_SCALE_MIN, LABEL_SCALE_MAX)
        const labelHeight = PORT_LABEL_HEIGHT * labelScale
        const labelPadding = PORT_LABEL_PADDING * labelScale
        const labelOffset = (renderTuning.value.port_label_offset ?? 0) * labelScale
        const minLabelWidth = 24 * labelScale
        const charWidth = 6 * labelScale
        const baseGap = Math.max(2, Math.min(renderTuning.value.label_gap_x ?? 0, renderTuning.value.label_gap_y ?? 0) * 0.5 * labelScale)

        const buildLabelRect = (
          linkId: string,
          text: string | undefined,
          anchor: { x: number; y: number },
          center: { x: number; y: number },
          neighbor: { x: number; y: number }
        ) => {
          const content = text?.trim()
          if (!content) return
          const width = Math.max(content.length * charWidth + labelPadding, minLabelWidth)
          const height = labelHeight
          const dx = neighbor.x - anchor.x
          const dy = neighbor.y - anchor.y
          const len = Math.hypot(dx, dy)
          let cx: number
          let cy: number
          if (len < 1) {
            const pos = computePortLabelPlacement(anchor, center, width, height, labelOffset)
            cx = pos.x + width / 2
            cy = pos.y + height / 2
          } else {
            const offset = (width / 2 + 4) / len
            cx = anchor.x + dx * offset
            cy = anchor.y + dy * offset
          }
          labelObstacles.push({
            linkId,
            rect: {
              x: cx - width / 2 - baseGap,
              y: cy - height / 2 - baseGap,
              width: width + baseGap * 2,
              height: height + baseGap * 2,
            }
          })
        }

        linkMetas.forEach(meta => {
          if (!meta) return
          buildLabelRect(meta.link.id, meta.link.fromPort, meta.fromAnchor, meta.fromCenter, meta.toCenter)
          buildLabelRect(meta.link.id, meta.link.toPort, meta.toAnchor, meta.toCenter, meta.fromCenter)
        })
      }

      const laneIndex = new Map<string, { index: number; total: number }>()
      laneGroups.forEach(list => {
        list.sort((a, b) => {
          const primary = a.order - b.order
          if (primary !== 0) return primary
          const secondary = a.portBias - b.portBias
          if (secondary !== 0) return secondary
          return a.id.localeCompare(b.id)
        })
        list.forEach((entry, idx) => {
          laneIndex.set(entry.id, { index: idx, total: list.length })
        })
      })

      return { linkMetas, laneIndex, labelObstacles }
    }

    const buildAnchorOverrides = (
      linkMetas: Array<any>,
      cache: Map<string, { points: number[]; fromAnchor: { x: number; y: number; side?: string }; toAnchor: { x: number; y: number; side?: string } }>
    ): AnchorOverrideMap => {
      const portStats = new Map<string, Map<string, {
        votes: Record<'left' | 'right' | 'top' | 'bottom', number>
        coords: Record<'left' | 'right' | 'top' | 'bottom', { sum: number; count: number }>
      }>>()
      const portPairRank = new Map<string, Map<string, { rank: number; count: number; neighborId: string }>>()
      const portNeighborDevice = new Map<string, Map<string, string>>()
      const portForcedSide = new Map<string, Map<string, 'left' | 'right' | 'top' | 'bottom'>>()
      const portAlignedCoord = new Map<string, Map<string, { axis: 'x' | 'y'; coord: number }>>()

      const registerPairRank = (deviceId: string, port: string, rank: number, count: number, neighborId: string) => {
        const deviceMap = portPairRank.get(deviceId) || new Map<string, { rank: number; count: number; neighborId: string }>()
        deviceMap.set(port, { rank, count, neighborId })
        portPairRank.set(deviceId, deviceMap)
      }

      const registerNeighborDevice = (deviceId: string, port: string, neighborId: string) => {
        const deviceMap = portNeighborDevice.get(deviceId) || new Map<string, string>()
        deviceMap.set(port, neighborId)
        portNeighborDevice.set(deviceId, deviceMap)
      }

      const registerForcedSide = (deviceId: string, port: string, side: 'left' | 'right' | 'top' | 'bottom') => {
        const deviceMap = portForcedSide.get(deviceId) || new Map<string, 'left' | 'right' | 'top' | 'bottom'>()
        deviceMap.set(port, side)
        portForcedSide.set(deviceId, deviceMap)
      }

      const registerForcedSideIfUnset = (deviceId: string, port: string, side: 'left' | 'right' | 'top' | 'bottom') => {
        const deviceMap = portForcedSide.get(deviceId) || new Map<string, 'left' | 'right' | 'top' | 'bottom'>()
        if (!deviceMap.has(port)) {
          deviceMap.set(port, side)
          portForcedSide.set(deviceId, deviceMap)
        }
      }

      const registerAlignedCoord = (deviceId: string, port: string, axis: 'x' | 'y', coord: number) => {
        const deviceMap = portAlignedCoord.get(deviceId) || new Map<string, { axis: 'x' | 'y'; coord: number }>()
        deviceMap.set(port, { axis, coord })
        portAlignedCoord.set(deviceId, deviceMap)
      }

      const ensureStats = (deviceId: string, port: string) => {
        const deviceMap = portStats.get(deviceId) || new Map()
        if (!deviceMap.has(port)) {
          deviceMap.set(port, {
            votes: { left: 0, right: 0, top: 0, bottom: 0 },
            coords: {
              left: { sum: 0, count: 0 },
              right: { sum: 0, count: 0 },
              top: { sum: 0, count: 0 },
              bottom: { sum: 0, count: 0 }
            }
          })
          portStats.set(deviceId, deviceMap)
        }
        return deviceMap.get(port)!
      }

      const record = (deviceId: string, port: string, side: 'left' | 'right' | 'top' | 'bottom', coord: number) => {
        const entry = ensureStats(deviceId, port)
        entry.votes[side] += 1
        entry.coords[side].sum += coord
        entry.coords[side].count += 1
      }

      const isOppositeSide = (a: string, b: string) => {
        return (
          (a === 'left' && b === 'right') ||
          (a === 'right' && b === 'left') ||
          (a === 'top' && b === 'bottom') ||
          (a === 'bottom' && b === 'top')
        )
      }

      const pairGroups = new Map<string, Array<{
        fromDeviceId: string
        toDeviceId: string
        fromPort?: string
        toPort?: string
        fromSide: 'left' | 'right' | 'top' | 'bottom'
        toSide: 'left' | 'right' | 'top' | 'bottom'
      }>>()

      linkMetas.forEach(meta => {
        if (!meta) return
        const entry = cache.get(meta.link.id)
        if (!entry) return
        const pts = entry.points
        const fromNext = pts.length >= 4
          ? { x: pts[2], y: pts[3] }
          : { x: entry.toAnchor.x, y: entry.toAnchor.y }
        const toPrev = pts.length >= 4
          ? { x: pts[pts.length - 4], y: pts[pts.length - 3] }
          : { x: entry.fromAnchor.x, y: entry.fromAnchor.y }
        const fromSide = (entry.fromAnchor.side || computeSide(meta.fromView, meta.toCenter)) as 'left' | 'right' | 'top' | 'bottom'
        const toSide = (entry.toAnchor.side || computeSide(meta.toView, meta.fromCenter)) as 'left' | 'right' | 'top' | 'bottom'

        if (meta.link.fromPort) {
          const coord = fromSide === 'left' || fromSide === 'right' ? fromNext.y : fromNext.x
          record(meta.link.fromDeviceId, meta.link.fromPort, fromSide, coord)
          registerNeighborDevice(meta.link.fromDeviceId, meta.link.fromPort, meta.link.toDeviceId)
        }
        if (meta.link.toPort) {
          const coord = toSide === 'left' || toSide === 'right' ? toPrev.y : toPrev.x
          record(meta.link.toDeviceId, meta.link.toPort, toSide, coord)
          registerNeighborDevice(meta.link.toDeviceId, meta.link.toPort, meta.link.fromDeviceId)
        }

        if (isL1View && meta.link.fromPort && meta.link.toPort) {
          const fromCenter = meta.fromCenter
          const toCenter = meta.toCenter
          const fromView = meta.fromView
          const toView = meta.toView
          const dxCenter = toCenter.x - fromCenter.x
          const dyCenter = toCenter.y - fromCenter.y
          const rowTolerance = Math.min(fromView.height, toView.height) * 0.35
          const colTolerance = Math.min(fromView.width, toView.width) * 0.35
          let axis: 'x' | 'y' | null = null
          if (Math.abs(dyCenter) <= rowTolerance && Math.abs(dxCenter) >= Math.abs(dyCenter)) {
            axis = 'y'
          } else if (Math.abs(dxCenter) <= colTolerance && Math.abs(dyCenter) > Math.abs(dxCenter)) {
            axis = 'x'
          }

          if (axis) {
            const portEdgeInset = renderTuning.value.port_edge_inset ?? 0
            const bundle = linkBundleIndex.value.get(meta.link.id)
            const bundleGap = Math.max(6, (renderTuning.value.bundle_gap ?? 0) * scale * 0.6)
            const bundleOffset = bundle && bundle.total > 1
              ? (bundle.index - (bundle.total - 1) / 2) * bundleGap
              : 0
            const baseCoord = axis === 'y'
              ? (fromCenter.y + toCenter.y) / 2
              : (fromCenter.x + toCenter.x) / 2

            const fromMin = axis === 'y'
              ? fromView.y + portEdgeInset
              : fromView.x + portEdgeInset
            const fromMax = axis === 'y'
              ? fromView.y + fromView.height - portEdgeInset
              : fromView.x + fromView.width - portEdgeInset
            const toMin = axis === 'y'
              ? toView.y + portEdgeInset
              : toView.x + portEdgeInset
            const toMax = axis === 'y'
              ? toView.y + toView.height - portEdgeInset
              : toView.x + toView.width - portEdgeInset
            const minCoord = Math.max(fromMin, toMin)
            const maxCoord = Math.min(fromMax, toMax)
            if (minCoord <= maxCoord) {
              const coord = clamp(baseCoord + bundleOffset, minCoord, maxCoord)
              const fromSide = axis === 'y'
                ? (toCenter.x >= fromCenter.x ? 'right' : 'left')
                : (toCenter.y >= fromCenter.y ? 'bottom' : 'top')
              const toSide = axis === 'y'
                ? (fromCenter.x >= toCenter.x ? 'right' : 'left')
                : (fromCenter.y >= toCenter.y ? 'bottom' : 'top')

              const fromAnchor = axis === 'y'
                ? { x: fromSide === 'left' ? fromView.x : fromView.x + fromView.width, y: coord }
                : { x: coord, y: fromSide === 'top' ? fromView.y : fromView.y + fromView.height }
              const toAnchor = axis === 'y'
                ? { x: toSide === 'left' ? toView.x : toView.x + toView.width, y: coord }
                : { x: coord, y: toSide === 'top' ? toView.y : toView.y + toView.height }

              const obstacles: Rect[] = []
              deviceRects.forEach(({ id, rect }) => {
                if (id === meta.link.fromDeviceId || id === meta.link.toDeviceId) return
                obstacles.push(rect)
              })
              if (meta.fromAreaId && meta.toAreaId && meta.fromAreaId !== meta.toAreaId) {
                areaRects.forEach(({ id, rect }) => {
                  if (id === meta.fromAreaId || id === meta.toAreaId) return
                  obstacles.push(rect)
                })
              }

              const blocked = obstacles.some(rect =>
                segmentIntersectsRect(fromAnchor, toAnchor, rect, clearance)
              )

              if (!blocked) {
                registerAlignedCoord(meta.link.fromDeviceId, meta.link.fromPort, axis, coord)
                registerAlignedCoord(meta.link.toDeviceId, meta.link.toPort, axis, coord)
                registerForcedSideIfUnset(meta.link.fromDeviceId, meta.link.fromPort, fromSide)
                registerForcedSideIfUnset(meta.link.toDeviceId, meta.link.toPort, toSide)
              }
            }
          }
        }

        if (meta.link.fromPort && meta.link.toPort) {
          const a = meta.link.fromDeviceId
          const b = meta.link.toDeviceId
          const pairKey = a < b ? `${a}|${b}` : `${b}|${a}`
          const list = pairGroups.get(pairKey) || []
          list.push({
            fromDeviceId: meta.link.fromDeviceId,
            toDeviceId: meta.link.toDeviceId,
            fromPort: meta.link.fromPort,
            toPort: meta.link.toPort,
            fromSide,
            toSide
          })
          pairGroups.set(pairKey, list)
        }
      })

      pairGroups.forEach(list => {
        if (list.length < 2) return
        const orientationByDevice = new Map<string, 'left' | 'right' | 'top' | 'bottom'>()
        let valid = true

        for (const entry of list) {
          if (!isOppositeSide(entry.fromSide, entry.toSide)) {
            valid = false
            break
          }
          const fromExisting = orientationByDevice.get(entry.fromDeviceId)
          if (fromExisting && fromExisting !== entry.fromSide) {
            valid = false
            break
          }
          orientationByDevice.set(entry.fromDeviceId, entry.fromSide)
          const toExisting = orientationByDevice.get(entry.toDeviceId)
          if (toExisting && toExisting !== entry.toSide) {
            valid = false
            break
          }
          orientationByDevice.set(entry.toDeviceId, entry.toSide)
        }

        if (!valid) return

        list.forEach(entry => {
          if (!entry.fromPort || !entry.toPort) return
          const fromOrder = devicePortOrder.value.get(entry.fromDeviceId)?.get(entry.fromPort) ?? 0
          const toOrder = devicePortOrder.value.get(entry.toDeviceId)?.get(entry.toPort) ?? 0
          registerPairRank(entry.fromDeviceId, entry.fromPort, toOrder, list.length, entry.toDeviceId)
          registerPairRank(entry.toDeviceId, entry.toPort, fromOrder, list.length, entry.fromDeviceId)
        })
      })

      pairGroups.forEach(list => {
        if (list.length < 2) return
        const first = list[0]
        const aRect = deviceViewMap.value.get(first.fromDeviceId)
        const bRect = deviceViewMap.value.get(first.toDeviceId)
        if (!aRect || !bRect) return
        const aCenter = { x: aRect.x + aRect.width / 2, y: aRect.y + aRect.height / 2 }
        const bCenter = { x: bRect.x + bRect.width / 2, y: bRect.y + bRect.height / 2 }
        const axis = Math.abs(bCenter.x - aCenter.x) >= Math.abs(bCenter.y - aCenter.y) ? 'x' : 'y'

        list.forEach(entry => {
          if (!entry.fromPort || !entry.toPort) return
          const fromRect = deviceViewMap.value.get(entry.fromDeviceId)
          const toRect = deviceViewMap.value.get(entry.toDeviceId)
          if (!fromRect || !toRect) return
          const fromCenter = { x: fromRect.x + fromRect.width / 2, y: fromRect.y + fromRect.height / 2 }
          const toCenter = { x: toRect.x + toRect.width / 2, y: toRect.y + toRect.height / 2 }
          const fromSide = axis === 'x'
            ? (toCenter.x >= fromCenter.x ? 'right' : 'left')
            : (toCenter.y >= fromCenter.y ? 'bottom' : 'top')
          const toSide = axis === 'x'
            ? (fromCenter.x >= toCenter.x ? 'right' : 'left')
            : (fromCenter.y >= toCenter.y ? 'bottom' : 'top')
          registerForcedSide(entry.fromDeviceId, entry.fromPort, fromSide)
          registerForcedSide(entry.toDeviceId, entry.toPort, toSide)
        })
      })

      const overrides: AnchorOverrideMap = new Map()
      const portEdgeInset = renderTuning.value.port_edge_inset ?? 0
      let overrideCount = 0

      devicePortList.value.forEach((ports, deviceId) => {
        const rect = deviceViewMap.value.get(deviceId)
        if (!rect || ports.length === 0) return
        const deviceStats = portStats.get(deviceId)
        if (!deviceStats) return
        const sideMap = devicePortSideMap.value.get(deviceId) || new Map<string, string>()
        const orderMap = devicePortOrder.value.get(deviceId) || new Map<string, number>()
        const neighborMap = devicePortNeighbors.value.get(deviceId) || new Map<string, { xSum: number; ySum: number; count: number }>()
        const pairMap = portPairRank.get(deviceId) || new Map<string, { rank: number; count: number; neighborId: string }>()
        const neighborDeviceMap = portNeighborDevice.get(deviceId) || new Map<string, string>()
        const forcedSideMap = portForcedSide.get(deviceId) || new Map<string, 'left' | 'right' | 'top' | 'bottom'>()
        const alignedCoordMap = portAlignedCoord.get(deviceId) || new Map<string, { axis: 'x' | 'y'; coord: number }>()
        const buckets: Record<'left' | 'right' | 'top' | 'bottom', Array<{
          port: string
          coord: number | null
          neighborCoord: number | null
          order: number
          pairRank: number | null
          pairKey: string | null
          fixedCoord: number | null
        }>> = { left: [], right: [], top: [], bottom: [] }

        ports.forEach(port => {
          const stats = deviceStats.get(port)
          let side = (sideMap.get(port) || 'right') as 'left' | 'right' | 'top' | 'bottom'
          const forcedSide = forcedSideMap.get(port)
          if (forcedSide) {
            side = forcedSide
          } else if (stats) {
            const entries = Object.entries(stats.votes) as Array<[string, number]>
            entries.sort((a, b) => b[1] - a[1])
            if (entries[0]?.[1] > 0) {
              side = entries[0][0] as 'left' | 'right' | 'top' | 'bottom'
            }
          }

          let coord: number | null = null
          if (stats) {
            const coordEntry = stats.coords[side]
            if (coordEntry.count > 0) coord = coordEntry.sum / coordEntry.count
          }
          const neighbor = neighborMap.get(port)
          const neighborCoord = neighbor
            ? (side === 'left' || side === 'right' ? neighbor.ySum / neighbor.count : neighbor.xSum / neighbor.count)
            : null
          const pairInfo = pairMap.get(port)
          const pairKey = pairInfo?.neighborId || neighborDeviceMap.get(port) || null
          const aligned = alignedCoordMap.get(port)
          const fixedCoord = aligned
            ? ((side === 'left' || side === 'right') && aligned.axis === 'y'
              ? aligned.coord
              : (side === 'top' || side === 'bottom') && aligned.axis === 'x'
                ? aligned.coord
                : null)
            : null

          buckets[side].push({
            port,
            coord,
            neighborCoord,
            order: orderMap.get(port) ?? 0,
            pairRank: pairInfo?.rank ?? null,
            pairKey,
            fixedCoord
          })
        })

        const anchors = new Map<string, { x: number; y: number; side: string }>()
        const sortEntries = (a: typeof buckets['left'][number], b: typeof buckets['left'][number]) => {
          if (a.pairKey && b.pairKey && a.pairKey === b.pairKey) {
            const ar = a.pairRank ?? 0
            const br = b.pairRank ?? 0
            if (ar !== br) return ar - br
          }
          if (a.fixedCoord != null && b.fixedCoord != null && a.fixedCoord !== b.fixedCoord) return a.fixedCoord - b.fixedCoord
          if (a.fixedCoord != null && b.fixedCoord == null) return -1
          if (a.fixedCoord == null && b.fixedCoord != null) return 1
          if (a.coord != null && b.coord != null && a.coord !== b.coord) return a.coord - b.coord
          if (a.coord != null && b.coord == null) return -1
          if (a.coord == null && b.coord != null) return 1
          if (a.neighborCoord != null && b.neighborCoord != null && a.neighborCoord !== b.neighborCoord) return a.neighborCoord - b.neighborCoord
          if (a.neighborCoord != null && b.neighborCoord == null) return -1
          if (a.neighborCoord == null && b.neighborCoord != null) return 1
          return a.order - b.order
        }

        const assignAnchorsForSide = (side: 'left' | 'right' | 'top' | 'bottom') => {
          const list = buckets[side]
          const count = list.length
          if (!count) return
          const isVertical = side === 'left' || side === 'right'
          const minCoord = isVertical ? rect.y + portEdgeInset : rect.x + portEdgeInset
          const maxCoord = isVertical ? rect.y + rect.height - portEdgeInset : rect.x + rect.width - portEdgeInset
          const span = Math.max(maxCoord - minCoord, 1)
          const baseSpacing = span / (count + 1)
          const minSpacing = Math.max(baseSpacing * 0.6, 4)

          const sorted = [...list].sort(sortEntries)
          const fixedCoords: number[] = []
          const fixedEntries: typeof list = []
          const groups: Array<typeof list> = []
          let currentGroup: typeof list = []

          sorted.forEach(entry => {
            if (entry.fixedCoord != null) {
              groups.push(currentGroup)
              currentGroup = []
              fixedEntries.push(entry)
              fixedCoords.push(clamp(entry.fixedCoord, minCoord, maxCoord))
            } else {
              currentGroup.push(entry)
            }
          })
          groups.push(currentGroup)

          const segments: Array<{ min: number; max: number }> = []
          let segStart = minCoord
          fixedCoords.forEach(coord => {
            segments.push({ min: segStart, max: coord - minSpacing })
            segStart = coord + minSpacing
          })
          segments.push({ min: segStart, max: maxCoord })

          const positions = new Map<string, number>()
          groups.forEach((group, idx) => {
            if (group.length === 0) return
            const segment = segments[idx] ?? { min: minCoord, max: maxCoord }
            const segMin = Math.min(segment.min, segment.max)
            const segMax = Math.max(segment.min, segment.max)
            const segSpan = Math.max(segMax - segMin, 0)
            if (segSpan <= 0) {
              const fallback = clamp(segMin, minCoord, maxCoord)
              group.forEach(entry => {
                positions.set(entry.port, fallback)
              })
              return
            }
            const spacing = segSpan / (group.length + 1)
            group.forEach((entry, index) => {
              positions.set(entry.port, segMin + spacing * (index + 1))
            })
          })

          fixedEntries.forEach((entry, index) => {
            positions.set(entry.port, fixedCoords[index])
          })

          sorted.forEach((entry, index) => {
            const coord = positions.get(entry.port) ?? (minCoord + baseSpacing * (index + 1))
            const x = isVertical
              ? (side === 'left' ? rect.x : rect.x + rect.width)
              : coord
            const y = isVertical
              ? coord
              : (side === 'top' ? rect.y : rect.y + rect.height)
            anchors.set(entry.port, { x, y, side })
          })
        }

        ;(['left', 'right'] as const).forEach(assignAnchorsForSide)
        ;(['top', 'bottom'] as const).forEach(assignAnchorsForSide)

        if (anchors.size) {
          overrides.set(deviceId, anchors)
          overrideCount += anchors.size
        }
      })

      if (overrideCount === 0) return new Map()
      return overrides
    }

    const computeLocalCorridor = (
      fromArea: Rect,
      toArea: Rect,
      fromExit: { x: number; y: number },
      toExit: { x: number; y: number },
      fromAreaId: string | null,
      toAreaId: string | null,
      interBundleOffset: number,
      clearanceValue: number
    ) => {
      const minGap = Math.max(6, clearanceValue + Math.abs(interBundleOffset))
      const fromRight = fromArea.x + fromArea.width
      const fromLeft = fromArea.x
      const fromTop = fromArea.y
      const fromBottom = fromArea.y + fromArea.height
      const toRight = toArea.x + toArea.width
      const toLeft = toArea.x
      const toTop = toArea.y
      const toBottom = toArea.y + toArea.height

      const isLeftRight = fromRight <= toLeft || toRight <= fromLeft
      const isTopBottom = fromBottom <= toTop || toBottom <= fromTop

      if (isLeftRight) {
        const leftRect = fromLeft < toLeft ? fromArea : toArea
        const rightRect = fromLeft < toLeft ? toArea : fromArea
        const gap = rightRect.x - (leftRect.x + leftRect.width)
        if (gap < minGap) return null
        const minCoord = leftRect.x + leftRect.width + clearanceValue
        const maxCoord = rightRect.x - clearanceValue
        if (minCoord >= maxCoord) return null
        const baseCoord = leftRect.x + leftRect.width + gap / 2
        const corridorX = clamp(baseCoord + interBundleOffset, minCoord, maxCoord)
        const fromAreaAnchor = computeAreaAnchor(fromArea, fromExit, toExit, interBundleOffset, 0)
        const toAreaAnchor = computeAreaAnchor(toArea, toExit, fromExit, interBundleOffset, 0)
        const segStart = { x: corridorX, y: fromAreaAnchor.y }
        const segEnd = { x: corridorX, y: toAreaAnchor.y }
        const blocked = areaRects.some(({ id, rect }) => {
          if (id === fromAreaId || id === toAreaId) return false
          return segmentIntersectsRect(segStart, segEnd, rect, clearanceValue)
        })
        if (blocked) return null
        return { axis: 'x' as const, coord: corridorX, fromAreaAnchor, toAreaAnchor }
      }

      if (isTopBottom) {
        const topRect = fromTop < toTop ? fromArea : toArea
        const bottomRect = fromTop < toTop ? toArea : fromArea
        const gap = bottomRect.y - (topRect.y + topRect.height)
        if (gap < minGap) return null
        const minCoord = topRect.y + topRect.height + clearanceValue
        const maxCoord = bottomRect.y - clearanceValue
        if (minCoord >= maxCoord) return null
        const baseCoord = topRect.y + topRect.height + gap / 2
        const corridorY = clamp(baseCoord + interBundleOffset, minCoord, maxCoord)
        const fromAreaAnchor = computeAreaAnchor(fromArea, fromExit, toExit, interBundleOffset, 0)
        const toAreaAnchor = computeAreaAnchor(toArea, toExit, fromExit, interBundleOffset, 0)
        const segStart = { x: fromAreaAnchor.x, y: corridorY }
        const segEnd = { x: toAreaAnchor.x, y: corridorY }
        const blocked = areaRects.some(({ id, rect }) => {
          if (id === fromAreaId || id === toAreaId) return false
          return segmentIntersectsRect(segStart, segEnd, rect, clearanceValue)
        })
        if (blocked) return null
        return { axis: 'y' as const, coord: corridorY, fromAreaAnchor, toAreaAnchor }
      }

      return null
    }

    const routeLinks = (
      linkMetas: Array<any>,
      laneIndex: Map<string, { index: number; total: number }>,
      labelObstacles: Array<{ linkId: string; rect: Rect }>
    ) => {
      const occupancy = new Map<string, number>()
      const cache = new Map<string, {
        points: number[]
        fromAnchor: { x: number; y: number; side?: string }
        toAnchor: { x: number; y: number; side?: string }
        fromCenter: { x: number; y: number }
        toCenter: { x: number; y: number }
      }>()

      const links = linkMetas
        .map(meta => {
          if (!meta) return null
          const {
            link,
            fromView,
            toView,
            fromCenter,
            toCenter,
            fromAnchor,
            toAnchor,
            fromAreaId,
            toAreaId,
            fromArea,
            toArea
          } = meta

          let points: number[] = []
          const isL1 = isL1View
          const bundle = linkBundleIndex.value.get(link.id)
          const areaBundle = laneIndex.get(link.id) || areaBundleIndex.value.get(link.id)
          const bundleOffset = bundle && bundle.total > 1
            ? (bundle.index - (bundle.total - 1) / 2) * ((renderTuning.value.bundle_gap ?? 0) * scale)
            : 0
          const interAreaBundleGap = (renderTuning.value.bundle_gap ?? 0) * scale
            * (areaBundle && areaBundle.total > 4 ? 1.9 : 1.6)
          const areaBundleOffset = areaBundle && areaBundle.total > 1
            ? (areaBundle.index - (areaBundle.total - 1) / 2) * interAreaBundleGap
            : 0
          const interBundleOffset = areaBundleOffset + bundleOffset * 0.5
          const bundleStub = (renderTuning.value.bundle_stub ?? 0) * scale
          const anchorOffset = ((renderTuning.value.area_anchor_offset ?? 0) + (renderTuning.value.area_clearance ?? 0)) * scale
          const exitStub = Math.max(renderTuning.value.bundle_stub ?? 0, renderTuning.value.area_clearance ?? 0) * scale

          const pushPoint = (arr: number[], x: number, y: number) => {
            const len = arr.length
            if (len >= 2 && arr[len - 2] === x && arr[len - 1] === y) return
            arr.push(x, y)
          }

          const isIntraArea = fromAreaId && toAreaId && fromAreaId === toAreaId
          const obstacles: Array<Rect> = []
          deviceRects.forEach(({ id, rect }) => {
            if (id === link.fromDeviceId || id === link.toDeviceId) return
            obstacles.push(rect)
          })
          if (!isIntraArea) {
            // Inter-area links né cả areas khác
            areaRects.forEach(({ id, rect }) => {
              if (id === fromAreaId || id === toAreaId) return
              obstacles.push(rect)
            })
          }
          if (isL1 && labelObstacles.length) {
            labelObstacles.forEach(entry => {
              if (entry.linkId === link.id) return
              obstacles.push(entry.rect)
            })
          }

          const lineBlocked = isL1 && obstacles.some(rect =>
            segmentIntersectsRect(
              { x: fromAnchor.x, y: fromAnchor.y },
              { x: toAnchor.x, y: toAnchor.y },
              rect,
              clearance
            )
          )
          const directAllowed = isL1 && !lineBlocked

          const fromSide = fromAnchor.side || computeSide(fromView, toCenter)
          const toSide = toAnchor.side || computeSide(toView, fromCenter)
          const fromExit = offsetFromAnchor({ ...fromAnchor, side: fromSide }, exitStub)
          const toExit = offsetFromAnchor({ ...toAnchor, side: toSide }, exitStub)

          let routed = false
          if (allowAStar && !directAllowed) {
            const preferAxis = Math.abs(toCenter.x - fromCenter.x) >= Math.abs(toCenter.y - fromCenter.y) ? 'x' : 'y'
            const route = routeOrthogonalPath({
              start: fromExit,
              end: toExit,
              obstacles,
              clearance,
              grid,
              occupancy,
              preferAxis
            })

            if (route && route.points.length) {
              const startAxis = fromSide === 'left' || fromSide === 'right' ? 'x' : 'y'
              const endAxis = toSide === 'left' || toSide === 'right' ? 'x' : 'y'
              const startConnector = connectOrthogonal(fromAnchor, route.points[0], obstacles, clearance, startAxis)
              const endConnector = connectOrthogonal(route.points[route.points.length - 1], toAnchor, obstacles, clearance, endAxis)

              const assembled: Array<{ x: number; y: number }> = []
              appendPoints(assembled, startConnector || [fromAnchor, route.points[0]])
              appendPoints(assembled, route.points)
              appendPoints(assembled, endConnector || [route.points[route.points.length - 1], toAnchor])

              const simplified = simplifyOrthogonalPath(assembled, minSegment)
              simplified.forEach(point => pushPoint(points, point.x, point.y))
              addOccupancy(occupancy, route.gridPath)
              routed = true
            }
          }

          if (!routed) {
            // Orthogonal routing for all links (fallback)
            if (fromAreaId && toAreaId && fromAreaId !== toAreaId && fromArea && toArea) {
              // Check for waypoint area between this area pair
              const wpKey = fromAreaId < toAreaId ? `${fromAreaId}|${toAreaId}` : `${toAreaId}|${fromAreaId}`
              const wp = waypointAreaMap.value.get(wpKey)

              if (wp) {
                // Route qua waypoint, tách lane trong phạm vi waypoint
                const axis = resolveLaneAxis(fromAreaId, toAreaId)
                const wpInset = Math.max(2, 4 * scale)
                const maxOffsetX = Math.max(0, wp.rect.width / 2 - wpInset)
                const maxOffsetY = Math.max(0, wp.rect.height / 2 - wpInset)
                const wpOffsetX = axis === 'x' ? clamp(interBundleOffset, -maxOffsetX, maxOffsetX) : 0
                const wpOffsetY = axis === 'y' ? clamp(interBundleOffset, -maxOffsetY, maxOffsetY) : 0
                const wpTarget = { x: wp.cx + wpOffsetX, y: wp.cy + wpOffsetY }

                const fromAreaAnchor = computeAreaAnchor(fromArea, fromExit, wpTarget, interBundleOffset, anchorOffset)
                const toAreaAnchor = computeAreaAnchor(toArea, toExit, wpTarget, interBundleOffset, anchorOffset)
                points = []
                pushPoint(points, fromAnchor.x, fromAnchor.y)
                pushPoint(points, fromExit.x, fromExit.y)
                pushPoint(points, fromAreaAnchor.x, fromAreaAnchor.y)
                pushPoint(points, wpTarget.x, fromAreaAnchor.y)
                pushPoint(points, wpTarget.x, wpTarget.y)
                pushPoint(points, wpTarget.x, toAreaAnchor.y)
                pushPoint(points, toAreaAnchor.x, toAreaAnchor.y)
                pushPoint(points, toExit.x, toExit.y)
                pushPoint(points, toAnchor.x, toAnchor.y)
            } else {
              // Fallback: corridor routing
              const localCorridor = computeLocalCorridor(
                fromArea,
                toArea,
                fromExit,
                toExit,
                fromAreaId,
                toAreaId,
                interBundleOffset,
                clearance
              )
              if (localCorridor) {
                const { axis, coord, fromAreaAnchor, toAreaAnchor } = localCorridor
                points = []
                pushPoint(points, fromAnchor.x, fromAnchor.y)
                pushPoint(points, fromExit.x, fromExit.y)
                pushPoint(points, fromAreaAnchor.x, fromAreaAnchor.y)
                if (axis === 'x') {
                  pushPoint(points, coord, fromAreaAnchor.y)
                  pushPoint(points, coord, toAreaAnchor.y)
                } else {
                  pushPoint(points, fromAreaAnchor.x, coord)
                  pushPoint(points, toAreaAnchor.x, coord)
                }
                pushPoint(points, toAreaAnchor.x, toAreaAnchor.y)
                pushPoint(points, toExit.x, toExit.y)
                pushPoint(points, toAnchor.x, toAnchor.y)
              } else {
                const fromAreaAnchor = computeAreaAnchor(fromArea, fromExit, toExit, interBundleOffset, anchorOffset)
                const toAreaAnchor = computeAreaAnchor(toArea, toExit, fromExit, interBundleOffset, anchorOffset)
                const bounds = areaBounds.value
                if (bounds) {
                  const corridorGap = (renderTuning.value.corridor_gap ?? 0) + (renderTuning.value.area_clearance ?? 0) + Math.abs(interBundleOffset)
                  const dx = toAnchor.x - fromAnchor.x
                  const dy = toAnchor.y - fromAnchor.y
                  if (Math.abs(dx) >= Math.abs(dy)) {
                    const topY = bounds.minY - corridorGap
                    const bottomY = bounds.maxY + corridorGap
                    const midY = (fromAnchor.y + toAnchor.y) / 2
                    const corridorBaseY = Math.abs(midY - topY) <= Math.abs(midY - bottomY) ? topY : bottomY
                    const corridorY = corridorBaseY + interBundleOffset
                    points = []
                    pushPoint(points, fromAnchor.x, fromAnchor.y)
                    pushPoint(points, fromExit.x, fromExit.y)
                    pushPoint(points, fromAreaAnchor.x, fromAreaAnchor.y)
                    pushPoint(points, fromAreaAnchor.x, corridorY)
                    pushPoint(points, toAreaAnchor.x, corridorY)
                    pushPoint(points, toAreaAnchor.x, toAreaAnchor.y)
                    pushPoint(points, toExit.x, toExit.y)
                    pushPoint(points, toAnchor.x, toAnchor.y)
                  } else {
                    const leftX = bounds.minX - corridorGap
                    const rightX = bounds.maxX + corridorGap
                    const midX = (fromAnchor.x + toAnchor.x) / 2
                    const corridorBaseX = Math.abs(midX - leftX) <= Math.abs(midX - rightX) ? leftX : rightX
                    const corridorX = corridorBaseX + interBundleOffset
                    points = []
                    pushPoint(points, fromAnchor.x, fromAnchor.y)
                    pushPoint(points, fromExit.x, fromExit.y)
                    pushPoint(points, fromAreaAnchor.x, fromAreaAnchor.y)
                    pushPoint(points, corridorX, fromAreaAnchor.y)
                    pushPoint(points, corridorX, toAreaAnchor.y)
                    pushPoint(points, toAreaAnchor.x, toAreaAnchor.y)
                    pushPoint(points, toExit.x, toExit.y)
                    pushPoint(points, toAnchor.x, toAnchor.y)
                  }
                } else {
                  const midX = (fromAnchor.x + toAnchor.x) / 2 + interBundleOffset
                  points = []
                  pushPoint(points, fromAnchor.x, fromAnchor.y)
                  pushPoint(points, fromExit.x, fromExit.y)
                  pushPoint(points, fromAreaAnchor.x, fromAreaAnchor.y)
                  pushPoint(points, midX, fromAreaAnchor.y)
                  pushPoint(points, midX, toAreaAnchor.y)
                  pushPoint(points, toAreaAnchor.x, toAreaAnchor.y)
                  pushPoint(points, toExit.x, toExit.y)
                  pushPoint(points, toAnchor.x, toAnchor.y)
                }
              }
            }
          } else if (isL1) {
              // L1 intra-area: straight segment between ports, bundle if needed
              // For bundled links, use device centers for consistent perpendicular direction
              const useCenters = bundleOffset !== 0
              const dx = useCenters ? (toCenter.x - fromCenter.x) : (toAnchor.x - fromAnchor.x)
              const dy = useCenters ? (toCenter.y - fromCenter.y) : (toAnchor.y - fromAnchor.y)
              const dir = normalizeVector(dx, dy)
              const perp = normalizeVector(-dir.y, dir.x)
              if (bundleOffset !== 0 && (dir.x !== 0 || dir.y !== 0)) {
                const fromStub = { x: fromAnchor.x + dir.x * bundleStub, y: fromAnchor.y + dir.y * bundleStub }
                const toStub = { x: toAnchor.x - dir.x * bundleStub, y: toAnchor.y - dir.y * bundleStub }
                const fromShift = { x: fromStub.x + perp.x * bundleOffset, y: fromStub.y + perp.y * bundleOffset }
                const toShift = { x: toStub.x + perp.x * bundleOffset, y: toStub.y + perp.y * bundleOffset }
                points = [
                  fromAnchor.x, fromAnchor.y,
                  fromShift.x, fromShift.y,
                  toShift.x, toShift.y,
                  toAnchor.x, toAnchor.y
                ]
              } else {
                points = [fromAnchor.x, fromAnchor.y, toAnchor.x, toAnchor.y]
              }

              if (bundleOffset === 0) {
                const blockedRects: Rect[] = []
                areaViewMap.value.forEach((rect, areaId) => {
                  if (areaId === fromAreaId || areaId === toAreaId) return
                  if (segmentIntersectsRect({ x: fromAnchor.x, y: fromAnchor.y }, { x: toAnchor.x, y: toAnchor.y }, rect, renderTuning.value.area_clearance ?? 0)) {
                    blockedRects.push(rect)
                  }
                })
                deviceRects.forEach(({ id, rect }) => {
                  if (id === link.fromDeviceId || id === link.toDeviceId) return
                  if (segmentIntersectsRect({ x: fromAnchor.x, y: fromAnchor.y }, { x: toAnchor.x, y: toAnchor.y }, rect, renderTuning.value.area_clearance ?? 0)) {
                    blockedRects.push(rect)
                  }
                })
                if (blockedRects.length) {
                  const midA = { x: fromAnchor.x, y: toAnchor.y }
                  const midB = { x: toAnchor.x, y: fromAnchor.y }
                  const score = (a: { x: number; y: number }) => {
                    let hits = 0
                    blockedRects.forEach(rect => {
                      if (segmentIntersectsRect(fromAnchor, a, rect, renderTuning.value.area_clearance ?? 0)) hits += 1
                      if (segmentIntersectsRect(a, toAnchor, rect, renderTuning.value.area_clearance ?? 0)) hits += 1
                    })
                    const length = Math.hypot(a.x - fromAnchor.x, a.y - fromAnchor.y) + Math.hypot(toAnchor.x - a.x, toAnchor.y - a.y)
                    return hits * 10000 + length
                  }
                  const scoreA = score(midA)
                  const scoreB = score(midB)
                  const mid = scoreA <= scoreB ? midA : midB
                  points = [fromAnchor.x, fromAnchor.y, mid.x, mid.y, toAnchor.x, toAnchor.y]
                }
              }
            } else {
              // Intra-area links: orthogonal (Manhattan) routing
              const dx = toAnchor.x - fromAnchor.x
              const dy = toAnchor.y - fromAnchor.y

              if (Math.abs(dx) < 5 && Math.abs(dy) < 5) {
                // Very close: direct line
                points = [fromAnchor.x, fromAnchor.y, toAnchor.x, toAnchor.y]
              } else if (Math.abs(dx) >= Math.abs(dy)) {
                // Horizontal dominant: go horizontal first
                const midX = fromAnchor.x + dx / 2
                points = [
                  fromAnchor.x, fromAnchor.y,
                  midX, fromAnchor.y,
                  midX, toAnchor.y,
                  toAnchor.x, toAnchor.y
                ]
              } else {
                // Vertical dominant: go vertical first
                const midY = fromAnchor.y + dy / 2
                points = [
                  fromAnchor.x, fromAnchor.y,
                  fromAnchor.x, midY,
                  toAnchor.x, midY,
                  toAnchor.x, toAnchor.y
                ]
              }
            }
          }

          return {
            id: link.id,
            fromAnchor,
            toAnchor,
            fromCenter,
            toCenter,
            points,
            config: {
              points,
              stroke: '#2b2a28',
              strokeWidth: 1.5,
              lineCap: 'round',
              lineJoin: 'round',
              dash: link.style === 'dashed' ? [8, 6] : link.style === 'dotted' ? [2, 4] : [],
              opacity: 0.8
            }
          }
        })
        .filter(Boolean) as RenderLink[]

      links.forEach(link => {
        cache.set(link.id, {
          points: [...link.points],
          fromAnchor: { ...link.fromAnchor },
          toAnchor: { ...link.toAnchor },
          fromCenter: { ...link.fromCenter },
          toCenter: { ...link.toCenter }
        })
      })

      return { links, cache }
    }

    const pass1 = buildLinkMetaData()
    const pass1Result = routeLinks(pass1.linkMetas, pass1.laneIndex, pass1.labelObstacles)
    const anchorOverrides = buildAnchorOverrides(pass1.linkMetas, pass1Result.cache)

    let finalResult = pass1Result
    if (anchorOverrides.size > 0) {
      const pass2 = buildLinkMetaData(anchorOverrides)
      finalResult = routeLinks(pass2.linkMetas, pass2.laneIndex, pass2.labelObstacles)
    }

    return { links: finalResult.links, cache: finalResult.cache }
  }

  const visibleLinks = computed(() => {
    if (isPanning.value) return buildVisibleLinks(true).links
    return visibleLinkCache.value
  })

  const linkCrossings = computed<Map<string, Crossing[]>>(() => {
    if (isPanning.value) return new Map()
    const links = visibleLinks.value
    if (!links || links.length < 2) return new Map()
    return computeCrossings(links.map(l => ({ id: l.id, points: l.points })))
  })

  const visibleLinkShapes = computed(() => {
    const crossMap = linkCrossings.value
    const R = ARC_RADIUS
    return visibleLinks.value.map(link => {
      const crossings = crossMap.get(link.id) || []
      const cfg = link.config
      return {
        id: link.id,
        config: {
          sceneFunc: (ctx: any, shape: any) => {
            ctx.beginPath()
            drawPolylineWithJumps(ctx, link.points, crossings, R)
            ctx.fillStrokeShape(shape)
          },
          stroke: cfg.stroke,
          strokeWidth: cfg.strokeWidth,
          lineCap: cfg.lineCap,
          lineJoin: cfg.lineJoin,
          dash: cfg.dash,
          opacity: cfg.opacity,
          listening: false,
        },
      }
    })
  })

  const linkPortLabels = computed(() => {
    if (isPanning.value) return []
    if ((props.viewMode || 'L1') !== 'L1') return []
    const linkMap = new Map(visibleLinks.value.map(link => [link.id, link]))
    const labelScale = clamp(layoutViewport.value.scale, LABEL_SCALE_MIN, LABEL_SCALE_MAX)
    const labelHeight = PORT_LABEL_HEIGHT * labelScale
    const labelPadding = PORT_LABEL_PADDING * labelScale
    const labelOffset = (renderTuning.value.port_label_offset ?? 0) * labelScale
    const fontSize = 10 * labelScale
    const textPadX = 4 * labelScale
    const textPadY = 2 * labelScale
    const minLabelWidth = 24 * labelScale
    const charWidth = 6 * labelScale

    const rawLabels: Array<{
      id: string
      deviceId: string
      areaId: string | null
      side: string
      width: number
      height: number
      text: string
      angle: number
      center: { x: number; y: number }
      rect: Rect
      fontSize: number
      textPadX: number
      textPadY: number
    }> = []

    const computeAngle = (from: { x: number; y: number }, to: { x: number; y: number }) => {
      const angle = Math.atan2(to.y - from.y, to.x - from.x) * (180 / Math.PI)
      if (angle > 90) return angle - 180
      if (angle < -90) return angle + 180
      return angle
    }

    props.links.forEach(link => {
      const entry = linkMap.get(link.id)
      if (!entry) return

      const fromText = link.fromPort?.trim()
      const toText = link.toPort?.trim()

      const placeLabel = (
        id: string,
        text: string,
        anchor: { x: number; y: number; side?: string },
        center: { x: number; y: number },
        neighbor: { x: number; y: number },
        deviceId: string,
        deviceRect: Rect,
        segmentCount: number
      ) => {
        if (!text) return
        const width = Math.max(text.length * charWidth + labelPadding, minLabelWidth)

        const dx = neighbor.x - anchor.x
        const dy = neighbor.y - anchor.y
        const len = Math.hypot(dx, dy)

        let cx: number
        let cy: number

        if (len < 1) {
          const pos = computePortLabelPlacement(anchor, center, width, labelHeight, labelOffset)
          cx = pos.x + width / 2
          cy = pos.y + labelHeight / 2
        } else {
          // Place label near the device anchor, ON the connection line
          // The line passes through the center of the label (via group offsetX/offsetY)
          // Use a small offset from anchor so label doesn't overlap the device edge
          const offset = (width / 2 + 4) / len
          cx = anchor.x + dx * offset
          cy = anchor.y + dy * offset
        }

        rawLabels.push({
          id,
          deviceId,
          areaId: deviceAreaMap.value.get(deviceId) || null,
          side: anchor.side || computeSide(deviceRect, neighbor),
          width,
          height: labelHeight,
          text,
          angle: computeAngle(anchor, neighbor),
          center: { x: cx, y: cy },
          rect: deviceRect,
          fontSize,
          textPadX,
          textPadY
        })
      }

      const fromNeighbor = entry.points.length >= 4
        ? { x: entry.points[2], y: entry.points[3] }
        : entry.toAnchor
      const toNeighbor = entry.points.length >= 4
        ? { x: entry.points[entry.points.length - 4], y: entry.points[entry.points.length - 3] }
        : entry.fromAnchor

      const fromRect = deviceViewMap.value.get(link.fromDeviceId)
      const toRect = deviceViewMap.value.get(link.toDeviceId)
      const segmentCount = entry.points.length / 2
      if (fromRect && fromText) {
        placeLabel(
          `${link.id}-from`,
          fromText,
          entry.fromAnchor,
          entry.fromCenter,
          fromNeighbor,
          link.fromDeviceId,
          fromRect,
          segmentCount
        )
      }
      if (toRect && toText) {
        placeLabel(
          `${link.id}-to`,
          toText,
          entry.toAnchor,
          entry.toCenter,
          toNeighbor,
          link.toDeviceId,
          toRect,
          segmentCount
        )
      }
    })

    // Single-pass collision avoidance per device-side (reduced gaps, capped displacement)
    const bySide = new Map<string, typeof rawLabels>()
    rawLabels.forEach(label => {
      const key = `${label.deviceId}-${label.side}`
      const list = bySide.get(key) || []
      list.push(label)
      bySide.set(key, list)
    })

    const maxDisplacement = 60 * labelScale // Cap max displacement from original position

    bySide.forEach(list => {
      if (list.length < 2) return
      const side = list[0].side
      // Save original positions to cap displacement
      const originals = list.map(l => ({ x: l.center.x, y: l.center.y }))

      if (side === 'left' || side === 'right') {
        list.sort((a, b) => a.center.y - b.center.y)
        let cursor = list[0].center.y
        list.forEach((label, idx) => {
          if (idx === 0) return
          const minGap = (list[idx - 1].height + label.height) / 2 + 2 * labelScale
          if (label.center.y < cursor + minGap) {
            label.center.y = cursor + minGap
          }
          cursor = label.center.y
        })
      } else {
        list.sort((a, b) => a.center.x - b.center.x)
        let cursor = list[0].center.x
        list.forEach((label, idx) => {
          if (idx === 0) return
          const minGap = (list[idx - 1].width + label.width) / 2 + 2 * labelScale
          if (label.center.x < cursor + minGap) {
            label.center.x = cursor + minGap
          }
          cursor = label.center.x
        })
      }

      // Cap displacement
      list.forEach((label, idx) => {
        const orig = originals[idx]
        const dispX = label.center.x - orig.x
        const dispY = label.center.y - orig.y
        const dist = Math.hypot(dispX, dispY)
        if (dist > maxDisplacement) {
          const scale = maxDisplacement / dist
          label.center.x = orig.x + dispX * scale
          label.center.y = orig.y + dispY * scale
        }
      })
    })

    return rawLabels.map(label => ({
      id: label.id,
      group: {
        x: label.center.x,
        y: label.center.y,
        rotation: label.angle,
        offsetX: label.width / 2,
        offsetY: label.height / 2
      },
      bg: {
        x: 0,
        y: 0,
        width: label.width,
        height: label.height,
        fill: '#ffffff',
        cornerRadius: 4 * labelScale,
        opacity: 0.92,
        shadowColor: 'rgba(0, 0, 0, 0.2)',
        shadowBlur: 4 * labelScale,
        shadowOffset: { x: 0, y: 2 },
        shadowOpacity: 0.2
      },
      text: {
        x: label.textPadX,
        y: label.textPadY,
        text: label.text,
        fontSize: label.fontSize,
        fill: '#2b2a28'
      }
    }))
  })

  const refreshLinkCache = () => {
    if (isPanning.value) return
    const result = buildVisibleLinks(false)
    visibleLinkCache.value = result.links
    if (result.cache) {
      linkRouteCache.value = result.cache
      linkRouteCacheViewport.value = { ...layoutViewport.value }
    }
  }

  let refreshLinkRaf = 0
  const scheduleRefreshLinkCache = () => {
    if (isPanning.value) return
    if (refreshLinkRaf) return
    refreshLinkRaf = requestAnimationFrame(() => {
      refreshLinkRaf = 0
      if (isPanning.value) return
      refreshLinkCache()
    })
  }

  watch(
    [
      () => props.links,
      () => props.areas,
      () => props.devices,
      () => props.viewMode,
      () => props.l2Assignments,
      () => layoutViewport.value.scale,
      () => layoutViewport.value.offsetX,
      () => layoutViewport.value.offsetY,
      renderTuning
    ],
    () => {
      scheduleRefreshLinkCache()
    },
    { immediate: true }
  )

  onBeforeUnmount(() => {
    if (refreshLinkRaf) {
      cancelAnimationFrame(refreshLinkRaf)
      refreshLinkRaf = 0
    }
  })

  return {
    visibleLinks,
    visibleLinkShapes,
    linkPortLabels
  }
}
