export type Point = { x: number; y: number }
export type Rect = { x: number; y: number; width: number; height: number }

export type GridSpec = {
  originX: number
  originY: number
  size: number
  cols: number
  rows: number
}

export type GridPoint = { gx: number; gy: number }

export type RouteOptions = {
  start: Point
  end: Point
  obstacles: Rect[]
  clearance: number
  grid: GridSpec
  occupancy?: Map<string, number>
  turnPenalty?: number
  congestionPenalty?: number
  maxIterations?: number
  preferAxis?: 'x' | 'y'
}

export type RouteResult = {
  points: Point[]
  gridPath: GridPoint[]
}

type HeapItem = { id: number; priority: number }

class MinHeap {
  private items: HeapItem[] = []

  get size() {
    return this.items.length
  }

  push(item: HeapItem) {
    this.items.push(item)
    this.bubbleUp(this.items.length - 1)
  }

  pop(): HeapItem | null {
    if (!this.items.length) return null
    const top = this.items[0]
    const last = this.items.pop()
    if (this.items.length && last) {
      this.items[0] = last
      this.bubbleDown(0)
    }
    return top
  }

  private bubbleUp(index: number) {
    let idx = index
    while (idx > 0) {
      const parent = Math.floor((idx - 1) / 2)
      if (this.items[parent].priority <= this.items[idx].priority) break
      const tmp = this.items[parent]
      this.items[parent] = this.items[idx]
      this.items[idx] = tmp
      idx = parent
    }
  }

  private bubbleDown(index: number) {
    let idx = index
    const length = this.items.length
    while (true) {
      const left = idx * 2 + 1
      const right = idx * 2 + 2
      let smallest = idx
      if (left < length && this.items[left].priority < this.items[smallest].priority) {
        smallest = left
      }
      if (right < length && this.items[right].priority < this.items[smallest].priority) {
        smallest = right
      }
      if (smallest === idx) break
      const tmp = this.items[smallest]
      this.items[smallest] = this.items[idx]
      this.items[idx] = tmp
      idx = smallest
    }
  }
}

const DIRS = [
  { dx: 0, dy: -1 },
  { dx: 0, dy: 1 },
  { dx: -1, dy: 0 },
  { dx: 1, dy: 0 }
]

const DIRS_8 = [
  { dx: 0, dy: -1 },
  { dx: 0, dy: 1 },
  { dx: -1, dy: 0 },
  { dx: 1, dy: 0 },
  { dx: -1, dy: -1 },
  { dx: -1, dy: 1 },
  { dx: 1, dy: -1 },
  { dx: 1, dy: 1 }
]

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

const pointInRect = (point: Point, rect: Rect, margin = 0) =>
  point.x >= rect.x - margin &&
  point.x <= rect.x + rect.width + margin &&
  point.y >= rect.y - margin &&
  point.y <= rect.y + rect.height + margin

const segmentIntersectsRect = (p1: Point, p2: Point, rect: Rect, margin = 0) => {
  if (pointInRect(p1, rect, margin) || pointInRect(p2, rect, margin)) return true

  const left = rect.x - margin
  const right = rect.x + rect.width + margin
  const top = rect.y - margin
  const bottom = rect.y + rect.height + margin

  const edges: Array<[Point, Point]> = [
    [{ x: left, y: top }, { x: right, y: top }],
    [{ x: right, y: top }, { x: right, y: bottom }],
    [{ x: right, y: bottom }, { x: left, y: bottom }],
    [{ x: left, y: bottom }, { x: left, y: top }]
  ]

  const ccw = (a: Point, b: Point, c: Point) => (c.y - a.y) * (b.x - a.x) > (b.y - a.y) * (c.x - a.x)
  const intersects = (a: Point, b: Point, c: Point, d: Point) => ccw(a, c, d) !== ccw(b, c, d) && ccw(a, b, c) !== ccw(a, b, d)

  return edges.some(([a, b]) => intersects(p1, p2, a, b))
}

export const buildGridSpec = (
  bounds: { minX: number; minY: number; maxX: number; maxY: number },
  preferredSize: number,
  maxNodes = 45000
): GridSpec => {
  let size = Math.max(4, Math.round(preferredSize))
  const width = Math.max(1, bounds.maxX - bounds.minX)
  const height = Math.max(1, bounds.maxY - bounds.minY)
  let cols = Math.ceil(width / size) + 1
  let rows = Math.ceil(height / size) + 1
  if (cols * rows > maxNodes) {
    size = Math.ceil(Math.sqrt((width * height) / maxNodes))
    cols = Math.ceil(width / size) + 1
    rows = Math.ceil(height / size) + 1
  }

  const originX = Math.floor(bounds.minX / size) * size
  const originY = Math.floor(bounds.minY / size) * size

  return { originX, originY, size, cols, rows }
}

