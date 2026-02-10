import type { Rect, RenderLink, RenderTuning, LinkMeta, AreaRectEntry, DeviceRectEntry } from './linkRoutingTypes'
import {
  clamp,
  computeSide,
  offsetFromAnchor,
  segmentIntersectsRect,
} from './linkRoutingUtils'
import { resolveLinkPurposeColor } from '../../composables/canvasConstants'
import { connectOrthogonal } from '../../utils/link_routing'

export type RouteLinksParams = {
  isL1View: boolean
  scale: number
  clearance: number
  areaRects: AreaRectEntry[]
  deviceRects: DeviceRectEntry[]
  renderTuning: RenderTuning
  linkBundleIndex: Map<string, { index: number; total: number }>
}

const LABEL_STUB_PADDING = 4
const FAN_SPREAD_BASE = 18
const GLOBAL_LANE_BUCKET_FACTOR = 1.15
const GLOBAL_LANE_GAP_X_FACTOR = 0.56
const GLOBAL_LANE_GAP_Y_FACTOR = 0.86
const GLOBAL_LANE_LIMIT_X = 44
const GLOBAL_LANE_LIMIT_Y = 56

type PeerPurposeKind = 'stack' | 'ha' | 'hsrp'

type ExitSide = 'left' | 'right' | 'top' | 'bottom'

type LinkEndpoint = 'from' | 'to'

type Point = { x: number; y: number }

type FanRank = { index: number; total: number }

const PEER_PURPOSE_VISUAL: Record<PeerPurposeKind, { stroke: string; dash: number[]; strokeWidth: number; opacity: number }> = {
  stack: { stroke: '#2d8cf0', dash: [], strokeWidth: 2, opacity: 0.98 },
  ha: { stroke: '#16a085', dash: [8, 5], strokeWidth: 1.9, opacity: 0.98 },
  hsrp: { stroke: '#9b59b6', dash: [3, 4], strokeWidth: 1.8, opacity: 0.96 },
}

// --- Fan ranking: group links by device+side, assign rank by position ---

function fanAxisOrder(anchor: { x: number; y: number; side: ExitSide }) {
  return (anchor.side === 'top' || anchor.side === 'bottom') ? anchor.x : anchor.y
}

function fanGroupKey(deviceId: string, side: ExitSide) {
  return `${deviceId}|${side}`
}

function fanEndpointKey(linkId: string, endpoint: LinkEndpoint) {
  return `${linkId}:${endpoint}`
}

function resolveFanDistance(rank: FanRank | undefined, spread: number) {
  if (!rank || rank.total <= 1) return 0
  return clamp(rank.index / (rank.total - 1), 0, 1) * spread
}

function resolveFanCenteredRank(rank: FanRank | undefined) {
  if (!rank || rank.total <= 1) return 0
  return rank.index - (rank.total - 1) / 2
}

function buildAreaPairKey(a: string, b: string) {
  return a < b ? `${a}|${b}` : `${b}|${a}`
}

function resolveLaneScopeKey(fromAreaId?: string, toAreaId?: string) {
  if (!fromAreaId && !toAreaId) return 'global'
  if (!fromAreaId || !toAreaId) return `edge:${fromAreaId || toAreaId}`
  if (fromAreaId === toAreaId) return `intra:${fromAreaId}`
  return `inter:${buildAreaPairKey(fromAreaId, toAreaId)}`
}

