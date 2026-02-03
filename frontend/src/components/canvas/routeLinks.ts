import type { Rect, RenderLink, RenderTuning, LinkMeta, AreaRectEntry, DeviceRectEntry } from './linkRoutingTypes'
import {
  clamp,
  computeSide,
  normalizeVector,
  offsetFromAnchor,
  segmentIntersectsRect,
  computeAreaAnchor,
} from './linkRoutingUtils'
import { addOccupancy, connectOrthogonal, routeOrthogonalPath, simplifyOrthogonalPath } from '../../utils/link_routing'

export type RouteLinksParams = {
  isL1View: boolean
  scale: number
  clearance: number
  minSegment: number
  grid: { cols: number; rows: number; minX: number; minY: number; cellSize: number } | null
  allowAStar: boolean
  areaRects: AreaRectEntry[]
  deviceRects: DeviceRectEntry[]
  renderTuning: RenderTuning
  areaViewMap: Map<string, Rect>
  deviceAreaMap: Map<string, string>
  areaBounds: { minX: number; minY: number; maxX: number; maxY: number } | null
  linkBundleIndex: Map<string, { index: number; total: number }>
  areaBundleIndex: Map<string, { index: number; total: number }>
  waypointAreaMap: Map<string, { cx: number; cy: number; rect: Rect }>
  areaCenters: Map<string, { x: number; y: number }>
}

const LABEL_STUB_PADDING = 4

