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

type PeerPurposeKind = 'stack' | 'ha' | 'hsrp'

type ExitSide = 'left' | 'right' | 'top' | 'bottom'

type Point = { x: number; y: number }

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

function pathBlocked(path: Point[], obstacles: Rect[], clearance: number) {
  for (let i = 1; i < path.length; i += 1) {
    const a = path[i - 1]
    const b = path[i]
    if (obstacles.some(rect => segmentIntersectsRect(a, b, rect, clearance))) return true
  }
  return false
}

function buildOrthPath(start: Point, end: Point, obstacles: Rect[], clearance: number, preferAxis: 'x' | 'y') {
  const orth = connectOrthogonal(start, end, obstacles, clearance, preferAxis)
  if (orth && orth.length >= 2) {
    return simplifyPath(orth)
  }

  const midpoint = preferAxis === 'x'
    ? { x: end.x, y: start.y }
    : { x: start.x, y: end.y }
  const fallback = simplifyPath([start, midpoint, end])
  if (!pathBlocked(fallback, obstacles, clearance)) return fallback

  const altMid = preferAxis === 'x'
    ? { x: start.x, y: end.y }
    : { x: end.x, y: start.y }
  const alt = simplifyPath([start, altMid, end])
  if (!pathBlocked(alt, obstacles, clearance)) return alt

  return simplifyPath([start, end])
}

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

function buildInterAreaPath(
  fromAnchor: Point,
  toAnchor: Point,
  fromBase: Point,
  toBase: Point,
  fromCenter: Point,
  toCenter: Point,
  lane: { index: number; total: number } | undefined,
  laneGap: number,
  obstacles: Rect[],
  clearance: number,
) {
  const laneOffset = lane && lane.total > 1
    ? (lane.index - (lane.total - 1) / 2) * laneGap
    : 0

  const dx = toCenter.x - fromCenter.x
  const dy = toCenter.y - fromCenter.y
  const useVerticalCorridor = Math.abs(dx) >= Math.abs(dy)

  if (useVerticalCorridor) {
    const corridorX = (fromBase.x + toBase.x) / 2 + laneOffset
    const candidate = simplifyPath([
      fromAnchor,
      fromBase,
      { x: corridorX, y: fromBase.y },
      { x: corridorX, y: toBase.y },
      toBase,
      toAnchor,
    ])
    if (!pathBlocked(candidate, obstacles, clearance)) return candidate
    const orth = buildOrthPath(fromBase, toBase, obstacles, clearance, 'x')
    return simplifyPath([fromAnchor, fromBase, ...orth, toBase, toAnchor])
  }

  const corridorY = (fromBase.y + toBase.y) / 2 + laneOffset
  const candidate = simplifyPath([
    fromAnchor,
    fromBase,
    { x: fromBase.x, y: corridorY },
    { x: toBase.x, y: corridorY },
    toBase,
    toAnchor,
  ])
  if (!pathBlocked(candidate, obstacles, clearance)) return candidate
  const orth = buildOrthPath(fromBase, toBase, obstacles, clearance, 'y')
  return simplifyPath([fromAnchor, fromBase, ...orth, toBase, toAnchor])
}

