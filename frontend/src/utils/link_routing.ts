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

const heuristic = (a: GridPoint, b: GridPoint) => (Math.abs(a.gx - b.gx) + Math.abs(a.gy - b.gy))

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
