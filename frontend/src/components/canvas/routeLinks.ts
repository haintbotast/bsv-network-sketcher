import type { Rect, RenderLink, RenderTuning, LinkMeta, AreaRectEntry, DeviceRectEntry } from './linkRoutingTypes'
import {
  clamp,
  computeSide,
  offsetFromAnchor,
  segmentIntersectsRect,
  computeAreaAnchor,
} from './linkRoutingUtils'
import { resolveLinkPurposeColor } from '../../composables/canvasConstants'
import {
  addOccupancy,
  connectOrthogonal,
  polylineToGridPath,
  routeAnyAnglePath,
  routeOrthogonalPath,
  smoothAnyAnglePath,
  type GridSpec,
} from '../../utils/link_routing'

export type RouteLinksParams = {
  isL1View: boolean
  scale: number
  clearance: number
  minSegment: number
  grid: GridSpec | null
  allowAStar: boolean
  areaRects: AreaRectEntry[]
  deviceRects: DeviceRectEntry[]
  renderTuning: RenderTuning
  areaViewMap: Map<string, Rect>
  deviceAreaMap: Map<string, string>
  areaBounds: { minX: number; minY: number; maxX: number; maxY: number } | null
  linkBundleIndex: Map<string, { index: number; total: number }>
  areaBundleIndex: Map<string, { index: number; total: number }>
  waypointAreaMap: Map<string, { id: string; cx: number; cy: number; rect: Rect }>
  areaCenters: Map<string, { x: number; y: number }>
  debugRouteMode?: boolean
}

const LABEL_STUB_PADDING = 4
const DEBUG_STROKE_L2 = '#c0392b'
const DEBUG_STROKE_L1_DIAGONAL = '#d35400'
const LABEL_SCALE_MIN = 0.6
const LABEL_SCALE_MAX = 1.15

type PeerPurposeKind = 'stack' | 'ha' | 'hsrp'

const PEER_PURPOSE_VISUAL: Record<PeerPurposeKind, { stroke: string; dash: number[]; strokeWidth: number; opacity: number }> = {
  stack: { stroke: '#2d8cf0', dash: [], strokeWidth: 2, opacity: 0.98 },
  ha: { stroke: '#16a085', dash: [8, 5], strokeWidth: 1.9, opacity: 0.98 },
  hsrp: { stroke: '#9b59b6', dash: [3, 4], strokeWidth: 1.8, opacity: 0.96 },
}

function resolvePeerPurposeKind(
  purpose: string,
  fromPort?: string | null,
  toPort?: string | null
): PeerPurposeKind | null {
  const key = (purpose || '').trim().toUpperCase()
  const from = (fromPort || '').trim().toUpperCase()
  const to = (toPort || '').trim().toUpperCase()
  if (from.includes('STACK') || to.includes('STACK')) return 'stack'
  if (!key) return null
  if (key.includes('STACK')) return 'stack'
  if (key.includes('HSRP')) return 'hsrp'
  if (key === 'HA' || key.includes('HIGH-AVAILABILITY') || key.includes('HIGH_AVAILABILITY')) return 'ha'
  return null
}

function computeLocalCorridor(
  fromArea: Rect,
  toArea: Rect,
  fromExit: { x: number; y: number },
  toExit: { x: number; y: number },
  fromAreaId: string | null,
  toAreaId: string | null,
  interBundleOffset: number,
  clearanceValue: number,
  areaRects: AreaRectEntry[],
  deviceRects: DeviceRectEntry[]
) {
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
    }) || deviceRects.some(({ rect }) => segmentIntersectsRect(segStart, segEnd, rect, clearanceValue))
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
    }) || deviceRects.some(({ rect }) => segmentIntersectsRect(segStart, segEnd, rect, clearanceValue))
    if (blocked) return null
    return { axis: 'y' as const, coord: corridorY, fromAreaAnchor, toAreaAnchor }
  }

  return null
}

type PadSide = 'left' | 'right'

interface AreaPadInfo {
  leftX: number
  rightX: number
  leftMinX: number
  leftMaxX: number
  rightMinX: number
  rightMaxX: number
  inset: number
}

interface PadCorridorChannel {
  side: PadSide
  coord: number
}

interface PadCorridorPlan {
  laneSpacing: number
  channels: PadCorridorChannel[]
  linkCount: number
}

function computeAreaPadInfo(
  areaRects: AreaRectEntry[],
  deviceRects: DeviceRectEntry[],
  deviceAreaMap: Map<string, string>,
  renderTuning: RenderTuning,
  scale: number,
): Map<string, AreaPadInfo> {
  const result = new Map<string, AreaPadInfo>()
  const minInset = Math.max(6, Math.round((renderTuning.area_clearance ?? 0) * 0.4 * scale))
  const defaultPadRatio = 0.22

  const deviceBounds = new Map<string, { minX: number; minY: number; maxX: number; maxY: number; count: number }>()
  deviceRects.forEach(({ id, rect }) => {
    const areaId = deviceAreaMap.get(id)
    if (!areaId) return
    const entry = deviceBounds.get(areaId) || {
      minX: rect.x,
      minY: rect.y,
      maxX: rect.x + rect.width,
      maxY: rect.y + rect.height,
      count: 0
    }
    entry.minX = Math.min(entry.minX, rect.x)
    entry.minY = Math.min(entry.minY, rect.y)
    entry.maxX = Math.max(entry.maxX, rect.x + rect.width)
    entry.maxY = Math.max(entry.maxY, rect.y + rect.height)
    entry.count += 1
    deviceBounds.set(areaId, entry)
  })

  const resolveInset = (padSize: number) => {
    if (!Number.isFinite(padSize) || padSize <= 0) return minInset
    const maxInset = Math.max(minInset, padSize - minInset)
    return clamp(padSize * 0.5, minInset, maxInset)
  }

  areaRects.forEach(({ id, rect }) => {
    const bounds = deviceBounds.get(id)
    const fallbackPadX = rect.width * defaultPadRatio
    const fallbackPadY = rect.height * defaultPadRatio

    const padLeft = bounds ? Math.max(0, bounds.minX - rect.x) : fallbackPadX
    const padRight = bounds ? Math.max(0, rect.x + rect.width - bounds.maxX) : fallbackPadX
    const padTop = bounds ? Math.max(0, bounds.minY - rect.y) : fallbackPadY
    const padBottom = bounds ? Math.max(0, rect.y + rect.height - bounds.maxY) : fallbackPadY

    const leftInset = resolveInset(padLeft)
    const rightInset = resolveInset(padRight)

    const leftMinX = rect.x + minInset
    const leftMaxX = rect.x + Math.max(minInset, padLeft - minInset)
    const rightMinX = rect.x + rect.width - Math.max(minInset, padRight - minInset)
    const rightMaxX = rect.x + rect.width - minInset

    const safeLeftMax = leftMaxX < leftMinX ? leftMinX : leftMaxX
    const safeRightMin = rightMinX > rightMaxX ? rightMaxX : rightMinX

    const leftX = clamp(rect.x + leftInset, leftMinX, safeLeftMax)
    const rightX = clamp(rect.x + rect.width - rightInset, safeRightMin, rightMaxX)

    const inset = Math.max(minInset, Math.min(padTop, padBottom, rect.height * 0.25))

    result.set(id, {
      leftX,
      rightX,
      leftMinX,
      leftMaxX: safeLeftMax,
      rightMinX: safeRightMin,
      rightMaxX,
      inset
    })
  })

  return result
}

