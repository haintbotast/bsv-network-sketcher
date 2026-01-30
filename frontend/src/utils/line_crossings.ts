/**
 * Phát hiện giao điểm giữa các đường link (orthogonal segments)
 * và cung cấp thông tin để vẽ arc jump tại điểm giao.
 */

export interface Crossing {
  x: number
  y: number
  segmentIndex: number
  distAlongSeg: number
}

export interface LinkForCrossing {
  id: string
  points: number[]  // flat [x1,y1, x2,y2, ...]
}

const EPS = 1.0  // epsilon loại trừ giao điểm quá gần endpoint

/**
 * Tìm giao điểm 2 đoạn thẳng orthogonal.
 * Trả về null nếu không giao hoặc giao tại endpoint/T-junction.
 */
function segmentIntersection(
  ax1: number, ay1: number, ax2: number, ay2: number,
  bx1: number, by1: number, bx2: number, by2: number,
): { x: number; y: number } | null {
  const aHoriz = Math.abs(ay2 - ay1) < 0.5
  const bHoriz = Math.abs(by2 - by1) < 0.5
  const aVert = Math.abs(ax2 - ax1) < 0.5
  const bVert = Math.abs(bx2 - bx1) < 0.5

  // Cần 1 ngang + 1 dọc
  let hx1: number, hx2: number, hy: number
  let vx: number, vy1: number, vy2: number

  if (aHoriz && bVert) {
    hx1 = Math.min(ax1, ax2); hx2 = Math.max(ax1, ax2); hy = ay1
    vx = bx1; vy1 = Math.min(by1, by2); vy2 = Math.max(by1, by2)
  } else if (aVert && bHoriz) {
    hx1 = Math.min(bx1, bx2); hx2 = Math.max(bx1, bx2); hy = by1
    vx = ax1; vy1 = Math.min(ay1, ay2); vy2 = Math.max(ay1, ay2)
  } else {
    // Cả hai cùng hướng hoặc đường chéo → không xử lý
    return null
  }

  // Giao điểm tại (vx, hy)
  // Kiểm tra nằm trong range cả hai đoạn (loại trừ endpoint)
  if (vx > hx1 + EPS && vx < hx2 - EPS && hy > vy1 + EPS && hy < vy2 - EPS) {
    return { x: vx, y: hy }
  }
  return null
}

/**
 * Tính crossings cho tất cả links.
 * Link có index cao hơn (render sau) sẽ nhận jump arc.
 */
export function computeCrossings(links: LinkForCrossing[]): Map<string, Crossing[]> {
  const result = new Map<string, Crossing[]>()
  if (links.length < 2) return result

  // Extract segments cho mỗi link
  const allSegments: Array<{
    linkIdx: number
    segIdx: number
    x1: number; y1: number; x2: number; y2: number
  }> = []

  for (let li = 0; li < links.length; li++) {
    const pts = links[li].points
    for (let si = 0; si < pts.length / 2 - 1; si++) {
      allSegments.push({
        linkIdx: li,
        segIdx: si,
        x1: pts[si * 2], y1: pts[si * 2 + 1],
        x2: pts[(si + 1) * 2], y2: pts[(si + 1) * 2 + 1],
      })
    }
  }

  // Kiểm tra mọi cặp segments từ links khác nhau
  for (let i = 0; i < allSegments.length; i++) {
    for (let j = i + 1; j < allSegments.length; j++) {
      const a = allSegments[i]
      const b = allSegments[j]
      if (a.linkIdx === b.linkIdx) continue  // Bỏ qua self-crossing

      const pt = segmentIntersection(a.x1, a.y1, a.x2, a.y2, b.x1, b.y1, b.x2, b.y2)
      if (!pt) continue

      // Link có index CAO hơn nhận jump arc
      const jumpLink = a.linkIdx > b.linkIdx ? a : b
      const jumpLinkId = links[jumpLink.linkIdx].id

      const distAlongSeg = Math.hypot(pt.x - jumpLink.x1, pt.y - jumpLink.y1)

      if (!result.has(jumpLinkId)) {
        result.set(jumpLinkId, [])
      }
      result.get(jumpLinkId)!.push({
        x: pt.x,
        y: pt.y,
        segmentIndex: jumpLink.segIdx,
        distAlongSeg,
      })
    }
  }

  // Sort crossings theo segmentIndex rồi distAlongSeg
  for (const crossings of result.values()) {
    crossings.sort((a, b) => a.segmentIndex - b.segmentIndex || a.distAlongSeg - b.distAlongSeg)
  }

  return result
}