export const addOccupancy = (occupancy: Map<string, number>, gridPath: GridPoint[]) => {
  for (let i = 1; i < gridPath.length; i += 1) {
    const a = gridPath[i - 1]
    const b = gridPath[i]
    const key = edgeKey(a.gx, a.gy, b.gx, b.gy)
    occupancy.set(key, (occupancy.get(key) || 0) + 1)
  }
}

export const polylineToGridPath = (points: Point[], grid: GridSpec): GridPoint[] => {
  if (points.length < 2) return []

  const toGrid = (point: Point): GridPoint => ({
    gx: clamp(Math.round((point.x - grid.originX) / grid.size), 0, grid.cols - 1),
    gy: clamp(Math.round((point.y - grid.originY) / grid.size), 0, grid.rows - 1),
  })

  const path: GridPoint[] = []
  for (let i = 0; i < points.length - 1; i += 1) {
    const start = toGrid(points[i])
    const end = toGrid(points[i + 1])
    const segment = gridLine(start, end)
    segment.forEach(node => {
      const last = path[path.length - 1]
      if (!last || last.gx !== node.gx || last.gy !== node.gy) {
        path.push(node)
      }
    })
  }
  return path
}

export const connectOrthogonal = (
  start: Point,
  end: Point,
  obstacles: Rect[],
  clearance: number,
  preferAxis?: 'x' | 'y'
): Point[] | null => {
  const isClear = (a: Point, b: Point) =>
    !obstacles.some(rect => segmentIntersectsRect(a, b, rect, clearance))

  if (start.x === end.x || start.y === end.y) {
    if (isClear(start, end)) {
      return [start, end]
    }
  }

  const midA = { x: end.x, y: start.y }
  const midB = { x: start.x, y: end.y }

  const aClear = isClear(start, midA) && isClear(midA, end)
  const bClear = isClear(start, midB) && isClear(midB, end)

  if (aClear && bClear) {
    const preferA = preferAxis === 'x'
    const preferB = preferAxis === 'y'
    if (preferA && !preferB) return [start, midA, end]
    if (preferB && !preferA) return [start, midB, end]
    const lenA = Math.abs(start.x - midA.x) + Math.abs(start.y - midA.y) + Math.abs(end.x - midA.x) + Math.abs(end.y - midA.y)
    const lenB = Math.abs(start.x - midB.x) + Math.abs(start.y - midB.y) + Math.abs(end.x - midB.x) + Math.abs(end.y - midB.y)
    return lenA <= lenB ? [start, midA, end] : [start, midB, end]
  }

  if (aClear) return [start, midA, end]
  if (bClear) return [start, midB, end]
  return null
}

export const simplifyOrthogonalPath = (points: Point[], minSegment = 0) => {
  if (points.length <= 2) return points
  const cleaned: Point[] = []
  points.forEach(point => {
    const last = cleaned[cleaned.length - 1]
    if (last && last.x === point.x && last.y === point.y) return
    cleaned.push(point)
  })

  const simplified: Point[] = []
  for (let i = 0; i < cleaned.length; i += 1) {
    const prev = simplified[simplified.length - 1]
    const current = cleaned[i]
    const next = cleaned[i + 1]
    if (prev && next) {
      if ((prev.x === current.x && current.x === next.x) || (prev.y === current.y && current.y === next.y)) {
        continue
      }
    }
    simplified.push(current)
  }

  if (minSegment <= 0 || simplified.length <= 2) return simplified
  const finalPath: Point[] = [simplified[0]]
  for (let i = 1; i < simplified.length - 1; i += 1) {
    const last = finalPath[finalPath.length - 1]
    const curr = simplified[i]
    if (Math.hypot(curr.x - last.x, curr.y - last.y) < minSegment) {
      continue
    }
    finalPath.push(curr)
  }
  finalPath.push(simplified[simplified.length - 1])
  return finalPath
}

const expandRect = (rect: Rect, clearance: number): Rect => ({
  x: rect.x - clearance,
  y: rect.y - clearance,
  width: rect.width + clearance * 2,
  height: rect.height + clearance * 2
})

const hasLineOfSight = (a: Point, b: Point, expanded: Rect[]) =>
  !expanded.some(rect => segmentIntersectsRect(a, b, rect, 0))