function buildGlobalLaneRanks(
  linkMetas: Array<LinkMeta | null>,
  resolvedAnchorsByLink: Map<string, {
    fromAnchor: { x: number; y: number; side: ExitSide }
    toAnchor: { x: number; y: number; side: ExitSide }
  }>,
  bucketSize: number,
) {
  const laneXGroups = new Map<string, Array<{ linkId: string; order: number }>>()
  const laneYGroups = new Map<string, Array<{ linkId: string; order: number }>>()

  linkMetas.forEach(meta => {
    if (!meta) return
    const anchors = resolvedAnchorsByLink.get(meta.link.id)
    if (!anchors) return

    const scope = resolveLaneScopeKey(meta.fromAreaId || undefined, meta.toAreaId || undefined)
    const corridorX = (anchors.fromAnchor.x + anchors.toAnchor.x) / 2
    const corridorY = (anchors.fromAnchor.y + anchors.toAnchor.y) / 2
    const orderX = (anchors.fromAnchor.x + anchors.toAnchor.x) / 2
    const orderY = (anchors.fromAnchor.y + anchors.toAnchor.y) / 2

    const keyX = `${scope}|x|${Math.round(corridorX / bucketSize)}`
    const keyY = `${scope}|y|${Math.round(corridorY / bucketSize)}`

    const xList = laneXGroups.get(keyX) || []
    xList.push({ linkId: meta.link.id, order: orderY })
    laneXGroups.set(keyX, xList)

    const yList = laneYGroups.get(keyY) || []
    yList.push({ linkId: meta.link.id, order: orderX })
    laneYGroups.set(keyY, yList)
  })

  const toRankMap = (groups: Map<string, Array<{ linkId: string; order: number }>>) => {
    const rankMap = new Map<string, FanRank>()
    groups.forEach(entries => {
      entries.sort((a, b) => a.order - b.order || a.linkId.localeCompare(b.linkId))
      const total = entries.length
      entries.forEach((entry, index) => {
        rankMap.set(entry.linkId, { index, total })
      })
    })
    return rankMap
  }

  return {
    globalLaneRankXByLink: toRankMap(laneXGroups),
    globalLaneRankYByLink: toRankMap(laneYGroups),
  }
}

function resolveGlobalLaneOffset(
  rank: FanRank | undefined,
  axis: 'x' | 'y',
  scale: number,
  renderTuning: RenderTuning
) {
  const centered = resolveFanCenteredRank(rank)
  if (!centered) return 0
  const densityBoost = rank && rank.total > 5
    ? Math.min(1.6, 1 + (rank.total - 5) * 0.07)
    : 1
  const baseGap = Math.max(3.5, (renderTuning.bundle_gap ?? 0) * scale)
  const axisGap = axis === 'x'
    ? Math.max(5, baseGap * GLOBAL_LANE_GAP_X_FACTOR * densityBoost)
    : Math.max(6, baseGap * GLOBAL_LANE_GAP_Y_FACTOR * densityBoost)
  const baseLimit = axis === 'x' ? GLOBAL_LANE_LIMIT_X : GLOBAL_LANE_LIMIT_Y
  const limit = Math.max(axis === 'x' ? 16 : 20, baseLimit * scale)
  return clamp(centered * axisGap, -limit, limit)
}

// --- Peer purpose detection ---

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

// --- Path helpers ---

function simplifyPath(path: Point[]) {
  if (path.length <= 2) return path
  const eps = 0.5
  const out: Point[] = []

  path.forEach(point => {
    const last = out[out.length - 1]
    if (last && Math.abs(last.x - point.x) <= eps && Math.abs(last.y - point.y) <= eps) return
    out.push(point)

    while (out.length >= 3) {
      const a = out[out.length - 3]
      const b = out[out.length - 2]
      const c = out[out.length - 1]
      const colX = Math.abs(a.x - b.x) <= eps && Math.abs(b.x - c.x) <= eps
      const colY = Math.abs(a.y - b.y) <= eps && Math.abs(b.y - c.y) <= eps
      if (!colX && !colY) break
      out.splice(out.length - 2, 1)
    }
  })

  return out
}

function toPointsArray(path: Point[]) {
  const points: number[] = []
  path.forEach(point => {
    const lastX = points[points.length - 2]
    const lastY = points[points.length - 1]
    if (lastX === point.x && lastY === point.y) return
    points.push(point.x, point.y)
  })
  return points
}

function toPathArray(points: number[]) {
  const path: Point[] = []
  for (let i = 0; i + 1 < points.length; i += 2) {
    path.push({ x: points[i], y: points[i + 1] })
  }
  return path
}

function buildOrthShiftPath(from: Point, to: Point, preferAxis: 'x' | 'y'): Point[] {
  if (Math.abs(from.x - to.x) < 0.5 && Math.abs(from.y - to.y) < 0.5) return []
  const corner = preferAxis === 'x'
    ? { x: from.x, y: to.y }
    : { x: to.x, y: from.y }
  return simplifyPath([from, corner, to]).slice(1)
}

function pathBlocked(path: Point[], obstacles: Rect[], clearance: number) {
  for (let i = 1; i < path.length; i += 1) {
    const a = path[i - 1]
    const b = path[i]
    if (obstacles.some(rect => segmentIntersectsRect(a, b, rect, clearance))) return true
  }
  return false
}