export function routeLinks(
  linkMetas: Array<LinkMeta | null>,
  laneIndex: Map<string, { index: number; total: number }>,
  _labelObstacles: Array<{ linkId: string; rect: Rect }>,
  ctx: RouteLinksParams
) {
  const {
    isL1View,
    scale,
    clearance,
    renderTuning,
    areaRects,
    deviceRects,
    linkBundleIndex,
  } = ctx

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

      let fromAnchor = { ...meta.fromAnchor, side: (meta.fromAnchor.side || computeSide(fromView, toCenter)) as ExitSide }
      let toAnchor = { ...meta.toAnchor, side: (meta.toAnchor.side || computeSide(toView, fromCenter)) as ExitSide }

      const purpose = (link.purpose || '').trim().toUpperCase()
      const peerPurpose = resolvePeerPurposeKind(purpose, link.fromPort, link.toPort)
      const isIntraArea = !!(fromAreaId && toAreaId && fromAreaId === toAreaId)
      const isInterArea = !!(fromAreaId && toAreaId && fromAreaId !== toAreaId)

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
      const fromStubDistance = Math.max(baseStub, fromLabelStub, minPortTurnDistance)
      const toStubDistance = Math.max(baseStub, toLabelStub, minPortTurnDistance)
      const fromBase = offsetFromAnchor(fromAnchor, fromStubDistance)
      const toBase = offsetFromAnchor(toAnchor, toStubDistance)

      const obstacles: Rect[] = []
      deviceRects.forEach(({ id, rect }) => {
        if (id === link.fromDeviceId || id === link.toDeviceId) return
        obstacles.push(rect)
      })
      if (isInterArea) {
        areaRects.forEach(({ id, rect }) => {
          if (id === fromAreaId || id === toAreaId) return
          obstacles.push(rect)
        })
      }

      let path: Point[] = []

      if (isL1View && peerPurpose && isIntraArea) {
        const laneY = resolvePeerLaneY(fromAnchor.side as ExitSide, toAnchor.side as ExitSide, fromBase, toBase, fromCenter, toCenter, peerPurpose, scale)
        const peerPath = simplifyPath([
          { x: fromAnchor.x, y: fromAnchor.y },
          { x: fromBase.x, y: fromBase.y },
          { x: fromBase.x, y: laneY },
          { x: toBase.x, y: laneY },
          { x: toBase.x, y: toBase.y },
          { x: toAnchor.x, y: toAnchor.y },
        ])

        if (!pathBlocked(peerPath, obstacles, clearance)) {
          path = peerPath
        }
      }

      if (!path.length) {
        const preferAxis: 'x' | 'y' = Math.abs(toCenter.x - fromCenter.x) >= Math.abs(toCenter.y - fromCenter.y) ? 'x' : 'y'
        const bundle = linkBundleIndex.get(link.id)
        const bundleOffset = bundle && bundle.total > 1
          ? (bundle.index - (bundle.total - 1) / 2) * Math.max(4, (renderTuning.bundle_gap ?? 0) * scale * 0.45)
          : 0

        const fromShifted: Point = preferAxis === 'x'
          ? { x: fromBase.x, y: fromBase.y + bundleOffset }
          : { x: fromBase.x + bundleOffset, y: fromBase.y }
        const toShifted: Point = preferAxis === 'x'
          ? { x: toBase.x, y: toBase.y + bundleOffset }
          : { x: toBase.x + bundleOffset, y: toBase.y }

        if (isL1View && isInterArea) {
          const interLaneGap = Math.max(10, (renderTuning.bundle_gap ?? 0) * scale * 1.6)
          path = buildInterAreaPath(
            { x: fromAnchor.x, y: fromAnchor.y },
            { x: toAnchor.x, y: toAnchor.y },
            fromShifted,
            toShifted,
            fromCenter,
            toCenter,
            laneIndex.get(link.id),
            interLaneGap,
            obstacles,
            clearance,
          )
        } else {
          const orth = buildOrthPath(fromShifted, toShifted, obstacles, clearance, preferAxis)
          path = simplifyPath([
            { x: fromAnchor.x, y: fromAnchor.y },
            { x: fromBase.x, y: fromBase.y },
            ...orth,
            { x: toBase.x, y: toBase.y },
            { x: toAnchor.x, y: toAnchor.y },
          ])
        }

        if (pathBlocked(path, obstacles, clearance)) {
          const fallback = buildOrthPath({ x: fromBase.x, y: fromBase.y }, { x: toBase.x, y: toBase.y }, obstacles, clearance, preferAxis === 'x' ? 'y' : 'x')
          path = simplifyPath([
            { x: fromAnchor.x, y: fromAnchor.y },
            { x: fromBase.x, y: fromBase.y },
            ...fallback,
            { x: toBase.x, y: toBase.y },
            { x: toAnchor.x, y: toAnchor.y },
          ])
        }
      }

      const points = toPointsArray(path)
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