const shortcutPath = (points: Point[], expanded: Rect[]) => {
  if (points.length <= 2) return points
  const simplified: Point[] = []
  let index = 0
  simplified.push(points[0])
  while (index < points.length - 1) {
    let next = points.length - 1
    for (let j = points.length - 1; j > index + 1; j -= 1) {
      if (hasLineOfSight(points[index], points[j], expanded)) {
        next = j
        break
      }
    }
    simplified.push(points[next])
    index = next
  }
  return simplified
}

const roundCorners = (points: Point[], radius: number, minSegment = 0) => {
  if (points.length <= 2 || radius <= 0) return points
  const output: Point[] = [points[0]]
  const maxCos = 0.999

  for (let i = 1; i < points.length - 1; i += 1) {
    const prev = points[i - 1]
    const curr = points[i]
    const next = points[i + 1]

    const v1x = prev.x - curr.x
    const v1y = prev.y - curr.y
    const v2x = next.x - curr.x
    const v2y = next.y - curr.y

    const len1 = Math.hypot(v1x, v1y)
    const len2 = Math.hypot(v2x, v2y)
    if (len1 < 1e-3 || len2 < 1e-3) {
      output.push(curr)
      continue
    }

    const cos = (v1x * v2x + v1y * v2y) / (len1 * len2)
    if (Math.abs(cos) >= maxCos) {
      output.push(curr)
      continue
    }

    const offset = Math.min(radius, len1 * 0.5, len2 * 0.5)
    if (offset < minSegment * 0.3) {
      output.push(curr)
      continue
    }

    const p1 = { x: curr.x + (v1x / len1) * offset, y: curr.y + (v1y / len1) * offset }
    const p2 = { x: curr.x + (v2x / len2) * offset, y: curr.y + (v2y / len2) * offset }

    output.push(p1, p2)
  }

  output.push(points[points.length - 1])
  return output
}

export const smoothAnyAnglePath = (
  points: Point[],
  obstacles: Rect[],
  clearance: number,
  cornerRadius: number,
  minSegment = 0
): Point[] => {
  if (points.length <= 2) return points
  const expanded = obstacles.map(rect => expandRect(rect, clearance))
  const shortened = shortcutPath(points, expanded)
  return roundCorners(shortened, cornerRadius, minSegment)
}

export const routeOrthogonalPath = (options: RouteOptions): RouteResult | null => {
  const {
    start,
    end,
    obstacles,
    clearance,
    grid,
    occupancy,
    preferAxis,
    turnPenalty = grid.size * 0.8,
    congestionPenalty = grid.size * 5,
    maxIterations = grid.cols * grid.rows * 8
  } = options

  if (grid.cols <= 1 || grid.rows <= 1) return null

  const expanded = obstacles.map(rect => ({
    x: rect.x - clearance,
    y: rect.y - clearance,
    width: rect.width + clearance * 2,
    height: rect.height + clearance * 2
  }))

  const toGrid = (point: Point) => ({
    gx: clamp(Math.round((point.x - grid.originX) / grid.size), 0, grid.cols - 1),
    gy: clamp(Math.round((point.y - grid.originY) / grid.size), 0, grid.rows - 1)
  })

  const toWorld = (gp: GridPoint) => ({
    x: grid.originX + gp.gx * grid.size,
    y: grid.originY + gp.gy * grid.size
  })

  const isBlocked = (gp: GridPoint, allow: GridPoint) => {
    if (gp.gx === allow.gx && gp.gy === allow.gy) return false
    const point = toWorld(gp)
    return expanded.some(rect => pointInRect(point, rect, 0))
  }

  const startNode = toGrid(start)
  const endNode = toGrid(end)

  if (isBlocked(startNode, startNode) || isBlocked(endNode, endNode)) {
    // Allow start/end, continue
  }

  const cols = grid.cols
  const rows = grid.rows
  const totalStates = cols * rows * 4
  const gScore = new Float64Array(totalStates)
  const cameFrom = new Int32Array(totalStates)
  gScore.fill(Number.POSITIVE_INFINITY)
  cameFrom.fill(-1)

  const open = new MinHeap()
  for (let dir = 0; dir < 4; dir += 1) {
    const idx = stateIndex(startNode.gx, startNode.gy, dir, cols)
    gScore[idx] = 0
    const h = heuristic(startNode, endNode)
    open.push({ id: idx, priority: h })
  }

  let iterations = 0
  let bestEnd: number | null = null

  while (open.size && iterations < maxIterations) {
    iterations += 1
    const current = open.pop()
    if (!current) break
    const { gx, gy, dir } = decodeState(current.id, cols)

    if (gx === endNode.gx && gy === endNode.gy) {
      bestEnd = current.id
      break
    }

    for (let ndir = 0; ndir < 4; ndir += 1) {
      const nx = gx + DIRS[ndir].dx
      const ny = gy + DIRS[ndir].dy
      if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue
      const nextNode = { gx: nx, gy: ny }
      if (isBlocked(nextNode, endNode)) continue

      const edgePenalty = occupancy ? (occupancy.get(edgeKey(gx, gy, nx, ny)) || 0) * congestionPenalty : 0
      const moveAxis = ndir < 2 ? 'y' : 'x'
      const axisPenalty = preferAxis && moveAxis !== preferAxis ? grid.size * 0.15 : 0
      const turnCost = dir === ndir ? 0 : turnPenalty
      const tentative = gScore[current.id] + grid.size + turnCost + edgePenalty + axisPenalty
      const nextId = stateIndex(nx, ny, ndir, cols)

      if (tentative < gScore[nextId]) {
        cameFrom[nextId] = current.id
        gScore[nextId] = tentative
        const h = heuristic(nextNode, endNode)
        open.push({ id: nextId, priority: tentative + h })
      }
    }
  }

  if (bestEnd == null) return null

  const gridPath: GridPoint[] = []
  let currentId = bestEnd
  while (currentId >= 0) {
    const { gx, gy } = decodeState(currentId, cols)
    const last = gridPath[0]
    if (!last || last.gx !== gx || last.gy !== gy) {
      gridPath.unshift({ gx, gy })
    }
    currentId = cameFrom[currentId]
  }

  if (gridPath.length < 2) {
    return { points: [start, end], gridPath }
  }

  const points = simplifyOrthogonalPath(gridPath.map(toWorld))
  return { points, gridPath }
}