function computeLocalCorridor(
  fromArea: Rect,
  toArea: Rect,
  fromExit: { x: number; y: number },
  toExit: { x: number; y: number },
  fromAreaId: string | null,
  toAreaId: string | null,
  interBundleOffset: number,
  clearanceValue: number,
  areaRects: AreaRectEntry[]
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
  } = ctx

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

  const appendPoints = (arr: { x: number; y: number }[], points: { x: number; y: number }[]) => {
    points.forEach(point => {
      const last = arr[arr.length - 1]
      if (last && last.x === point.x && last.y === point.y) return
      arr.push(point)
    })
  }

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
      const bundle = linkBundleIndex.get(link.id)
      const areaBundle = laneIndex.get(link.id) || areaBundleIndex.get(link.id)
      const bundleOffset = bundle && bundle.total > 1
        ? (bundle.index - (bundle.total - 1) / 2) * ((renderTuning.bundle_gap ?? 0) * scale)
        : 0
      const interAreaBundleGap = (renderTuning.bundle_gap ?? 0) * scale
        * (areaBundle && areaBundle.total > 4 ? 1.9 : 1.6)
      const areaBundleOffset = areaBundle && areaBundle.total > 1
        ? (areaBundle.index - (areaBundle.total - 1) / 2) * interAreaBundleGap
        : 0
      const interBundleOffset = areaBundleOffset + bundleOffset * 0.5
      const bundleStub = (renderTuning.bundle_stub ?? 0) * scale
      const anchorOffset = ((renderTuning.area_anchor_offset ?? 0) + (renderTuning.area_clearance ?? 0)) * scale
      const baseExitStub = Math.max(renderTuning.bundle_stub ?? 0, renderTuning.area_clearance ?? 0) * scale

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
      const fromLabelStub = isL1View && meta.fromLabelWidth ? meta.fromLabelWidth + LABEL_STUB_PADDING : 0
      const toLabelStub = isL1View && meta.toLabelWidth ? meta.toLabelWidth + LABEL_STUB_PADDING : 0
      const fromExit = offsetFromAnchor(
        { ...fromAnchor, side: fromSide },
        Math.max(baseExitStub, fromLabelStub)
      )
      const toExit = offsetFromAnchor(
        { ...toAnchor, side: toSide },
        Math.max(baseExitStub, toLabelStub)
      )

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
        if (fromAreaId && toAreaId && fromAreaId !== toAreaId && fromArea && toArea) {
          const wpKey = fromAreaId < toAreaId ? `${fromAreaId}|${toAreaId}` : `${toAreaId}|${fromAreaId}`
          const wp = waypointAreaMap.get(wpKey)

          if (wp) {
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
            const localCorridor = computeLocalCorridor(
              fromArea,
              toArea,
              fromExit,
              toExit,
              fromAreaId,
              toAreaId,
              interBundleOffset,
              clearance,
              areaRects
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
              if (areaBounds) {
                const corridorGap = (renderTuning.corridor_gap ?? 0) + (renderTuning.area_clearance ?? 0) + Math.abs(interBundleOffset)
                const dx = toAnchor.x - fromAnchor.x
                const dy = toAnchor.y - fromAnchor.y
                if (Math.abs(dx) >= Math.abs(dy)) {
                  const topY = areaBounds.minY - corridorGap
                  const bottomY = areaBounds.maxY + corridorGap
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
                  const leftX = areaBounds.minX - corridorGap
                  const rightX = areaBounds.maxX + corridorGap
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
          const useCenters = bundleOffset !== 0
          const fromBase = fromExit
          const toBase = toExit
          const dx = useCenters ? (toCenter.x - fromCenter.x) : (toBase.x - fromBase.x)
          const dy = useCenters ? (toCenter.y - fromCenter.y) : (toBase.y - fromBase.y)
          const dir = normalizeVector(dx, dy)
          const perp = normalizeVector(-dir.y, dir.x)
          if (bundleOffset !== 0 && (dir.x !== 0 || dir.y !== 0)) {
            const fromStub = { x: fromBase.x + dir.x * bundleStub, y: fromBase.y + dir.y * bundleStub }
            const toStub = { x: toBase.x - dir.x * bundleStub, y: toBase.y - dir.y * bundleStub }
            const fromShift = { x: fromStub.x + perp.x * bundleOffset, y: fromStub.y + perp.y * bundleOffset }
            const toShift = { x: toStub.x + perp.x * bundleOffset, y: toStub.y + perp.y * bundleOffset }
            points = []
            pushPoint(points, fromAnchor.x, fromAnchor.y)
            pushPoint(points, fromBase.x, fromBase.y)
            pushPoint(points, fromShift.x, fromShift.y)
            pushPoint(points, toShift.x, toShift.y)
            pushPoint(points, toBase.x, toBase.y)
            pushPoint(points, toAnchor.x, toAnchor.y)
          } else {
            points = []
            pushPoint(points, fromAnchor.x, fromAnchor.y)
            pushPoint(points, fromBase.x, fromBase.y)
            pushPoint(points, toBase.x, toBase.y)
            pushPoint(points, toAnchor.x, toAnchor.y)
          }

          if (bundleOffset === 0) {
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
            if (blockedRects.length) {
              const midA = { x: fromBase.x, y: toBase.y }
              const midB = { x: toBase.x, y: fromBase.y }
              const score = (a: { x: number; y: number }) => {
                let hits = 0
                blockedRects.forEach(rect => {
                  if (segmentIntersectsRect(fromBase, a, rect, renderTuning.area_clearance ?? 0)) hits += 1
                  if (segmentIntersectsRect(a, toBase, rect, renderTuning.area_clearance ?? 0)) hits += 1
                })
                const length = Math.hypot(a.x - fromBase.x, a.y - fromBase.y) + Math.hypot(toBase.x - a.x, toBase.y - a.y)
                return hits * 10000 + length
              }
              const scoreA = score(midA)
              const scoreB = score(midB)
              const mid = scoreA <= scoreB ? midA : midB
              points = []
              pushPoint(points, fromAnchor.x, fromAnchor.y)
              pushPoint(points, fromBase.x, fromBase.y)
              pushPoint(points, mid.x, mid.y)
              pushPoint(points, toBase.x, toBase.y)
              pushPoint(points, toAnchor.x, toAnchor.y)
            }
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