function pathCrossesObjects(path: Point[], obstacles: Rect[]) {
  // Hard collision only: chỉ tính xuyên thân object, không tính vùng đệm clearance.
  return pathBlocked(path, obstacles, 0)
}

// --- Routing strategies ---

function findUShapePath(start: Point, end: Point, obstacles: Rect[], clearance: number, preferAxis: 'x' | 'y'): Point[] | null {
  if (!obstacles.length) return null
  const pad = Math.max(clearance, 8)
  const minX = Math.min(start.x, end.x) - pad
  const maxX = Math.max(start.x, end.x) + pad
  const minY = Math.min(start.y, end.y) - pad
  const maxY = Math.max(start.y, end.y) + pad
  const relevant = obstacles.filter(r =>
    r.x < maxX && r.x + r.width > minX && r.y < maxY && r.y + r.height > minY
  )
  if (!relevant.length) return null

  if (preferAxis === 'x') {
    let topEdge = Infinity, bottomEdge = -Infinity
    for (const r of relevant) {
      topEdge = Math.min(topEdge, r.y)
      bottomEdge = Math.max(bottomEdge, r.y + r.height)
    }
    const midY = (start.y + end.y) / 2
    const aboveY = topEdge - pad
    const belowY = bottomEdge + pad
    const sorted = Math.abs(aboveY - midY) <= Math.abs(belowY - midY) ? [aboveY, belowY] : [belowY, aboveY]
    for (const y of sorted) {
      const path = simplifyPath([start, { x: start.x, y }, { x: end.x, y }, end])
      if (!pathBlocked(path, obstacles, clearance)) return path
    }
  } else {
    let leftEdge = Infinity, rightEdge = -Infinity
    for (const r of relevant) {
      leftEdge = Math.min(leftEdge, r.x)
      rightEdge = Math.max(rightEdge, r.x + r.width)
    }
    const midX = (start.x + end.x) / 2
    const leftX = leftEdge - pad
    const rightX = rightEdge + pad
    const sorted = Math.abs(leftX - midX) <= Math.abs(rightX - midX) ? [leftX, rightX] : [rightX, leftX]
    for (const x of sorted) {
      const path = simplifyPath([start, { x, y: start.y }, { x, y: end.y }, end])
      if (!pathBlocked(path, obstacles, clearance)) return path
    }
  }
  return null
}

function buildBoundaryEscapePath(
  start: Point,
  end: Point,
  obstacles: Rect[],
  clearance: number,
  preferAxis: 'x' | 'y'
) {
  if (!obstacles.length) return null
  const windowPad = Math.max(clearance * 12, 180)
  const focusMinX = Math.min(start.x, end.x) - windowPad
  const focusMaxX = Math.max(start.x, end.x) + windowPad
  const focusMinY = Math.min(start.y, end.y) - windowPad
  const focusMaxY = Math.max(start.y, end.y) + windowPad
  const localObstacles = obstacles.filter(rect =>
    rect.x < focusMaxX && rect.x + rect.width > focusMinX &&
    rect.y < focusMaxY && rect.y + rect.height > focusMinY
  )
  const activeObstacles = localObstacles.length ? localObstacles : obstacles
  let minX = Math.min(start.x, end.x)
  let maxX = Math.max(start.x, end.x)
  let minY = Math.min(start.y, end.y)
  let maxY = Math.max(start.y, end.y)
  activeObstacles.forEach(rect => {
    minX = Math.min(minX, rect.x)
    maxX = Math.max(maxX, rect.x + rect.width)
    minY = Math.min(minY, rect.y)
    maxY = Math.max(maxY, rect.y + rect.height)
  })
  const basePad = Math.max(clearance, 12)
  const multipliers = [1, 1.5, 2, 3]
  for (const m of multipliers) {
    const pad = basePad * m
    const topY = minY - pad
    const bottomY = maxY + pad
    const leftX = minX - pad
    const rightX = maxX + pad
    const candidates = preferAxis === 'x'
      ? [
          simplifyPath([start, { x: start.x, y: topY }, { x: end.x, y: topY }, end]),
          simplifyPath([start, { x: start.x, y: bottomY }, { x: end.x, y: bottomY }, end]),
          simplifyPath([start, { x: leftX, y: start.y }, { x: leftX, y: end.y }, end]),
          simplifyPath([start, { x: rightX, y: start.y }, { x: rightX, y: end.y }, end]),
        ]
      : [
          simplifyPath([start, { x: leftX, y: start.y }, { x: leftX, y: end.y }, end]),
          simplifyPath([start, { x: rightX, y: start.y }, { x: rightX, y: end.y }, end]),
          simplifyPath([start, { x: start.x, y: topY }, { x: end.x, y: topY }, end]),
          simplifyPath([start, { x: start.x, y: bottomY }, { x: end.x, y: bottomY }, end]),
        ]
    for (const candidate of candidates) {
      if (!pathBlocked(candidate, obstacles, clearance)) return candidate
    }
  }
  return null
}