export const routeAnyAnglePath = (options: RouteOptions): RouteResult | null => {
  const {
    start,
    end,
    obstacles,
    clearance,
    grid,
    occupancy,
    preferAxis,
    congestionPenalty = grid.size * 3,
    maxIterations = grid.cols * grid.rows * 6
  } = options

  if (grid.cols <= 1 || grid.rows <= 1) return null

  const expanded = obstacles.map(rect => expandRect(rect, clearance))

  const toGrid = (point: Point) => ({
    gx: clamp(Math.round((point.x - grid.originX) / grid.size), 0, grid.cols - 1),
    gy: clamp(Math.round((point.y - grid.originY) / grid.size), 0, grid.rows - 1)
  })

  const toWorld = (gp: GridPoint) => ({
    x: grid.originX + gp.gx * grid.size,
    y: grid.originY + gp.gy * grid.size
  })

  const isBlocked = (gp: GridPoint, allow: GridPoint) => {
    if (gp.gx === allow.gx && gp.gy === allow.gy) return false
    const point = toWorld(gp)
    return expanded.some(rect => pointInRect(point, rect, 0))
  }

  const lineOfSight = (a: GridPoint, b: GridPoint) =>
    hasLineOfSight(toWorld(a), toWorld(b), expanded)

  const startNode = toGrid(start)
  const endNode = toGrid(end)
  const startIdx = nodeIndex(startNode.gx, startNode.gy, grid.cols)
  const endIdx = nodeIndex(endNode.gx, endNode.gy, grid.cols)

  const totalNodes = grid.cols * grid.rows
  const gScore = new Float64Array(totalNodes)
  const fScore = new Float64Array(totalNodes)
  const parent = new Int32Array(totalNodes)
  const closed = new Uint8Array(totalNodes)

  gScore.fill(Number.POSITIVE_INFINITY)
  fScore.fill(Number.POSITIVE_INFINITY)
  parent.fill(-1)

  gScore[startIdx] = 0
  fScore[startIdx] = heuristic(startNode, endNode)
  parent[startIdx] = startIdx

  const open = new MinHeap()
  open.push({ id: startIdx, priority: fScore[startIdx] })

  let iterations = 0
  let found = false

  while (open.size && iterations < maxIterations) {
    iterations += 1
    const current = open.pop()
    if (!current) break
    const currentIdx = current.id
    if (closed[currentIdx]) continue
    closed[currentIdx] = 1

    if (currentIdx === endIdx) {
      found = true
      break
    }

    const currentNode = decodeNode(currentIdx, grid.cols)
    for (const dir of DIRS_8) {
      const nx = currentNode.gx + dir.dx
      const ny = currentNode.gy + dir.dy
      if (nx < 0 || ny < 0 || nx >= grid.cols || ny >= grid.rows) continue
      const nextNode = { gx: nx, gy: ny }
      const nextIdx = nodeIndex(nx, ny, grid.cols)
      if (closed[nextIdx]) continue
      if (isBlocked(nextNode, endNode)) continue

      const parentIdx = parent[currentIdx] >= 0 ? parent[currentIdx] : currentIdx
      const parentNode = decodeNode(parentIdx, grid.cols)
      const useParent = lineOfSight(parentNode, nextNode)
      const baseNode = useParent ? parentNode : currentNode
      const baseIdx = useParent ? parentIdx : currentIdx

      const dx = nextNode.gx - baseNode.gx
      const dy = nextNode.gy - baseNode.gy
      const stepCost = grid.size * Math.hypot(dx, dy)

      let axisPenalty = 0
      if (preferAxis === 'x' && Math.abs(dy) > Math.abs(dx)) axisPenalty = grid.size * 0.1
      if (preferAxis === 'y' && Math.abs(dx) > Math.abs(dy)) axisPenalty = grid.size * 0.1

      const edgePenalty = occupancy
        ? (occupancy.get(edgeKey(currentNode.gx, currentNode.gy, nextNode.gx, nextNode.gy)) || 0) * congestionPenalty
        : 0

      const tentative = gScore[baseIdx] + stepCost + axisPenalty + edgePenalty

      if (tentative < gScore[nextIdx]) {
        gScore[nextIdx] = tentative
        parent[nextIdx] = baseIdx
        fScore[nextIdx] = tentative + heuristic(nextNode, endNode)
        open.push({ id: nextIdx, priority: fScore[nextIdx] })
      }
    }
  }

  if (!found) return null

  const pathNodes: GridPoint[] = []
  let currentIdx = endIdx
  const guard = totalNodes + 5
  let steps = 0
  while (steps < guard) {
    steps += 1
    const node = decodeNode(currentIdx, grid.cols)
    pathNodes.unshift(node)
    const parentIdx = parent[currentIdx]
    if (parentIdx < 0 || parentIdx === currentIdx) break
    currentIdx = parentIdx
  }

  if (!pathNodes.length) return null

  const gridPath: GridPoint[] = []
  for (let i = 0; i < pathNodes.length - 1; i += 1) {
    const segment = gridLine(pathNodes[i], pathNodes[i + 1])
    segment.forEach(node => {
      const last = gridPath[gridPath.length - 1]
      if (!last || last.gx !== node.gx || last.gy !== node.gy) {
        gridPath.push(node)
      }
    })
  }

  const points = pathNodes.map(toWorld)
  points[0] = start
  points[points.length - 1] = end

  return { points, gridPath }
}

