import type { Rect } from './linkRoutingTypes'

export function clamp(value: number, min: number, max: number) {
  if (Number.isNaN(value)) return min
  if (value < min) return min
  if (value > max) return max
  return value
}

export function comparePorts(a: string, b: string) {
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

export function extractPortIndex(portName?: string) {
  if (!portName) return null
  const match = portName.match(/(\d+)(?!.*\d)/)
  if (!match) return null
  return Number.parseInt(match[1], 10)
}

export function computePortAnchorFallback(
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

export function computeSide(rect: Rect, target: { x: number; y: number }) {
  const center = { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 }
  const dx = target.x - center.x
  const dy = target.y - center.y
  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx >= 0 ? 'right' : 'left'
  }
  return dy >= 0 ? 'bottom' : 'top'
}

export function computeSideFromVector(dx: number, dy: number) {
  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx >= 0 ? 'right' : 'left'
  }
  return dy >= 0 ? 'bottom' : 'top'
}

export function computePortLabelPlacement(
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

export function normalizeVector(dx: number, dy: number) {
  const len = Math.hypot(dx, dy)
  if (!len) return { x: 0, y: 0 }
  return { x: dx / len, y: dy / len }
}

export function offsetFromAnchor(anchor: { x: number; y: number; side?: string }, distance: number) {
  const side = anchor.side || 'right'
  if (side === 'left') return { x: anchor.x - distance, y: anchor.y }
  if (side === 'right') return { x: anchor.x + distance, y: anchor.y }
  if (side === 'top') return { x: anchor.x, y: anchor.y - distance }
  return { x: anchor.x, y: anchor.y + distance }
}

export function pointInRect(point: { x: number; y: number }, rect: Rect, margin = 0) {
  return (
    point.x >= rect.x - margin &&
    point.x <= rect.x + rect.width + margin &&
    point.y >= rect.y - margin &&
    point.y <= rect.y + rect.height + margin
  )
}

export function segmentIntersectsRect(
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

export function computeAreaAnchor(
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
    const baseY = clamp(fromPoint.y, areaRect.y + inset, areaRect.y + areaRect.height - inset)
    const y = baseY + shift
    return { x, y }
  }
  const y = dy >= 0 ? areaRect.y + areaRect.height + edgeOffset : areaRect.y - edgeOffset
  const baseX = clamp(fromPoint.x, areaRect.x + inset, areaRect.x + areaRect.width - inset)
  const x = baseX + shift
  return { x, y }
}