// Pipeline: connectOrthogonal → L-shapes → U-shape → per-obstacle → boundary escape → forced L-shape
// Luôn trả path (không bao giờ null/diagonal).
function buildOrthPath(start: Point, end: Point, obstacles: Rect[], clearance: number, preferAxis: 'x' | 'y') {
  // 1. connectOrthogonal (2 L-shapes with obstacle check)
  const orth = connectOrthogonal(start, end, obstacles, clearance, preferAxis)
  if (orth && orth.length >= 2) {
    const candidate = simplifyPath(orth)
    if (!pathBlocked(candidate, obstacles, clearance)) return candidate
  }

  // 2. L-shape preferred axis
  const midpoint = preferAxis === 'x'
    ? { x: end.x, y: start.y }
    : { x: start.x, y: end.y }
  const fallback = simplifyPath([start, midpoint, end])
  if (!pathBlocked(fallback, obstacles, clearance)) return fallback

  // 3. L-shape alternate axis
  const altMid = preferAxis === 'x'
    ? { x: start.x, y: end.y }
    : { x: end.x, y: start.y }
  const alt = simplifyPath([start, altMid, end])
  if (!pathBlocked(alt, obstacles, clearance)) return alt

  // 4. U-shape (bounding box of relevant obstacles)
  const uPath = findUShapePath(start, end, obstacles, clearance, preferAxis)
  if (uPath) return uPath
  const uPathAlt = findUShapePath(start, end, obstacles, clearance, preferAxis === 'x' ? 'y' : 'x')
  if (uPathAlt) return uPathAlt

  // 5. Per-obstacle avoidance (4 directions around each blocking obstacle)
  const avoidGap = Math.max(clearance, 12)
  for (const obs of obstacles) {
    if (!segmentIntersectsRect(start, end, obs, clearance)) continue
    for (const p of [
      simplifyPath([start, { x: obs.x + obs.width + avoidGap, y: start.y }, { x: obs.x + obs.width + avoidGap, y: end.y }, end]),
      simplifyPath([start, { x: obs.x - avoidGap, y: start.y }, { x: obs.x - avoidGap, y: end.y }, end]),
      simplifyPath([start, { x: start.x, y: obs.y + obs.height + avoidGap }, { x: end.x, y: obs.y + obs.height + avoidGap }, end]),
      simplifyPath([start, { x: start.x, y: obs.y - avoidGap }, { x: end.x, y: obs.y - avoidGap }, end]),
    ]) {
      if (!pathBlocked(p, obstacles, clearance)) return p
    }
  }

  // 6. Boundary escape (increasing padding around obstacle bounds)
  const escaped = buildBoundaryEscapePath(start, end, obstacles, clearance, preferAxis)
  if (escaped) return escaped

  // 7. Forced orthogonal (never diagonal, never null)
  return simplifyPath([start, midpoint, end])
}

// --- Peer lane ---

function resolvePeerLaneY(
  fromSide: ExitSide,
  toSide: ExitSide,
  fromBase: Point,
  toBase: Point,
  fromCenter: Point,
  toCenter: Point,
  purpose: PeerPurposeKind,
  scale: number,
) {
  const laneOffset = purpose === 'stack' ? -10 * scale : purpose === 'ha' ? 0 : 10 * scale
  const laneGap = Math.max(12 * scale, 28 * scale)

  if (fromSide === 'bottom' && toSide === 'bottom') {
    return Math.max(fromBase.y, toBase.y) + laneGap + laneOffset
  }
  if (fromSide === 'top' && toSide === 'top') {
    return Math.min(fromBase.y, toBase.y) - laneGap + laneOffset
  }

  return (fromCenter.y + toCenter.y) / 2 + laneOffset
}