function resolvePadCorridorCoord(
  side: PadSide,
  baseCoord: number,
  padA: AreaPadInfo,
  padB: AreaPadInfo,
) {
  const minCoord = side === 'left'
    ? Math.max(padA.leftMinX, padB.leftMinX)
    : Math.max(padA.rightMinX, padB.rightMinX)
  const maxCoord = side === 'left'
    ? Math.min(padA.leftMaxX, padB.leftMaxX)
    : Math.min(padA.rightMaxX, padB.rightMaxX)
  if (minCoord <= maxCoord) {
    return clamp(baseCoord, minCoord, maxCoord)
  }
  return baseCoord
}

function computePadCorridors(
  areaViewMap: Map<string, Rect>,
  areaCenters: Map<string, { x: number; y: number }>,
  linkMetas: Array<LinkMeta | null>,
  areaPadMap: Map<string, AreaPadInfo>,
  areaRects: AreaRectEntry[],
  deviceRects: DeviceRectEntry[],
  renderTuning: RenderTuning,
  scale: number,
): Map<string, PadCorridorPlan> {
  const result = new Map<string, PadCorridorPlan>()
  const laneSpacing = Math.max(8, (renderTuning.bundle_gap ?? 0) * scale * 2.8)
  const laneSnapStep = Math.max(8, laneSpacing * 0.5)
  const pairKey = (a: string, b: string) => a < b ? `${a}|${b}` : `${b}|${a}`
  const linksPerChannelRaw = Number(renderTuning.inter_area_links_per_channel ?? 4)
  const maxChannelsRaw = Number(renderTuning.inter_area_max_channels ?? 4)
  const linksPerChannel = clamp(Number.isFinite(linksPerChannelRaw) ? Math.round(linksPerChannelRaw) : 4, 1, 24)
  const maxChannels = clamp(Number.isFinite(maxChannelsRaw) ? Math.round(maxChannelsRaw) : 4, 1, 8)

  const pairCounts = new Map<string, number>()
  for (const meta of linkMetas) {
    if (!meta) continue
    if (!meta.fromAreaId || !meta.toAreaId || meta.fromAreaId === meta.toAreaId) continue
    const key = pairKey(meta.fromAreaId, meta.toAreaId)
    pairCounts.set(key, (pairCounts.get(key) || 0) + 1)
  }

  const alternatingRank = (index: number) => {
    if (index <= 0) return 0
    const step = Math.ceil(index / 2)
    return index % 2 === 1 ? step : -step
  }

  for (const [key, linkCount] of pairCounts.entries()) {
    const [idA, idB] = key.split('|')
    const areaA = areaViewMap.get(idA)
    const areaB = areaViewMap.get(idB)
    const padA = areaPadMap.get(idA)
    const padB = areaPadMap.get(idB)
    const cA = areaCenters.get(idA)
    const cB = areaCenters.get(idB)
    if (!areaA || !areaB || !padA || !padB || !cA || !cB) continue

    const baseLeft = (padA.leftX + padB.leftX) / 2
    const baseRight = (padA.rightX + padB.rightX) / 2
    const leftCoord = resolvePadCorridorCoord('left', baseLeft, padA, padB)
    const rightCoord = resolvePadCorridorCoord('right', baseRight, padA, padB)

    const scoreSide = (side: PadSide, corridorX: number) => {
      const fromX = side === 'left' ? padA.leftX : padA.rightX
      const toX = side === 'left' ? padB.leftX : padB.rightX
      const fromY = clamp(cA.y, areaA.y + padA.inset, areaA.y + areaA.height - padA.inset)
      const toY = clamp(cB.y, areaB.y + padB.inset, areaB.y + areaB.height - padB.inset)
      const points = [
        { x: fromX, y: fromY },
        { x: corridorX, y: fromY },
        { x: corridorX, y: toY },
        { x: toX, y: toY }
      ]
      let hits = 0
      let length = 0
      for (let i = 1; i < points.length; i += 1) {
        const a = points[i - 1]
        const b = points[i]
        length += Math.abs(b.x - a.x) + Math.abs(b.y - a.y)
        areaRects.forEach(({ id, rect }) => {
          if (id === idA || id === idB) return
          if (segmentIntersectsRect(a, b, rect, 0)) hits += 1
        })
        deviceRects.forEach(({ rect }) => {
          if (segmentIntersectsRect(a, b, rect, 0)) hits += 1
        })
      }
      return { hits, length }
    }

    const leftScore = scoreSide('left', leftCoord)
    const rightScore = scoreSide('right', rightCoord)
    const pickLeft = leftScore.hits === rightScore.hits
      ? leftScore.length <= rightScore.length
      : leftScore.hits < rightScore.hits
    const primary = pickLeft
      ? { side: 'left' as PadSide, coord: leftCoord }
      : { side: 'right' as PadSide, coord: rightCoord }
    const secondary = pickLeft
      ? { side: 'right' as PadSide, coord: rightCoord }
      : { side: 'left' as PadSide, coord: leftCoord }

    const channelCount = Math.max(1, Math.min(maxChannels, Math.ceil(linkCount / linksPerChannel)))
    const channels: PadCorridorChannel[] = []
    const channelStep = Math.max(8, laneSpacing * 1.15)

    for (let channelIndex = 0; channelIndex < channelCount; channelIndex += 1) {
      const sidePlan = channelIndex % 2 === 0 ? primary : secondary
      const bandIndex = Math.floor(channelIndex / 2)
      const offsetRank = alternatingRank(bandIndex)
      const rawCoord = sidePlan.coord + offsetRank * channelStep
      const corridorCoord = resolvePadCorridorCoord(
        sidePlan.side,
        rawCoord,
        padA,
        padB,
      )
      const snappedCoord = Math.round(corridorCoord / laneSnapStep) * laneSnapStep
      channels.push({
        side: sidePlan.side,
        coord: snappedCoord,
      })
    }

    result.set(key, { laneSpacing, channels, linkCount })
  }

  return result
}