/**
 * Vẽ polyline với arc jump tại các giao điểm.
 * ctx là CanvasRenderingContext2D (Konva sceneFunc context).
 */
export function drawPolylineWithJumps(
  ctx: { moveTo: Function; lineTo: Function; arc: Function },
  points: number[],
  crossings: Crossing[],
  radius: number,
): void {
  if (points.length < 4) {
    if (points.length >= 2) ctx.moveTo(points[0], points[1])
    if (points.length >= 4) ctx.lineTo(points[2], points[3])
    return
  }

  ctx.moveTo(points[0], points[1])

  if (!crossings || crossings.length === 0) {
    // Không có crossing → vẽ thẳng
    for (let i = 2; i < points.length; i += 2) {
      ctx.lineTo(points[i], points[i + 1])
    }
    return
  }

  let crossIdx = 0
  const numSegs = points.length / 2 - 1

  for (let seg = 0; seg < numSegs; seg++) {
    const x1 = points[seg * 2]
    const y1 = points[seg * 2 + 1]
    const x2 = points[(seg + 1) * 2]
    const y2 = points[(seg + 1) * 2 + 1]

    // Thu thập crossings trên segment này
    const segCrossings: Crossing[] = []
    while (crossIdx < crossings.length && crossings[crossIdx].segmentIndex === seg) {
      segCrossings.push(crossings[crossIdx])
      crossIdx++
    }

    if (segCrossings.length === 0) {
      ctx.lineTo(x2, y2)
      continue
    }

    const isHorizontal = Math.abs(y2 - y1) < 0.5
    const segLen = Math.hypot(x2 - x1, y2 - y1)

    // Lọc crossings quá gần endpoint hoặc quá gần nhau
    const filtered: Crossing[] = []
    for (const c of segCrossings) {
      const dist = isHorizontal ? Math.abs(c.x - x1) : Math.abs(c.y - y1)
      const distEnd = isHorizontal ? Math.abs(c.x - x2) : Math.abs(c.y - y2)
      if (dist < radius + 1 || distEnd < radius + 1) continue  // Quá gần endpoint
      if (filtered.length > 0) {
        const prev = filtered[filtered.length - 1]
        const gap = Math.hypot(c.x - prev.x, c.y - prev.y)
        if (gap < radius * 2.5) continue  // Quá gần crossing trước
      }
      filtered.push(c)
    }

    if (filtered.length === 0) {
      ctx.lineTo(x2, y2)
      continue
    }

    if (isHorizontal) {
      const dir = x2 > x1 ? 1 : -1
      for (const c of filtered) {
        // Vẽ đến trước arc
        ctx.lineTo(c.x - dir * radius, c.y)
        // Semicircle nhảy lên (negative Y)
        const startAngle = dir > 0 ? Math.PI : 0
        const endAngle = dir > 0 ? 0 : Math.PI
        ctx.arc(c.x, c.y, radius, startAngle, endAngle, true)
      }
    } else {
      const dir = y2 > y1 ? 1 : -1
      for (const c of filtered) {
        // Vẽ đến trước arc
        ctx.lineTo(c.x, c.y - dir * radius)
        // Semicircle nhảy sang phải (positive X)
        const startAngle = dir > 0 ? -Math.PI / 2 : Math.PI / 2
        const endAngle = dir > 0 ? Math.PI / 2 : -Math.PI / 2
        ctx.arc(c.x, c.y, radius, startAngle, endAngle, true)
      }
    }

    // Kết thúc segment
    ctx.lineTo(x2, y2)
  }
}