// --- Post-processing: tách segment song song chồng nhau ---

type SegInfo = {
  linkIdx: number
  ptIdx: number      // index trong flat points[] (x của điểm đầu segment)
  coord: number      // x cho vertical, y cho horizontal
  rangeMin: number
  rangeMax: number
}

function nudgeOverlappingSegments(links: RenderLink[], scale: number) {
  if (links.length < 2) return

  const nudgeGap = Math.max(7, 9 * scale)
  const coordThreshold = Math.max(5, 7 * scale)
  const minSegLen = 10
  const eps = 0.5
  const skipSegs = 2 // giữ ổn định đoạn gần port, chỉ nudge corridor giữa
  const maxOffset = Math.max(22, 28 * scale)

  const verticals: SegInfo[] = []
  const horizontals: SegInfo[] = []

  links.forEach((link, linkIdx) => {
    const pts = link.points
    const minIdx = skipSegs * 2
    const maxIdx = pts.length - (skipSegs + 1) * 2
    if (minIdx >= maxIdx) return

    for (let i = minIdx; i < maxIdx; i += 2) {
      const x1 = pts[i], y1 = pts[i + 1]
      const x2 = pts[i + 2], y2 = pts[i + 3]

      if (Math.abs(x1 - x2) < eps && Math.abs(y1 - y2) > minSegLen) {
        verticals.push({ linkIdx, ptIdx: i, coord: (x1 + x2) / 2, rangeMin: Math.min(y1, y2), rangeMax: Math.max(y1, y2) })
      } else if (Math.abs(y1 - y2) < eps && Math.abs(x1 - x2) > minSegLen) {
        horizontals.push({ linkIdx, ptIdx: i, coord: (y1 + y2) / 2, rangeMin: Math.min(x1, x2), rangeMax: Math.max(x1, x2) })
      }
    }
  })

  function applyNudge(segs: SegInfo[], isVertical: boolean) {
    if (segs.length < 2) return
    segs.sort((a, b) => a.coord - b.coord)

    const used = new Uint8Array(segs.length)

    for (let i = 0; i < segs.length; i++) {
      if (used[i]) continue
      const group = [segs[i]]
      used[i] = 1

      for (let j = i + 1; j < segs.length; j++) {
        if (used[j]) continue
        if (segs[j].coord - segs[i].coord > coordThreshold * 3) break
        const sj = segs[j]
        if (group.some(g =>
          Math.abs(g.coord - sj.coord) <= coordThreshold &&
          Math.max(g.rangeMin, sj.rangeMin) < Math.min(g.rangeMax, sj.rangeMax)
        )) {
          group.push(sj)
          used[j] = 1
        }
      }

      // Chỉ nudge khi có >= 2 link khác nhau
      const uniqueLinks = new Set(group.map(s => s.linkIdx))
      if (uniqueLinks.size < 2 || group.length < 2) continue

      group.forEach((seg, rank) => {
        const rawOffset = (rank - (group.length - 1) / 2) * nudgeGap
        const offset = clamp(rawOffset, -maxOffset, maxOffset)
        if (Math.abs(offset) < 0.3) return

        const pts = links[seg.linkIdx].points
        if (isVertical) {
          pts[seg.ptIdx] += offset
          pts[seg.ptIdx + 2] += offset
        } else {
          pts[seg.ptIdx + 1] += offset
          pts[seg.ptIdx + 3] += offset
        }
      })
    }
  }

  applyNudge(verticals, true)
  applyNudge(horizontals, false)
}

// --- Main ---