export function routeLinks(
  linkMetas: Array<LinkMeta | null>,
  laneIndex: Map<string, { index: number; total: number }>,
  labelObstacles: Array<{ linkId: string; rect: Rect }>,
  ctx: RouteLinksParams
) {
  const {
    isL1View, scale, clearance, minSegment,
    grid, allowAStar,
    areaRects, deviceRects,
    renderTuning, areaViewMap, deviceAreaMap, areaBounds,
    linkBundleIndex, areaBundleIndex, waypointAreaMap,
    areaCenters,
    debugRouteMode,
  } = ctx
  const debugOn = !!debugRouteMode
  const getPairKey = (fromArea: string, toArea: string) =>
    fromArea < toArea ? `${fromArea}|${toArea}` : `${toArea}|${fromArea}`

  const appendPoints = (arr: { x: number; y: number }[], points: { x: number; y: number }[]) => {
    points.forEach(point => {
      const last = arr[arr.length - 1]
      if (last && last.x === point.x && last.y === point.y) return
      arr.push(point)
    })
  }

  const computePolylineLength = (pts: Array<{ x: number; y: number }>) => {
    let length = 0
    for (let i = 1; i < pts.length; i += 1) {
      const a = pts[i - 1]
      const b = pts[i]
      length += Math.abs(b.x - a.x) + Math.abs(b.y - a.y)
    }
    return length
  }

  const computePathHits = (pts: Array<{ x: number; y: number }>, obstacles: Rect[], clearanceValue: number) => {
    let hits = 0
    for (let i = 1; i < pts.length; i += 1) {
      const a = pts[i - 1]
      const b = pts[i]
      obstacles.forEach(rect => {
        if (segmentIntersectsRect(a, b, rect, clearanceValue)) hits += 1
      })
    }
    return hits
  }

  const hasSignificantDiagonal = (pts: number[], minDiagonal: number) => {
    if (pts.length < 4) return false
    for (let i = 2; i + 1 < pts.length; i += 2) {
      const dx = Math.abs(pts[i] - pts[i - 2])
      const dy = Math.abs(pts[i + 1] - pts[i - 1])
      if (dx <= 0.5 || dy <= 0.5) continue
      const len = Math.hypot(dx, dy)
      if (len >= minDiagonal) return true
    }
    return false
  }

  const simplifyOrthogonalPath = (pts: Array<{ x: number; y: number }>) => {
    if (pts.length <= 2) return pts
    const eps = 0.5
    const out: Array<{ x: number; y: number }> = []

    pts.forEach(point => {
      const last = out[out.length - 1]
      if (last && Math.abs(point.x - last.x) <= eps && Math.abs(point.y - last.y) <= eps) {
        return
      }
      out.push(point)
      while (out.length >= 3) {
        const a = out[out.length - 3]
        const b = out[out.length - 2]
        const c = out[out.length - 1]
        const colX = Math.abs(a.x - b.x) <= eps && Math.abs(b.x - c.x) <= eps
        const colY = Math.abs(a.y - b.y) <= eps && Math.abs(b.y - c.y) <= eps
        if (colX || colY) {
          out.splice(out.length - 2, 1)
        } else {
          break
        }
      }
    })

    return out
  }

  const orthogonalizePath = (
    pts: Array<{ x: number; y: number }>,
    preferAxis: 'x' | 'y'
  ) => {
    if (pts.length <= 1) return pts
    const out: Array<{ x: number; y: number }> = [pts[0]]
    for (let i = 1; i < pts.length; i += 1) {
      const prev = out[out.length - 1]
      const curr = pts[i]
      const sameX = Math.abs(prev.x - curr.x) < 0.5
      const sameY = Math.abs(prev.y - curr.y) < 0.5
      if (sameX || sameY) {
        out.push(curr)
        continue
      }
      if (preferAxis === 'x') {
        out.push({ x: curr.x, y: prev.y }, curr)
      } else {
        out.push({ x: prev.x, y: curr.y }, curr)
      }
    }
    return out
  }

  type ExitSide = 'left' | 'right' | 'top' | 'bottom'
  const exitBundleIndex = (() => {
    const index = new Map<string, { index: number; total: number; side: ExitSide }>()
    if (!isL1View) return index
    const grouped = new Map<string, Array<{ key: string; coord: number; side: ExitSide; linkId: string }>>()

    const add = (deviceId: string, side: ExitSide, coord: number, key: string, linkId: string) => {
      const groupKey = `${deviceId}|${side}`
      const list = grouped.get(groupKey) || []
      list.push({ key, coord, side, linkId })
      grouped.set(groupKey, list)
    }

    linkMetas.forEach(meta => {
      if (!meta) return
      const fromSide = (meta.fromAnchor.side || computeSide(meta.fromView, meta.toCenter)) as ExitSide
      const toSide = (meta.toAnchor.side || computeSide(meta.toView, meta.fromCenter)) as ExitSide
      const fromCoord = (fromSide === 'left' || fromSide === 'right') ? meta.fromAnchor.y : meta.fromAnchor.x
      const toCoord = (toSide === 'left' || toSide === 'right') ? meta.toAnchor.y : meta.toAnchor.x
      add(meta.link.fromDeviceId, fromSide, fromCoord, `${meta.link.id}|from`, meta.link.id)
      add(meta.link.toDeviceId, toSide, toCoord, `${meta.link.id}|to`, meta.link.id)
    })

    grouped.forEach(list => {
      list.sort((a, b) => {
        const primary = a.coord - b.coord
        if (primary !== 0) return primary
        return a.linkId.localeCompare(b.linkId)
      })
      list.forEach((entry, idx) => {
        index.set(entry.key, { index: idx, total: list.length, side: entry.side })
      })
    })

    return index
  })()

  const exitBundleGapBase = (renderTuning.bundle_gap ?? 0) * scale
  const labelGapBase = (renderTuning.port_label_offset ?? 0) * scale
  const gridCell = grid?.size ?? 0
  const exitBundleGap = exitBundleGapBase > 0
    ? Math.max(6, exitBundleGapBase, labelGapBase, gridCell)
    : 0
  const resolveExitGap = (entry?: { total: number }) => {
    if (!entry || entry.total <= 1 || exitBundleGap <= 0) return 0
    const extra = Math.max(0, entry.total - 4)
    const scaleFactor = clamp(1 + extra * 0.12, 1, 2.5)
    return exitBundleGap * scaleFactor
  }
  const resolveExitShift = (key: string) => {
    const entry = exitBundleIndex.get(key)
    const gap = resolveExitGap(entry)
    if (!entry || gap <= 0) return { dx: 0, dy: 0 }
    const offset = (entry.index - (entry.total - 1) / 2) * gap
    if (entry.side === 'left' || entry.side === 'right') {
      return { dx: 0, dy: offset }
    }
    return { dx: offset, dy: 0 }
  }
  const occupancy = new Map<string, number>()
  const corridorLoad = new Map<string, Map<number, number>>()
  const cache = new Map<string, {
    points: number[]
    fromAnchor: { x: number; y: number; side?: string }
    toAnchor: { x: number; y: number; side?: string }
    fromCenter: { x: number; y: number }
    toCenter: { x: number; y: number }
  }>()

  const areaPadMap = computeAreaPadInfo(
    areaRects,
    deviceRects,
    deviceAreaMap,
    renderTuning,
    scale,
  )
  const padCorridors = computePadCorridors(
    areaViewMap,
    areaCenters,
    linkMetas,
    areaPadMap,
    areaRects,
    deviceRects,
    renderTuning,
    scale,
  )

  const links = linkMetas
    .map(meta => {
      if (!meta) return null
      const {
        link,
        fromView,
        toView,
        fromCenter,
        toCenter,
        fromAreaId,
        toAreaId,
        fromArea,
        toArea
      } = meta
      let { fromAnchor, toAnchor } = meta

      let points: number[] = []
      const isL1 = isL1View
      const bundle = linkBundleIndex.get(link.id)
      const areaBundle = laneIndex.get(link.id) || areaBundleIndex.get(link.id)
      const fromExitEntry = exitBundleIndex.get(`${link.id}|from`)
      const toExitEntry = exitBundleIndex.get(`${link.id}|to`)
      const hasExitBundle = (fromExitEntry?.total ?? 0) > 1 || (toExitEntry?.total ?? 0) > 1
      const fromSide = (fromAnchor.side || computeSide(fromView, toCenter)) as ExitSide
      const toSide = (toAnchor.side || computeSide(toView, fromCenter)) as ExitSide
      // Keep endpoint anchor pinned to the port cell; lane separation starts after exit stub.
      fromAnchor = { ...fromAnchor, side: fromSide }
      toAnchor = { ...toAnchor, side: toSide }
      const bundleOffset = bundle && bundle.total > 1
        ? (bundle.index - (bundle.total - 1) / 2) * ((renderTuning.bundle_gap ?? 0) * scale)
        : 0
      const interAreaNudgeGap = Math.max(6, (renderTuning.bundle_gap ?? 0) * scale * 0.35)
      const areaBundleOffset = areaBundle && areaBundle.total > 1
        ? (areaBundle.index - (areaBundle.total - 1) / 2) * interAreaNudgeGap
        : 0
      const interBundleOffset = areaBundleOffset + bundleOffset * 0.35
      const anchorOffset = ((renderTuning.area_anchor_offset ?? 0) + (renderTuning.area_clearance ?? 0)) * scale
      const baseExitStub = Math.max(renderTuning.bundle_stub ?? 0, renderTuning.area_clearance ?? 0) * scale

      const pushPoint = (arr: number[], x: number, y: number) => {
        const len = arr.length
        if (len >= 2 && arr[len - 2] === x && arr[len - 1] === y) return
        arr.push(x, y)
      }

      const computePadAnchor = (
        areaRect: Rect,
        fromPoint: { x: number; y: number },
        side: PadSide,
        shift: number,
        padInfo: AreaPadInfo,
      ) => {
        const minY = areaRect.y + padInfo.inset
        const maxY = areaRect.y + areaRect.height - padInfo.inset
        const y = clamp(fromPoint.y + shift, minY, maxY)
        const x = side === 'left' ? padInfo.leftX : padInfo.rightX
        return { x, y }
      }

      const isIntraArea = !!(fromAreaId && toAreaId && fromAreaId === toAreaId)
      const obstacles: Array<Rect> = []
      deviceRects.forEach(({ id, rect }) => {
        if (id === link.fromDeviceId || id === link.toDeviceId) return
        obstacles.push(rect)
      })
      if (!isIntraArea) {
        areaRects.forEach(({ id, rect }) => {
          if (id === fromAreaId || id === toAreaId) return
          obstacles.push(rect)
        })
      }
      if (!isL1 && labelObstacles.length) {
        labelObstacles.forEach(entry => {
          if (entry.linkId === link.id) return
          obstacles.push(entry.rect)
        })
      }

      const lineBlocked = obstacles.some(rect =>
        segmentIntersectsRect(
          { x: fromAnchor.x, y: fromAnchor.y },
          { x: toAnchor.x, y: toAnchor.y },
          rect,
          clearance
        )
      )
      const directOrthogonal = Math.abs(fromAnchor.x - toAnchor.x) < 1 || Math.abs(fromAnchor.y - toAnchor.y) < 1
      const isInterArea = !!(fromAreaId && toAreaId && fromAreaId !== toAreaId && fromArea && toArea)
      const directAllowed = isL1 && !lineBlocked && directOrthogonal && !hasExitBundle && !isInterArea
      const parallelAllowed = isL1 && !lineBlocked && directOrthogonal && !isInterArea
      // Allow diagonal direct line when no obstacles block the path
      const diagonalAllowed = !isL1 && !lineBlocked && !directOrthogonal

      const labelScale = clamp(scale, LABEL_SCALE_MIN, LABEL_SCALE_MAX)
      const labelInset = Math.max(2, Math.round(6 * labelScale))
      const labelOffset = (renderTuning.port_label_offset ?? 0) * labelScale
      const baseLabelDistance = Math.max(0, labelOffset - labelInset)
      const minPortTurnDistance = Math.max(28 * scale, labelOffset + 22 * scale)
      const fromLabelWidth = meta.fromLabelWidth ?? 0
      const toLabelWidth = meta.toLabelWidth ?? 0
      const fromLabelStub = isL1View && fromLabelWidth > 0
        ? baseLabelDistance + fromLabelWidth / 2 + LABEL_STUB_PADDING
        : 0
      const toLabelStub = isL1View && toLabelWidth > 0
        ? baseLabelDistance + toLabelWidth / 2 + LABEL_STUB_PADDING
        : 0
      const fromStubDistance = Math.max(baseExitStub, fromLabelStub, minPortTurnDistance)
      const toStubDistance = Math.max(baseExitStub, toLabelStub, minPortTurnDistance)
      const fromBase = offsetFromAnchor(fromAnchor, fromStubDistance)
      const toBase = offsetFromAnchor(toAnchor, toStubDistance)
      const fromExitShift = resolveExitShift(`${link.id}|from`)
      const toExitShift = resolveExitShift(`${link.id}|to`)
      const fromExit = { x: fromBase.x + fromExitShift.dx, y: fromBase.y + fromExitShift.dy }
      const toExit = { x: toBase.x + toExitShift.dx, y: toBase.y + toExitShift.dy }
      const purpose = (link.purpose || '').trim().toUpperCase()
      const peerPurpose = resolvePeerPurposeKind(purpose, link.fromPort, link.toPort)
      const isPeerControlLink = isL1 && !!peerPurpose && isIntraArea

      let routed = false
      let occupancyRecorded = false

      if (isPeerControlLink && !routed) {
        const rowThreshold = Math.max(fromView.height, toView.height) * 0.85
        const sameRow = Math.abs(fromCenter.y - toCenter.y) <= rowThreshold
        if (sameRow) {
          const laneOffset =
            peerPurpose === 'stack'
              ? -10 * scale
              : peerPurpose === 'ha'
                ? 0
                : 10 * scale
          const laneY = (fromCenter.y + toCenter.y) / 2 + laneOffset
          const peerPath = [
            fromAnchor,
            fromBase,
            fromExit,
            { x: fromExit.x, y: laneY },
            { x: toExit.x, y: laneY },
            toExit,
            toBase,
            toAnchor,
          ]
          const blocked = peerPath.some((point, idx) => {
            if (idx === 0) return false
            const a = peerPath[idx - 1]
            const b = point
            return obstacles.some(rect => segmentIntersectsRect(a, b, rect, clearance))
          })
          if (!blocked) {
            points = []
            peerPath.forEach(point => pushPoint(points, point.x, point.y))
            routed = true
          }
        }
      }

      // Direct diagonal routing when no obstacles block the path
      if (diagonalAllowed && !routed) {
        // Check if we need stub for port labels
        const needFromStub = isL1View && meta.fromLabelWidth && meta.fromLabelWidth > 10
        const needToStub = isL1View && meta.toLabelWidth && meta.toLabelWidth > 10

        if (needFromStub || needToStub) {
          // Use stubs only when port labels exist
          pushPoint(points, fromAnchor.x, fromAnchor.y)
          if (needFromStub) pushPoint(points, fromBase.x, fromBase.y)
          if (needToStub) pushPoint(points, toBase.x, toBase.y)
          pushPoint(points, toAnchor.x, toAnchor.y)
        } else {
          // Pure diagonal line - no bends
          pushPoint(points, fromAnchor.x, fromAnchor.y)
          pushPoint(points, toAnchor.x, toAnchor.y)
        }
        routed = true
      }

      // Parallel straight routing for bundled links on same row/col
      if (parallelAllowed && hasExitBundle && !routed) {
        const alignIsVertical = Math.abs(fromAnchor.x - toAnchor.x) < 1
        const delta = alignIsVertical
          ? (fromAnchor.x - toAnchor.x)
          : (fromAnchor.y - toAnchor.y)
        const offset = Math.abs(delta) < 0.5 ? 0 : delta
        const offsetFromExit = alignIsVertical
          ? { x: fromExit.x + offset, y: fromExit.y }
          : { x: fromExit.x, y: fromExit.y + offset }
        const offsetToExit = alignIsVertical
          ? { x: toExit.x + offset, y: toExit.y }
          : { x: toExit.x, y: toExit.y + offset }
        const path = [
          fromAnchor,
          fromBase,
          fromExit,
          offsetFromExit,
          offsetToExit,
          toExit,
          toBase,
          toAnchor,
        ]
        const blocked = path.some((p, idx) => {
          if (idx === 0) return false
          const a = path[idx - 1]
          const b = p
          return obstacles.some(rect => segmentIntersectsRect(a, b, rect, clearance))
        })
        if (!blocked) {
          points = []
          pushPoint(points, fromAnchor.x, fromAnchor.y)
          pushPoint(points, fromBase.x, fromBase.y)
          pushPoint(points, fromExit.x, fromExit.y)
          pushPoint(points, offsetFromExit.x, offsetFromExit.y)
          pushPoint(points, offsetToExit.x, offsetToExit.y)
          pushPoint(points, toExit.x, toExit.y)
          pushPoint(points, toBase.x, toBase.y)
          pushPoint(points, toAnchor.x, toAnchor.y)
          routed = true
        }
      }

      // Hành lang pad cho tuyến liên-area (ép trái/phải trong vùng đệm)
      if (!routed && isL1 && isInterArea && fromAreaId && toAreaId && fromArea && toArea) {
        const pairKey = getPairKey(fromAreaId, toAreaId)
        const corridorPlan = padCorridors.get(pairKey)
        const padFrom = areaPadMap.get(fromAreaId)
        const padTo = areaPadMap.get(toAreaId)
        if (corridorPlan && corridorPlan.channels.length && padFrom && padTo) {
          const channelCount = corridorPlan.channels.length
          const bundleTotal = Math.max(1, areaBundle?.total ?? corridorPlan.linkCount)
          const bundleIndex = Math.max(0, areaBundle?.index ?? 0)
          const linksPerChannel = Math.max(1, Math.ceil(bundleTotal / channelCount))
          const preferredChannel = Math.min(channelCount - 1, Math.floor(bundleIndex / linksPerChannel))
          const localStart = preferredChannel * linksPerChannel
          const localTotal = Math.max(1, Math.min(linksPerChannel, bundleTotal - localStart))
          const localIndex = Math.max(0, Math.min(localTotal - 1, bundleIndex - localStart))
          const laneNudgeGap = Math.max(4, corridorPlan.laneSpacing * 0.24)
          const laneNudge = localTotal > 1
            ? (localIndex - (localTotal - 1) / 2) * laneNudgeGap
            : 0
          const occupancyWeightRaw = Number(renderTuning.inter_area_occupancy_weight ?? 1)
          const occupancyWeight = clamp(Number.isFinite(occupancyWeightRaw) ? occupancyWeightRaw : 1, 0, 5)

          const channelOrder = corridorPlan.channels
            .map((channel, idx) => ({
              channel,
              idx,
              distance: Math.abs(idx - preferredChannel),
            }))
            .sort((a, b) => {
              const primary = a.distance - b.distance
              if (primary !== 0) return primary
              return a.idx - b.idx
            })
          const maxChannelCandidates = 3

          let bestRoute: {
            score: number
            hits: number
            path: Array<{ x: number; y: number }>
            channelIndex: number
          } | null = null

          for (const candidate of channelOrder.slice(0, maxChannelCandidates)) {
            const laneCoord = resolvePadCorridorCoord(
              candidate.channel.side,
              candidate.channel.coord + laneNudge,
              padFrom,
              padTo,
            )
            const fromAreaAnchor = computePadAnchor(fromArea, fromExit, candidate.channel.side, laneNudge, padFrom)
            const toAreaAnchor = computePadAnchor(toArea, toExit, candidate.channel.side, laneNudge, padTo)
            const corridorPath: Array<{ x: number; y: number }> = [
              fromAnchor, fromBase, fromExit, fromAreaAnchor,
              { x: laneCoord, y: fromAreaAnchor.y },
              { x: laneCoord, y: toAreaAnchor.y },
              toAreaAnchor, toExit, toBase, toAnchor,
            ]
            const simplified = simplifyOrthogonalPath(corridorPath)
            const hits = computePathHits(simplified, obstacles, clearance)
            const length = computePolylineLength(simplified)
            const pairLoad = corridorLoad.get(pairKey)
            const channelLoad = pairLoad?.get(candidate.idx) || 0
            const occupancyCost = channelLoad * occupancyWeight * Math.max(1, corridorPlan.laneSpacing * 0.35)
            const channelPenalty = candidate.distance * corridorPlan.laneSpacing * 1.6
            const score = hits * 100000 + length + occupancyCost + channelPenalty
            if (!bestRoute || score < bestRoute.score) {
              bestRoute = { score, hits, path: simplified, channelIndex: candidate.idx }
            }
          }

          if (bestRoute && bestRoute.hits === 0) {
            points = []
            bestRoute.path.forEach(point => pushPoint(points, point.x, point.y))
            const pairLoad = corridorLoad.get(pairKey) || new Map<number, number>()
            pairLoad.set(bestRoute.channelIndex, (pairLoad.get(bestRoute.channelIndex) || 0) + 1)
            corridorLoad.set(pairKey, pairLoad)
            routed = true
          }
        }
      }

      // Ưu tiên A*/orthogonal cho L1; non-L1 dùng any-angle.
      if (allowAStar && !directAllowed && !routed && grid) {
        const preferAxis = Math.abs(toCenter.x - fromCenter.x) >= Math.abs(toCenter.y - fromCenter.y) ? 'x' : 'y'
        const bundleShift = preferAxis === 'x'
          ? { x: 0, y: bundleOffset }
          : { x: bundleOffset, y: 0 }
        const offsetFromExit = {
          x: fromExit.x + bundleShift.x,
          y: fromExit.y + bundleShift.y
        }
        const offsetToExit = {
          x: toExit.x + bundleShift.x,
          y: toExit.y + bundleShift.y
        }

        const routeOrthogonal = (start: { x: number; y: number }, end: { x: number; y: number }) => {
          return routeOrthogonalPath({
            start,
            end,
            obstacles,
            clearance,
            grid,
            occupancy,
            preferAxis,
            turnPenalty: grid.size * 1.2,
            congestionPenalty: grid.size * 80
          })
        }

        if (isL1) {
          const waypointKey = fromAreaId && toAreaId ? getPairKey(fromAreaId, toAreaId) : null
          const waypoint = waypointKey ? waypointAreaMap.get(waypointKey) : null
          let routeSegments: Array<{ points: Array<{ x: number; y: number }>; gridPath: Array<{ gx: number; gy: number }> }> = []

          if (waypoint && waypoint.rect) {
            const wpShift = areaBundleOffset
            const wpEntry = computeAreaAnchor(waypoint.rect, offsetFromExit, offsetToExit, wpShift, 0)
            const wpExit = computeAreaAnchor(waypoint.rect, offsetToExit, offsetFromExit, wpShift, 0)

            const routeA = routeOrthogonal(offsetFromExit, wpEntry)
            const routeB = routeOrthogonal(wpExit, offsetToExit)
            if (routeA && routeB) {
              const waypointPoints = (wpEntry.x === wpExit.x || wpEntry.y === wpExit.y)
                ? [wpEntry, wpExit]
                : [wpEntry, { x: wpEntry.x, y: wpExit.y }, wpExit]
              routeSegments = [
                { points: routeA.points, gridPath: routeA.gridPath },
                { points: waypointPoints, gridPath: [] },
                { points: routeB.points, gridPath: routeB.gridPath }
              ]
            }
          }

          if (routeSegments.length === 0) {
            const route = routeOrthogonal(offsetFromExit, offsetToExit)
            if (route && route.points.length) {
              routeSegments = [{ points: route.points, gridPath: route.gridPath }]
            }
          }

          if (routeSegments.length) {
            const assembled: Array<{ x: number; y: number }> = []
            appendPoints(assembled, [fromAnchor, fromBase, fromExit])
            routeSegments.forEach(segment => {
              appendPoints(assembled, segment.points)
              if (segment.gridPath.length) {
                addOccupancy(occupancy, segment.gridPath)
                occupancyRecorded = true
              }
            })
            appendPoints(assembled, [toExit, toBase, toAnchor])

            const simplified = simplifyOrthogonalPath(assembled)
            simplified.forEach(point => pushPoint(points, point.x, point.y))
            routed = true
          }
        } else {
          const route = routeAnyAnglePath({
            start: offsetFromExit,
            end: offsetToExit,
            obstacles,
            clearance,
            grid,
            occupancy,
            preferAxis
          })

          if (route && route.points.length) {
            const assembled: Array<{ x: number; y: number }> = []
            appendPoints(assembled, [fromAnchor, fromBase, fromExit])
            appendPoints(assembled, route.points)
            appendPoints(assembled, [toExit, toBase, toAnchor])

            const cornerRadius = Math.max(2, Math.min(minSegment * 0.8, 12 * scale))
            const smoothed = smoothAnyAnglePath(assembled, obstacles, clearance, cornerRadius, minSegment)
            smoothed.forEach(point => pushPoint(points, point.x, point.y))
            addOccupancy(occupancy, route.gridPath)
            occupancyRecorded = true
            routed = true
          }
        }
      }

      if (!routed) {
        if (fromAreaId && toAreaId && fromAreaId !== toAreaId && fromArea && toArea) {
          // Fallback corridor khi chưa có route an toàn qua A*/waypoint.
          const localCorridor = computeLocalCorridor(
            fromArea,
            toArea,
            fromExit,
            toExit,
            fromAreaId,
            toAreaId,
            interBundleOffset,
            clearance,
            areaRects,
            deviceRects
          )
          if (localCorridor) {
            const { axis, coord, fromAreaAnchor, toAreaAnchor } = localCorridor
            points = []
            pushPoint(points, fromAnchor.x, fromAnchor.y)
            pushPoint(points, fromBase.x, fromBase.y)
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
            pushPoint(points, toBase.x, toBase.y)
            pushPoint(points, toAnchor.x, toAnchor.y)
          } else {
            const fromAreaAnchor = computeAreaAnchor(fromArea, fromExit, toExit, interBundleOffset, anchorOffset)
            const toAreaAnchor = computeAreaAnchor(toArea, toExit, fromExit, interBundleOffset, anchorOffset)
            const primaryAxis: 'x' | 'y' = Math.abs(toAreaAnchor.x - fromAreaAnchor.x) >= Math.abs(toAreaAnchor.y - fromAreaAnchor.y)
              ? 'x'
              : 'y'
            const orth = connectOrthogonal(fromAreaAnchor, toAreaAnchor, obstacles, clearance, primaryAxis)
            points = []
            pushPoint(points, fromAnchor.x, fromAnchor.y)
            pushPoint(points, fromBase.x, fromBase.y)
            pushPoint(points, fromExit.x, fromExit.y)
            pushPoint(points, fromAreaAnchor.x, fromAreaAnchor.y)
            if (orth && orth.length) {
              orth.forEach(p => pushPoint(points, p.x, p.y))
            } else if (primaryAxis === 'x') {
              const midX = (fromAreaAnchor.x + toAreaAnchor.x) / 2 + interBundleOffset * 0.35
              pushPoint(points, midX, fromAreaAnchor.y)
              pushPoint(points, midX, toAreaAnchor.y)
            } else {
              const midY = (fromAreaAnchor.y + toAreaAnchor.y) / 2 + interBundleOffset * 0.35
              pushPoint(points, fromAreaAnchor.x, midY)
              pushPoint(points, toAreaAnchor.x, midY)
            }
            pushPoint(points, toAreaAnchor.x, toAreaAnchor.y)
            pushPoint(points, toExit.x, toExit.y)
            pushPoint(points, toBase.x, toBase.y)
            pushPoint(points, toAnchor.x, toAnchor.y)
          }
        } else if (isL1) {
          const preferAxis = Math.abs(toCenter.x - fromCenter.x) >= Math.abs(toCenter.y - fromCenter.y) ? 'x' : 'y'
          const bundleShift = preferAxis === 'x'
            ? { x: 0, y: bundleOffset }
            : { x: bundleOffset, y: 0 }
          const fromStart = { x: fromExit.x + bundleShift.x, y: fromExit.y + bundleShift.y }
          const toStart = { x: toExit.x + bundleShift.x, y: toExit.y + bundleShift.y }

          const orth = connectOrthogonal(fromStart, toStart, obstacles, clearance, preferAxis)
          if (orth && orth.length) {
            points = []
            pushPoint(points, fromAnchor.x, fromAnchor.y)
            pushPoint(points, fromBase.x, fromBase.y)
            pushPoint(points, fromExit.x, fromExit.y)
            orth.forEach(p => pushPoint(points, p.x, p.y))
            pushPoint(points, toExit.x, toExit.y)
            pushPoint(points, toBase.x, toBase.y)
            pushPoint(points, toAnchor.x, toAnchor.y)
          } else {
            const blockedRects: Rect[] = []
            areaViewMap.forEach((rect, areaId) => {
              if (areaId === fromAreaId || areaId === toAreaId) return
              if (segmentIntersectsRect({ x: fromAnchor.x, y: fromAnchor.y }, { x: toAnchor.x, y: toAnchor.y }, rect, renderTuning.area_clearance ?? 0)) {
                blockedRects.push(rect)
              }
            })
            deviceRects.forEach(({ id, rect }) => {
              if (id === link.fromDeviceId || id === link.toDeviceId) return
              if (segmentIntersectsRect({ x: fromAnchor.x, y: fromAnchor.y }, { x: toAnchor.x, y: toAnchor.y }, rect, renderTuning.area_clearance ?? 0)) {
                blockedRects.push(rect)
              }
            })

            const midA = { x: fromStart.x, y: toStart.y }
            const midB = { x: toStart.x, y: fromStart.y }
            const score = (a: { x: number; y: number }) => {
              let hits = 0
              blockedRects.forEach(rect => {
                if (segmentIntersectsRect(fromStart, a, rect, renderTuning.area_clearance ?? 0)) hits += 1
                if (segmentIntersectsRect(a, toStart, rect, renderTuning.area_clearance ?? 0)) hits += 1
              })
              const length = Math.hypot(a.x - fromStart.x, a.y - fromStart.y) + Math.hypot(toStart.x - a.x, toStart.y - a.y)
              return hits * 10000 + length
            }
            const scoreA = score(midA)
            const scoreB = score(midB)
            const mid = scoreA <= scoreB ? midA : midB
            points = []
            pushPoint(points, fromAnchor.x, fromAnchor.y)
            pushPoint(points, fromBase.x, fromBase.y)
            pushPoint(points, fromExit.x, fromExit.y)
            pushPoint(points, fromStart.x, fromStart.y)
            pushPoint(points, mid.x, mid.y)
            pushPoint(points, toStart.x, toStart.y)
            pushPoint(points, toExit.x, toExit.y)
            pushPoint(points, toBase.x, toBase.y)
            pushPoint(points, toAnchor.x, toAnchor.y)
          }
        } else {
          const dx = toAnchor.x - fromAnchor.x
          const dy = toAnchor.y - fromAnchor.y

          if (Math.abs(dx) < 5 && Math.abs(dy) < 5) {
            points = [fromAnchor.x, fromAnchor.y, toAnchor.x, toAnchor.y]
          } else if (Math.abs(dx) >= Math.abs(dy)) {
            const midX = fromAnchor.x + dx / 2
            points = [
              fromAnchor.x, fromAnchor.y,
              midX, fromAnchor.y,
              midX, toAnchor.y,
              toAnchor.x, toAnchor.y
            ]
          } else {
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

      if (isL1 && points.length >= 4) {
        const rawPathPoints: Array<{ x: number; y: number }> = []
        for (let i = 0; i + 1 < points.length; i += 2) {
          rawPathPoints.push({ x: points[i], y: points[i + 1] })
        }
        const isPathBlocked = (path: Array<{ x: number; y: number }>) => {
          return path.some((point, idx) => {
            if (idx === 0) return false
            const prev = path[idx - 1]
            return obstacles.some(rect => segmentIntersectsRect(prev, point, rect, clearance))
          })
        }
        const primaryAxis: 'x' | 'y' = Math.abs(toCenter.x - fromCenter.x) >= Math.abs(toCenter.y - fromCenter.y)
          ? 'x'
          : 'y'
        const orth = orthogonalizePath(rawPathPoints, primaryAxis)
        const simplifiedOrth = simplifyOrthogonalPath(orth)
        const simplifiedRaw = simplifyOrthogonalPath(rawPathPoints)
        const orthBlocked = isPathBlocked(simplifiedOrth)
        let finalPath = orthBlocked ? simplifiedRaw : simplifiedOrth
        if (isPathBlocked(finalPath)) {
          const emergency = connectOrthogonal(fromExit, toExit, obstacles, clearance, primaryAxis)
          if (emergency && emergency.length) {
            const assembled: Array<{ x: number; y: number }> = [fromAnchor, fromBase, fromExit]
            appendPoints(assembled, emergency)
            appendPoints(assembled, [toExit, toBase, toAnchor])
            finalPath = simplifyOrthogonalPath(assembled)
          }
        }
        points = []
        finalPath.forEach(point => pushPoint(points, point.x, point.y))
      }

      if (grid && isInterArea && points.length >= 4 && !occupancyRecorded) {
        const pathPoints: Array<{ x: number; y: number }> = []
        for (let i = 0; i + 1 < points.length; i += 2) {
          pathPoints.push({ x: points[i], y: points[i + 1] })
        }
        const gridPath = polylineToGridPath(pathPoints, grid)
        if (gridPath.length >= 2) {
          addOccupancy(occupancy, gridPath)
          occupancyRecorded = true
        }
      }

      const neutralL1Purposes = new Set(['', 'DEFAULT', 'LAN'])
      const purposeStroke = resolveLinkPurposeColor(link.purpose)
      const peerVisual = peerPurpose ? PEER_PURPOSE_VISUAL[peerPurpose] : null
      const baseStroke = peerVisual
        ? peerVisual.stroke
        : ((isL1 && neutralL1Purposes.has(purpose)) ? '#2b2a28' : purposeStroke)
      const debugStroke = (() => {
        if (!debugOn) return baseStroke
        if (!isL1) return DEBUG_STROKE_L2
        const minDiagonal = Math.max(12, minSegment * 2)
        if (hasSignificantDiagonal(points, minDiagonal)) return DEBUG_STROKE_L1_DIAGONAL
        return baseStroke
      })()
      const dash = peerVisual
        ? peerVisual.dash
        : (link.style === 'dashed' ? [8, 6] : link.style === 'dotted' ? [2, 4] : [])
      const strokeWidth = peerVisual
        ? peerVisual.strokeWidth
        : (isL1 ? 1.35 : 1.5)
      const opacity = peerVisual
        ? peerVisual.opacity
        : (isL1 ? 0.92 : 0.8)

      return {
        id: link.id,
        fromAnchor,
        toAnchor,
        fromCenter,
        toCenter,
        points,
        config: {
          points,
          stroke: debugStroke,
          strokeWidth,
          lineCap: isL1 ? 'butt' : 'round',
          lineJoin: isL1 ? 'miter' : 'round',
          dash,
          opacity
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
