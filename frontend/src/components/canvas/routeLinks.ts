import type { Rect, RenderLink, RenderTuning, LinkMeta, AreaRectEntry, DeviceRectEntry } from './linkRoutingTypes'
import {
  clamp,
  computeSide,
  normalizeVector,
  offsetFromAnchor,
  segmentIntersectsRect,
  computeAreaAnchor,
} from './linkRoutingUtils'
import { resolveLinkPurposeColor } from '../../composables/canvasConstants'
import { addOccupancy, connectOrthogonal, routeAnyAnglePath, routeOrthogonalPath, smoothAnyAnglePath } from '../../utils/link_routing'

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
  waypointAreaMap: Map<string, { id: string; cx: number; cy: number; rect: Rect }>
  areaCenters: Map<string, { x: number; y: number }>
  debugRouteMode?: boolean
}

const LABEL_STUB_PADDING = 4
const DEBUG_STROKE_L2 = '#c0392b'
const DEBUG_STROKE_L1_DIAGONAL = '#d35400'

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
    debugRouteMode,
  } = ctx
  const debugOn = !!debugRouteMode

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

  const hasCorner = (pts: number[]) => {
    if (pts.length < 6) return false
    for (let i = 2; i + 3 < pts.length; i += 2) {
      const ax = pts[i - 2]
      const ay = pts[i - 1]
      const bx = pts[i]
      const by = pts[i + 1]
      const cx = pts[i + 2]
      const cy = pts[i + 3]
      const dx1 = bx - ax
      const dy1 = by - ay
      const dx2 = cx - bx
      const dy2 = cy - by
      const len1 = Math.hypot(dx1, dy1)
      const len2 = Math.hypot(dx2, dy2)
      if (len1 <= 0 || len2 <= 0) continue
      const dot = (dx1 * dx2 + dy1 * dy2) / (len1 * len2)
      if (dot < 0.999) return true
    }
    return false
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

  const roundOrthogonalCorners = (
    pts: Array<{ x: number; y: number }>,
    cornerRadius: number,
    minSegmentValue: number
  ) => {
    if (pts.length <= 2) return pts
    const output: Array<{ x: number; y: number }> = [pts[0]]
    for (let i = 1; i < pts.length - 1; i += 1) {
      const prev = pts[i - 1]
      const curr = pts[i]
      const next = pts[i + 1]
      const v1x = prev.x - curr.x
      const v1y = prev.y - curr.y
      const v2x = next.x - curr.x
      const v2y = next.y - curr.y
      const len1 = Math.hypot(v1x, v1y)
      const len2 = Math.hypot(v2x, v2y)
      if (len1 <= 0 || len2 <= 0) {
        output.push(curr)
        continue
      }
      const dot = (v1x * v2x + v1y * v2y) / (len1 * len2)
      if (dot > 0.999) {
        output.push(curr)
        continue
      }
      const offset = Math.min(cornerRadius, len1 * 0.4, len2 * 0.4)
      if (offset < minSegmentValue * 0.25) {
        output.push(curr)
        continue
      }
      const p1 = { x: curr.x + (v1x / len1) * offset, y: curr.y + (v1y / len1) * offset }
      const p2 = { x: curr.x + (v2x / len2) * offset, y: curr.y + (v2y / len2) * offset }
      output.push(p1, p2)
    }
    output.push(pts[pts.length - 1])
    return output
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
  const exitBundleGap = exitBundleGapBase > 0 ? Math.max(6, exitBundleGapBase * 0.85) : 0
  const resolveExitShift = (key: string) => {
    const entry = exitBundleIndex.get(key)
    if (!entry || entry.total <= 1 || exitBundleGap <= 0) return { dx: 0, dy: 0 }
    const offset = (entry.index - (entry.total - 1) / 2) * exitBundleGap
    if (entry.side === 'left' || entry.side === 'right') {
      return { dx: 0, dy: offset }
    }
    return { dx: offset, dy: 0 }
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
      // Increased multiplier for better corridor separation
      const interAreaBundleGap = (renderTuning.bundle_gap ?? 0) * scale
        * (areaBundle && areaBundle.total > 4 ? 2.5 : 2.0)
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

      const lineBlocked = obstacles.some(rect =>
        segmentIntersectsRect(
          { x: fromAnchor.x, y: fromAnchor.y },
          { x: toAnchor.x, y: toAnchor.y },
          rect,
          clearance
        )
      )
      const directOrthogonal = Math.abs(fromAnchor.x - toAnchor.x) < 1 || Math.abs(fromAnchor.y - toAnchor.y) < 1
      const directAllowed = isL1 && !lineBlocked && directOrthogonal
      // Allow diagonal direct line when no obstacles block the path
      const diagonalAllowed = !lineBlocked && !directOrthogonal

      const fromSide = fromAnchor.side || computeSide(fromView, toCenter)
      const toSide = toAnchor.side || computeSide(toView, fromCenter)
      const fromLabelStub = isL1View && meta.fromLabelWidth ? meta.fromLabelWidth + LABEL_STUB_PADDING : 0
      const toLabelStub = isL1View && meta.toLabelWidth ? meta.toLabelWidth + LABEL_STUB_PADDING : 0
      const fromBase = offsetFromAnchor(
        { ...fromAnchor, side: fromSide },
        Math.max(baseExitStub, fromLabelStub)
      )
      const toBase = offsetFromAnchor(
        { ...toAnchor, side: toSide },
        Math.max(baseExitStub, toLabelStub)
      )
      const fromExitShift = resolveExitShift(`${link.id}|from`)
      const toExitShift = resolveExitShift(`${link.id}|to`)
      const fromExit = { x: fromBase.x + fromExitShift.dx, y: fromBase.y + fromExitShift.dy }
      const toExit = { x: toBase.x + toExitShift.dx, y: toBase.y + toExitShift.dy }

      let routed = false

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

      // Use direct any-angle routing for all links (waypoint logic disabled)
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

        // Convert grid format to GridSpec
        const gridSpec = {
          originX: grid.minX,
          originY: grid.minY,
          size: grid.cellSize,
          cols: grid.cols,
          rows: grid.rows
        }

        const routeOrthogonal = (start: { x: number; y: number }, end: { x: number; y: number }) => {
          return routeOrthogonalPath({
            start,
            end,
            obstacles,
            clearance,
            grid: gridSpec,
            occupancy,
            preferAxis,
            turnPenalty: gridSpec.size * 1.2,
            congestionPenalty: gridSpec.size * 25
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
              if (segment.gridPath.length) addOccupancy(occupancy, segment.gridPath)
            })
            appendPoints(assembled, [toExit, toBase, toAnchor])

            const simplified = simplifyOrthogonalPath(assembled)
            const cornerRadius = Math.max(4, Math.min(minSegment * 1.2, 14 * scale))
            const rounded = roundOrthogonalCorners(simplified, cornerRadius, minSegment)
            rounded.forEach(point => pushPoint(points, point.x, point.y))
            routed = true
          }
        } else {
          const route = routeAnyAnglePath({
            start: offsetFromExit,
            end: offsetToExit,
            obstacles,
            clearance,
            grid: gridSpec,
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
            routed = true
          }
        }
      }

      if (!routed) {
        if (fromAreaId && toAreaId && fromAreaId !== toAreaId && fromArea && toArea) {
          // Waypoint routing disabled - use corridor fallback directly
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
                pushPoint(points, fromBase.x, fromBase.y)
                pushPoint(points, fromExit.x, fromExit.y)
                pushPoint(points, fromAreaAnchor.x, fromAreaAnchor.y)
                pushPoint(points, fromAreaAnchor.x, corridorY)
                pushPoint(points, toAreaAnchor.x, corridorY)
                pushPoint(points, toAreaAnchor.x, toAreaAnchor.y)
                pushPoint(points, toExit.x, toExit.y)
                pushPoint(points, toBase.x, toBase.y)
                pushPoint(points, toAnchor.x, toAnchor.y)
              } else {
                const leftX = areaBounds.minX - corridorGap
                const rightX = areaBounds.maxX + corridorGap
                const midX = (fromAnchor.x + toAnchor.x) / 2
                const corridorBaseX = Math.abs(midX - leftX) <= Math.abs(midX - rightX) ? leftX : rightX
                const corridorX = corridorBaseX + interBundleOffset
                points = []
                pushPoint(points, fromAnchor.x, fromAnchor.y)
                pushPoint(points, fromBase.x, fromBase.y)
                pushPoint(points, fromExit.x, fromExit.y)
                pushPoint(points, fromAreaAnchor.x, fromAreaAnchor.y)
                pushPoint(points, corridorX, fromAreaAnchor.y)
                pushPoint(points, corridorX, toAreaAnchor.y)
                pushPoint(points, toAreaAnchor.x, toAreaAnchor.y)
                pushPoint(points, toExit.x, toExit.y)
                pushPoint(points, toBase.x, toBase.y)
                pushPoint(points, toAnchor.x, toAnchor.y)
              }
            } else {
              const midX = (fromAnchor.x + toAnchor.x) / 2 + interBundleOffset
              points = []
              pushPoint(points, fromAnchor.x, fromAnchor.y)
              pushPoint(points, fromBase.x, fromBase.y)
              pushPoint(points, fromExit.x, fromExit.y)
              pushPoint(points, fromAreaAnchor.x, fromAreaAnchor.y)
              pushPoint(points, midX, fromAreaAnchor.y)
              pushPoint(points, midX, toAreaAnchor.y)
              pushPoint(points, toAreaAnchor.x, toAreaAnchor.y)
              pushPoint(points, toExit.x, toExit.y)
              pushPoint(points, toBase.x, toBase.y)
              pushPoint(points, toAnchor.x, toAnchor.y)
            }
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

      if (isL1 && !routed && points.length >= 6 && hasCorner(points)) {
        const pathPoints: Array<{ x: number; y: number }> = []
        for (let i = 0; i + 1 < points.length; i += 2) {
          pathPoints.push({ x: points[i], y: points[i + 1] })
        }
        const simplified = simplifyOrthogonalPath(pathPoints)
        const cornerRadius = Math.max(4, Math.min(minSegment * 1.2, 14 * scale))
        const rounded = roundOrthogonalCorners(simplified, cornerRadius, minSegment)
        points = []
        rounded.forEach(point => pushPoint(points, point.x, point.y))
      }

      const baseStroke = resolveLinkPurposeColor(link.purpose)
      const debugStroke = (() => {
        if (!debugOn) return baseStroke
        if (!isL1) return DEBUG_STROKE_L2
        const minDiagonal = Math.max(12, minSegment * 2)
        if (hasSignificantDiagonal(points, minDiagonal)) return DEBUG_STROKE_L1_DIAGONAL
        return baseStroke
      })()

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