export function routeLinks(
  linkMetas: Array<LinkMeta | null>,
  ctx: RouteLinksParams
) {
  const {
    isL1View,
    scale,
    clearance: rawClearance,
    renderTuning,
    areaRects,
    deviceRects,
    linkBundleIndex,
  } = ctx
  const clearance = Math.max(rawClearance, 2)

  // --- Pre-pass: resolve anchors + build fan rank (1 hệ thống duy nhất) ---
  const resolvedAnchorsByLink = new Map<string, {
    fromAnchor: { x: number; y: number; side: ExitSide }
    toAnchor: { x: number; y: number; side: ExitSide }
  }>()
  const fanGroups = new Map<string, Array<{
    linkId: string
    endpoint: LinkEndpoint
    order: number
  }>>()

  linkMetas.forEach(meta => {
    if (!meta) return
    const fromAnchor = { ...meta.fromAnchor, side: (meta.fromAnchor.side || computeSide(meta.fromView, meta.toCenter)) as ExitSide }
    const toAnchor = { ...meta.toAnchor, side: (meta.toAnchor.side || computeSide(meta.toView, meta.fromCenter)) as ExitSide }
    resolvedAnchorsByLink.set(meta.link.id, { fromAnchor, toAnchor })

    const pushFan = (deviceId: string, side: ExitSide, linkId: string, endpoint: LinkEndpoint, order: number) => {
      const key = fanGroupKey(deviceId, side)
      const list = fanGroups.get(key) || []
      list.push({ linkId, endpoint, order })
      fanGroups.set(key, list)
    }
    pushFan(meta.link.fromDeviceId, fromAnchor.side, meta.link.id, 'from', fanAxisOrder(fromAnchor))
    pushFan(meta.link.toDeviceId, toAnchor.side, meta.link.id, 'to', fanAxisOrder(toAnchor))
  })

  const fanRankByEndpoint = new Map<string, FanRank>()
  fanGroups.forEach(entries => {
    entries.sort((a, b) => a.order - b.order || a.linkId.localeCompare(b.linkId) || a.endpoint.localeCompare(b.endpoint))
    const total = entries.length
    entries.forEach((entry, index) => {
      fanRankByEndpoint.set(fanEndpointKey(entry.linkId, entry.endpoint), { index, total })
    })
  })

  // Global corridor split: tách làn toàn cục theo cả X và Y để giảm dính bó ngang/dọc.
  const globalLaneBucket = Math.max(12, (renderTuning.bundle_gap ?? 0) * scale * GLOBAL_LANE_BUCKET_FACTOR)
  const {
    globalLaneRankXByLink,
    globalLaneRankYByLink,
  } = buildGlobalLaneRanks(linkMetas, resolvedAnchorsByLink, globalLaneBucket)

  // --- Per-link routing ---
  const obstaclesByLink = new Map<string, Rect[]>()
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
      } = meta

      const resolvedAnchors = resolvedAnchorsByLink.get(link.id)
      const fromAnchor = resolvedAnchors
        ? { ...resolvedAnchors.fromAnchor }
        : { ...meta.fromAnchor, side: (meta.fromAnchor.side || computeSide(fromView, toCenter)) as ExitSide }
      const toAnchor = resolvedAnchors
        ? { ...resolvedAnchors.toAnchor }
        : { ...meta.toAnchor, side: (meta.toAnchor.side || computeSide(toView, fromCenter)) as ExitSide }

      const purpose = (link.purpose || '').trim().toUpperCase()
      const peerPurpose = resolvePeerPurposeKind(purpose, link.fromPort, link.toPort)
      const isIntraArea = !!(fromAreaId && toAreaId && fromAreaId === toAreaId)
      const isInterArea = !!(fromAreaId && toAreaId && fromAreaId !== toAreaId)

      // --- Stub distance + fan (tách link adjacent ports) ---
      const labelScale = clamp(scale, 0.6, 1.15)
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

      const baseStub = Math.max(renderTuning.bundle_stub ?? 0, renderTuning.area_clearance ?? 0) * scale
      const fanSpread = FAN_SPREAD_BASE * scale
      const fromFanRank = fanRankByEndpoint.get(fanEndpointKey(link.id, 'from'))
      const toFanRank = fanRankByEndpoint.get(fanEndpointKey(link.id, 'to'))
      const fromFan = resolveFanDistance(fromFanRank, fanSpread)
      const toFan = resolveFanDistance(toFanRank, fanSpread)
      const fromStubDistance = Math.max(baseStub, fromLabelStub, minPortTurnDistance) + fromFan
      const toStubDistance = Math.max(baseStub, toLabelStub, minPortTurnDistance) + toFan
      // fromStub = cuối đoạn stub thẳng (cùng trục với anchor)
      const fromStub = offsetFromAnchor(fromAnchor, fromStubDistance)
      const toStub = offsetFromAnchor(toAnchor, toStubDistance)

      // Stem jog: tách link cùng port bằng offset vuông góc với stub
      // anchor → stub (thẳng) → base (jog ngang/dọc) → shifted (bundle) → routing
      const stemGap = Math.max(3, 4.5 * scale)
      const fromStem = fromFanRank && fromFanRank.total > 1
        ? (fromFanRank.index - (fromFanRank.total - 1) / 2) * stemGap
        : 0
      const toStem = toFanRank && toFanRank.total > 1
        ? (toFanRank.index - (toFanRank.total - 1) / 2) * stemGap
        : 0
      const fromBase: Point = (fromAnchor.side === 'bottom' || fromAnchor.side === 'top')
        ? { x: fromStub.x + fromStem, y: fromStub.y }
        : { x: fromStub.x, y: fromStub.y + fromStem }
      const toBase: Point = (toAnchor.side === 'bottom' || toAnchor.side === 'top')
        ? { x: toStub.x + toStem, y: toStub.y }
        : { x: toStub.x, y: toStub.y + toStem }

      // --- Obstacles (self device inset) ---
      const selfInset = Math.max(clearance + 1, 4)
      const obstacles: Rect[] = []
      deviceRects.forEach(({ id, rect }) => {
        if (id === link.fromDeviceId || id === link.toDeviceId) {
          if (rect.width > selfInset * 2 && rect.height > selfInset * 2) {
            obstacles.push({
              x: rect.x + selfInset,
              y: rect.y + selfInset,
              width: rect.width - selfInset * 2,
              height: rect.height - selfInset * 2,
            })
          }
          return
        }
        obstacles.push(rect)
      })
      if (isInterArea) {
        areaRects.forEach(({ id, rect }) => {
          if (id === fromAreaId || id === toAreaId) return
          obstacles.push(rect)
        })
      }
      obstaclesByLink.set(link.id, obstacles)

      // --- Bundle offset (cùng cặp device → tách đường) ---
      const preferAxis: 'x' | 'y' = Math.abs(toCenter.x - fromCenter.x) >= Math.abs(toCenter.y - fromCenter.y) ? 'x' : 'y'
      const bundle = linkBundleIndex.get(link.id)
      const bundleGap = Math.max(8, (renderTuning.bundle_gap ?? 0) * scale * 0.9)
      const pairBundleOffset = bundle && bundle.total > 1
        ? (bundle.index - (bundle.total - 1) / 2) * bundleGap
        : 0
      const pairBundleOffsetX = preferAxis === 'y' ? pairBundleOffset : 0
      const pairBundleOffsetY = preferAxis === 'x' ? pairBundleOffset : 0
      const globalLaneOffsetX = isL1View
        ? resolveGlobalLaneOffset(globalLaneRankXByLink.get(link.id), 'y', scale, renderTuning)
        : 0
      const globalLaneOffsetY = isL1View
        ? resolveGlobalLaneOffset(globalLaneRankYByLink.get(link.id), 'x', scale, renderTuning)
        : 0

      const bundleLimitX = Math.max(18, GLOBAL_LANE_LIMIT_X * scale)
      const bundleLimitY = Math.max(20, GLOBAL_LANE_LIMIT_Y * scale)
      const bundleOffsetX = clamp(pairBundleOffsetX + globalLaneOffsetX, -bundleLimitX, bundleLimitX)
      const bundleOffsetY = clamp(pairBundleOffsetY + globalLaneOffsetY, -bundleLimitY, bundleLimitY)

      const fromShifted: Point = { x: fromBase.x + bundleOffsetX, y: fromBase.y + bundleOffsetY }
      const toShifted: Point = { x: toBase.x + bundleOffsetX, y: toBase.y + bundleOffsetY }
      const fromShiftPath = buildOrthShiftPath(fromBase, fromShifted, preferAxis)
      const toShiftPath = buildOrthShiftPath(toShifted, toBase, preferAxis)

      // --- Route: mọi nhánh đều dùng shifted points (giữ spacing đồng nhất) ---
      let path: Point[] = []

      // 1. Peer purpose (intra-area HA/stack/hsrp)
      if (isL1View && peerPurpose && isIntraArea) {
        const laneY = resolvePeerLaneY(
          fromAnchor.side as ExitSide, toAnchor.side as ExitSide,
          fromShifted, toShifted, fromCenter, toCenter, peerPurpose, scale
        )
        const peerPath = simplifyPath([
          { x: fromAnchor.x, y: fromAnchor.y },
          { x: fromStub.x, y: fromStub.y },
          { x: fromBase.x, y: fromBase.y },
          ...fromShiftPath,
          { x: fromShifted.x, y: laneY },
          { x: toShifted.x, y: laneY },
          ...toShiftPath,
          { x: toStub.x, y: toStub.y },
          { x: toAnchor.x, y: toAnchor.y },
        ])
        if (!pathBlocked(peerPath, obstacles, clearance)) path = peerPath
      }

      // 2. General orthogonal routing (with bundle offset)
      if (!path.length) {
        const orth = buildOrthPath(fromShifted, toShifted, obstacles, clearance, preferAxis)
        path = simplifyPath([
          { x: fromAnchor.x, y: fromAnchor.y },
          { x: fromStub.x, y: fromStub.y },
          { x: fromBase.x, y: fromBase.y },
          ...fromShiftPath,
          ...orth,
          ...toShiftPath,
          { x: toStub.x, y: toStub.y },
          { x: toAnchor.x, y: toAnchor.y },
        ])
      }

      // 3. Fallback alternate axis (vẫn giữ fromBase/toBase → giữ fan spacing)
      if (pathBlocked(path, obstacles, clearance)) {
        const fallback = buildOrthPath(
          { x: fromBase.x, y: fromBase.y },
          { x: toBase.x, y: toBase.y },
          obstacles, clearance,
          preferAxis === 'x' ? 'y' : 'x'
        )
        path = simplifyPath([
          { x: fromAnchor.x, y: fromAnchor.y },
          { x: fromStub.x, y: fromStub.y },
          { x: fromBase.x, y: fromBase.y },
          ...fallback,
          { x: toBase.x, y: toBase.y },
          { x: toStub.x, y: toStub.y },
          { x: toAnchor.x, y: toAnchor.y },
        ])
      }

      // Chốt an toàn trước render: chỉ loại path xuyên thân object thật.
      if (pathCrossesObjects(path, obstacles)) return null

      // --- Render ---
      const points = toPointsArray(path)
      if (points.length < 4) return null
      const neutralL1Purposes = new Set(['', 'DEFAULT', 'LAN'])
      const purposeStroke = resolveLinkPurposeColor(link.purpose)
      const peerVisual = peerPurpose ? PEER_PURPOSE_VISUAL[peerPurpose] : null
      const stroke = peerVisual
        ? peerVisual.stroke
        : ((isL1View && neutralL1Purposes.has(purpose)) ? '#2b2a28' : purposeStroke)
      const dash = peerVisual
        ? peerVisual.dash
        : (link.style === 'dashed' ? [8, 6] : link.style === 'dotted' ? [2, 4] : [])
      const strokeWidth = peerVisual
        ? peerVisual.strokeWidth
        : (isL1View ? 1.35 : 1.5)
      const opacity = peerVisual
        ? peerVisual.opacity
        : (isL1View ? 0.92 : 0.8)

      return {
        id: link.id,
        fromAnchor,
        toAnchor,
        fromCenter,
        toCenter,
        points,
        config: {
          points,
          stroke,
          strokeWidth,
          lineCap: isL1View ? 'butt' : 'round',
          lineJoin: isL1View ? 'miter' : 'round',
          dash,
          opacity,
        }
      } as RenderLink
    })
    .filter(Boolean) as RenderLink[]

  // Post-processing: tách segment song song chồng nhau giữa các link khác nhau
  const pointsBeforeNudge = new Map<string, number[]>()
  links.forEach(link => {
    pointsBeforeNudge.set(link.id, [...link.points])
  })
  nudgeOverlappingSegments(links, scale)

  // Nudge có thể đẩy segment vào vật cản -> rollback link đó về path trước nudge.
  links.forEach(link => {
    const obstacles = obstaclesByLink.get(link.id)
    if (!obstacles || !obstacles.length) return
    if (!pathCrossesObjects(toPathArray(link.points), obstacles)) return
    const original = pointsBeforeNudge.get(link.id)
    if (!original) return
    link.points = [...original]
  })
  links.forEach(link => {
    link.config.points = link.points
  })

  const cache = new Map<string, {
    points: number[]
    fromAnchor: { x: number; y: number; side?: string }
    toAnchor: { x: number; y: number; side?: string }
    fromCenter: { x: number; y: number }
    toCenter: { x: number; y: number }
  }>()

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