const heuristic = (a: GridPoint, b: GridPoint) => Math.hypot(a.gx - b.gx, a.gy - b.gy)

const stateIndex = (gx: number, gy: number, dir: number, cols: number) => ((gy * cols + gx) << 2) | dir

const decodeState = (id: number, cols: number) => {
  const dir = id & 3
  const cell = id >> 2
  const gx = cell % cols
  const gy = Math.floor(cell / cols)
  return { gx, gy, dir }
}

const edgeKey = (x1: number, y1: number, x2: number, y2: number) => {
  const a = `${x1},${y1}`
  const b = `${x2},${y2}`
  return a < b ? `${a}|${b}` : `${b}|${a}`
}

const nodeIndex = (gx: number, gy: number, cols: number) => gy * cols + gx

const decodeNode = (id: number, cols: number) => {
  const gx = id % cols
  const gy = Math.floor(id / cols)
  return { gx, gy }
}

const gridLine = (a: GridPoint, b: GridPoint): GridPoint[] => {
  const points: GridPoint[] = []
  let x0 = a.gx
  let y0 = a.gy
  const x1 = b.gx
  const y1 = b.gy
  const dx = Math.abs(x1 - x0)
  const dy = Math.abs(y1 - y0)
  const sx = x0 < x1 ? 1 : -1
  const sy = y0 < y1 ? 1 : -1
  let err = dx - dy

  while (true) {
    points.push({ gx: x0, gy: y0 })
    if (x0 === x1 && y0 === y1) break
    const e2 = 2 * err
    if (e2 > -dy) {
      err -= dy
      x0 += sx
    }
    if (e2 < dx) {
      err += dx
      y0 += sy
    }
  }

  return points
}
