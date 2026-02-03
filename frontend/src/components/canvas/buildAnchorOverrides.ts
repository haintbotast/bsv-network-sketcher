import type { Rect, RenderTuning, AnchorOverrideMap, LinkMeta, AreaRectEntry, DeviceRectEntry, PortAnchorOverrideMap } from './linkRoutingTypes'
import { clamp, computeSide, computeSideFromVector, segmentIntersectsRect } from './linkRoutingUtils'

export type BuildAnchorOverridesParams = {
  isL1View: boolean
  scale: number
  clearance: number
  areaRects: AreaRectEntry[]
  deviceRects: DeviceRectEntry[]
  renderTuning: RenderTuning
  deviceViewMap: Map<string, Rect>
  devicePortList: Map<string, string[]>
  devicePortSideMap: Map<string, Map<string, string>>
  devicePortOrder: Map<string, Map<string, number>>
  devicePortNeighbors: Map<string, Map<string, { xSum: number; ySum: number; count: number }>>
  linkBundleIndex: Map<string, { index: number; total: number }>
  userAnchorOverrides?: PortAnchorOverrideMap
}

export function buildAnchorOverrides(
  linkMetas: Array<LinkMeta | null>,
  cache: Map<string, { points: number[]; fromAnchor: { x: number; y: number; side?: string }; toAnchor: { x: number; y: number; side?: string } }>,
  ctx: BuildAnchorOverridesParams
): AnchorOverrideMap {
  const {
    isL1View, scale, clearance, areaRects, deviceRects,
    renderTuning, deviceViewMap,
    devicePortList, devicePortSideMap, devicePortOrder, devicePortNeighbors,
    linkBundleIndex,
    userAnchorOverrides,
  } = ctx

  const getUserOverride = (deviceId: string, port: string | undefined) => {
    if (!port) return null
    if (!userAnchorOverrides || userAnchorOverrides.size === 0) return null
    return userAnchorOverrides.get(deviceId)?.get(port) ?? null
  }

  const hasUserOverride = (deviceId: string, port: string | undefined) => {
    return !!getUserOverride(deviceId, port)
  }

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
    const fromVector = { x: fromNext.x - entry.fromAnchor.x, y: fromNext.y - entry.fromAnchor.y }
    const toVector = { x: toPrev.x - entry.toAnchor.x, y: toPrev.y - entry.toAnchor.y }
    const fromSide = (Math.hypot(fromVector.x, fromVector.y) >= 1
      ? computeSideFromVector(fromVector.x, fromVector.y)
      : (entry.fromAnchor.side || computeSide(meta.fromView, meta.toCenter))) as 'left' | 'right' | 'top' | 'bottom'
    const toSide = (Math.hypot(toVector.x, toVector.y) >= 1
      ? computeSideFromVector(toVector.x, toVector.y)
      : (entry.toAnchor.side || computeSide(meta.toView, meta.fromCenter))) as 'left' | 'right' | 'top' | 'bottom'
    const fromOverride = getUserOverride(meta.link.fromDeviceId, meta.link.fromPort)
    const toOverride = getUserOverride(meta.link.toDeviceId, meta.link.toPort)

    if (meta.link.fromPort && !hasUserOverride(meta.link.fromDeviceId, meta.link.fromPort)) {
      const coord = fromSide === 'left' || fromSide === 'right' ? fromNext.y : fromNext.x
      record(meta.link.fromDeviceId, meta.link.fromPort, fromSide, coord)
      registerNeighborDevice(meta.link.fromDeviceId, meta.link.fromPort, meta.link.toDeviceId)
    }
    if (meta.link.toPort && !hasUserOverride(meta.link.toDeviceId, meta.link.toPort)) {
      const coord = toSide === 'left' || toSide === 'right' ? toPrev.y : toPrev.x
      record(meta.link.toDeviceId, meta.link.toPort, toSide, coord)
      registerNeighborDevice(meta.link.toDeviceId, meta.link.toPort, meta.link.fromDeviceId)
    }

    if (
      isL1View
      && meta.link.fromPort
      && meta.link.toPort
    ) {
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
        const expectedSides = axis === 'y' ? ['left', 'right'] : ['top', 'bottom']
        if (fromOverride && !expectedSides.includes(fromOverride.side)) axis = null
        if (toOverride && !expectedSides.includes(toOverride.side)) axis = null
      }

      if (axis) {
        const portEdgeInset = renderTuning.port_edge_inset ?? 0
        const bundle = linkBundleIndex.get(meta.link.id)
        const bundleGap = Math.max(6, (renderTuning.bundle_gap ?? 0) * scale * 0.6)
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
          const fromSideAligned = axis === 'y'
            ? (toCenter.x >= fromCenter.x ? 'right' : 'left')
            : (toCenter.y >= fromCenter.y ? 'bottom' : 'top')
          const toSideAligned = axis === 'y'
            ? (fromCenter.x >= toCenter.x ? 'right' : 'left')
            : (fromCenter.y >= toCenter.y ? 'bottom' : 'top')
          if (fromOverride && fromOverride.side !== fromSideAligned) return
          if (toOverride && toOverride.side !== toSideAligned) return
          const fromSideFinal = fromOverride?.side ?? fromSideAligned
          const toSideFinal = toOverride?.side ?? toSideAligned

          const fromAnchor = axis === 'y'
            ? { x: fromSideFinal === 'left' ? fromView.x : fromView.x + fromView.width, y: coord }
            : { x: coord, y: fromSideFinal === 'top' ? fromView.y : fromView.y + fromView.height }
          const toAnchor = axis === 'y'
            ? { x: toSideFinal === 'left' ? toView.x : toView.x + toView.width, y: coord }
            : { x: coord, y: toSideFinal === 'top' ? toView.y : toView.y + toView.height }

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
            if (!fromOverride) {
              registerForcedSideIfUnset(meta.link.fromDeviceId, meta.link.fromPort, fromSideAligned as 'left' | 'right' | 'top' | 'bottom')
            }
            if (!toOverride) {
              registerForcedSideIfUnset(meta.link.toDeviceId, meta.link.toPort, toSideAligned as 'left' | 'right' | 'top' | 'bottom')
            }
          }
        }
      }
    }

    if (
      meta.link.fromPort
      && meta.link.toPort
      && !hasUserOverride(meta.link.fromDeviceId, meta.link.fromPort)
      && !hasUserOverride(meta.link.toDeviceId, meta.link.toPort)
    ) {
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
      if (hasUserOverride(entry.fromDeviceId, entry.fromPort) || hasUserOverride(entry.toDeviceId, entry.toPort)) return
      const fromOrder = devicePortOrder.get(entry.fromDeviceId)?.get(entry.fromPort) ?? 0
      const toOrder = devicePortOrder.get(entry.toDeviceId)?.get(entry.toPort) ?? 0
      registerPairRank(entry.fromDeviceId, entry.fromPort, toOrder, list.length, entry.toDeviceId)
      registerPairRank(entry.toDeviceId, entry.toPort, fromOrder, list.length, entry.fromDeviceId)
    })
  })

  pairGroups.forEach(list => {
    if (list.length < 2) return
    const first = list[0]
    const aRect = deviceViewMap.get(first.fromDeviceId)
    const bRect = deviceViewMap.get(first.toDeviceId)
    if (!aRect || !bRect) return
    const aCenter = { x: aRect.x + aRect.width / 2, y: aRect.y + aRect.height / 2 }
    const bCenter = { x: bRect.x + bRect.width / 2, y: bRect.y + bRect.height / 2 }
    const axis = Math.abs(bCenter.x - aCenter.x) >= Math.abs(bCenter.y - aCenter.y) ? 'x' : 'y'

    list.forEach(entry => {
      if (!entry.fromPort || !entry.toPort) return
      if (hasUserOverride(entry.fromDeviceId, entry.fromPort) || hasUserOverride(entry.toDeviceId, entry.toPort)) return
      const fromRect = deviceViewMap.get(entry.fromDeviceId)
      const toRect = deviceViewMap.get(entry.toDeviceId)
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
  const portEdgeInset = renderTuning.port_edge_inset ?? 0
  let overrideCount = 0

  devicePortList.forEach((ports, deviceId) => {
    const rect = deviceViewMap.get(deviceId)
    if (!rect || ports.length === 0) return
    const deviceStats = portStats.get(deviceId)
    if (!deviceStats) return
    const sideMap = devicePortSideMap.get(deviceId) || new Map<string, string>()
    const orderMap = devicePortOrder.get(deviceId) || new Map<string, number>()
    const neighborMap = devicePortNeighbors.get(deviceId) || new Map<string, { xSum: number; ySum: number; count: number }>()
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
      const userOverride = getUserOverride(deviceId, port)
      const aligned = alignedCoordMap.get(port)
      if (userOverride && !aligned) return
      const stats = deviceStats.get(port)
      let side = (sideMap.get(port) || 'right') as 'left' | 'right' | 'top' | 'bottom'
      const forcedSide = forcedSideMap.get(port)
      if (userOverride) {
        side = userOverride.side
      } else if (forcedSide) {
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

      const minSpacing = Math.max(baseSpacing * 0.6, 4)
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
