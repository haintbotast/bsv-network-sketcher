import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { Viewport } from '../../models/types'
import { buildGridSpec } from '../../utils/link_routing'
import { computeCrossings, drawPolylineWithJumps } from '../../utils/line_crossings'
import type { Crossing } from '../../utils/line_crossings'

// Re-export types for backward compatibility
export type { Rect } from './linkRoutingTypes'
import type { Rect, RenderLink, UseLinkRoutingParams, PortAnchorOverrideMap } from './linkRoutingTypes'

import { clamp, computeSide, computePortLabelPlacement } from './linkRoutingUtils'

// Import sub-composables
import { usePortAnchors } from './usePortAnchors'
import { useLinkBundles } from './useLinkBundles'

// Import extracted standalone functions
import { buildLinkMetaData } from './buildLinkMetaData'
import { buildAnchorOverrides } from './buildAnchorOverrides'
import { routeLinks } from './routeLinks'

const PORT_LABEL_HEIGHT = 16
const PORT_LABEL_PADDING = 8
const LABEL_SCALE_MIN = 0.6
const LABEL_SCALE_MAX = 1.15
const ARC_RADIUS = 5

export function useLinkRouting(params: UseLinkRoutingParams) {
  const { props, layoutViewport, renderTuning, deviceViewMap, areaViewMap, deviceAreaMap, areaBounds, isPanning } = params

  const linkRouteCache = ref(new Map<string, {
    points: number[]
    fromAnchor: { x: number; y: number; side?: string }
    toAnchor: { x: number; y: number; side?: string }
    fromCenter: { x: number; y: number }
    toCenter: { x: number; y: number }
  }>())
  const linkRouteCacheViewport = ref<Viewport | null>(null)
  const visibleLinkCache = ref<RenderLink[]>([])

  // Port anchors sub-composable
  const userPortAnchorOverrides = computed<PortAnchorOverrideMap>(() => props.portAnchorOverrides || new Map())

  const {
    devicePortList,
    devicePortOrder,
    devicePortNeighbors,
    devicePortSideMap,
    resolvePortAnchorWithOverrides,
  } = usePortAnchors({
    props,
    renderTuning,
    deviceViewMap,
    portAnchorOverrides: userPortAnchorOverrides
  })

  // Link bundles sub-composable
  const {
    linkBundleIndex,
    areaBundleIndex,
    waypointAreaMap,
  } = useLinkBundles({ props, deviceAreaMap, areaViewMap })

  const buildVisibleLinks = (useCache: boolean) => {
    const scale = clamp(layoutViewport.value.scale, LABEL_SCALE_MIN, LABEL_SCALE_MAX)
    if (useCache) {
      const cachedViewport = linkRouteCacheViewport.value
      if (cachedViewport && cachedViewport.scale === layoutViewport.value.scale) {
        const cached = linkRouteCache.value
        const dx = layoutViewport.value.offsetX - cachedViewport.offsetX
        const dy = layoutViewport.value.offsetY - cachedViewport.offsetY
        let canUseCache = cached.size === props.links.length && cached.size > 0
        const shifted = props.links
          .map(link => {
            const entry = cached.get(link.id)
            if (!entry) {
              canUseCache = false
              return null
            }
            const points = entry.points.map((value, idx) => value + (idx % 2 === 0 ? dx : dy))
            return {
              id: link.id,
              fromAnchor: { x: entry.fromAnchor.x + dx, y: entry.fromAnchor.y + dy, side: entry.fromAnchor.side },
              toAnchor: { x: entry.toAnchor.x + dx, y: entry.toAnchor.y + dy, side: entry.toAnchor.side },
              fromCenter: { x: entry.fromCenter.x + dx, y: entry.fromCenter.y + dy },
              toCenter: { x: entry.toCenter.x + dx, y: entry.toCenter.y + dy },
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

        if (canUseCache) return { links: shifted, cache: null }
      }
    }

    const isL1View = (props.viewMode || 'L1') === 'L1'
    const debugRouteMode = (() => {
      if (typeof window === 'undefined') return false
      return new URLSearchParams(window.location.search).get('debugRoute') === '1'
    })()
    const clearance = (renderTuning.value.area_clearance ?? 0) * scale
    const gridBase = Math.max(6, Math.round((renderTuning.value.area_clearance ?? 0) * 0.5 * scale))
    const minSegment = Math.max(4, Math.round(6 * scale))
    const maxRouteLinks = 400
    const maxGridNodes = 30000

    let minX = Number.POSITIVE_INFINITY
    let minY = Number.POSITIVE_INFINITY
    let maxX = Number.NEGATIVE_INFINITY
    let maxY = Number.NEGATIVE_INFINITY

    areaViewMap.value.forEach(rect => {
      minX = Math.min(minX, rect.x)
      minY = Math.min(minY, rect.y)
      maxX = Math.max(maxX, rect.x + rect.width)
      maxY = Math.max(maxY, rect.y + rect.height)
    })
    deviceViewMap.value.forEach(rect => {
      minX = Math.min(minX, rect.x)
      minY = Math.min(minY, rect.y)
      maxX = Math.max(maxX, rect.x + rect.width)
      maxY = Math.max(maxY, rect.y + rect.height)
    })

    const padding = (renderTuning.value.corridor_gap ?? 0) * scale + clearance + gridBase * 2
    const grid = Number.isFinite(minX)
      ? buildGridSpec(
        { minX: minX - padding, minY: minY - padding, maxX: maxX + padding, maxY: maxY + padding },
        gridBase
      )
      : null

    const areaRects = Array.from(areaViewMap.value.entries()).map(([id, rect]) => ({ id, rect }))
    const deviceRects = Array.from(deviceViewMap.value.entries()).map(([id, rect]) => ({ id, rect }))

    const gridNodeCount = grid ? grid.cols * grid.rows : 0
    const allowAStar = isL1View && grid && props.links.length <= maxRouteLinks && gridNodeCount > 0 && gridNodeCount <= maxGridNodes

    const areaCenters = new Map<string, { x: number; y: number }>()
    areaRects.forEach(({ id, rect }) => {
      areaCenters.set(id, { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 })
    })

    // Unwrap reactive values for standalone functions
    const tuning = renderTuning.value
    const dvMap = deviceViewMap.value
    const avMap = areaViewMap.value
    const daMap = deviceAreaMap.value
    const dpList = devicePortList.value
    const dpOrder = devicePortOrder.value
    const dpNeighbors = devicePortNeighbors.value
    const dpSideMap = devicePortSideMap.value
    const lbIndex = linkBundleIndex.value
    const abIndex = areaBundleIndex.value
    const wpMap = waypointAreaMap.value

    const metaParams = {
      links: props.links,
      deviceViewMap: dvMap,
      areaViewMap: avMap,
      deviceAreaMap: daMap,
      devicePortOrder: dpOrder,
      devicePortList: dpList,
      linkBundleIndex: lbIndex,
      renderTuning: tuning,
      layoutScale: layoutViewport.value.scale,
      isL1View,
      resolvePortAnchorWithOverrides,
      areaCenters,
    }

    const routeCtx = {
      isL1View,
      scale,
      clearance,
      minSegment,
      grid,
      allowAStar: !!allowAStar,
      areaRects,
      deviceRects,
      renderTuning: tuning,
      areaViewMap: avMap,
      deviceAreaMap: daMap,
      areaBounds: areaBounds.value,
      linkBundleIndex: lbIndex,
      areaBundleIndex: abIndex,
      waypointAreaMap: wpMap,
      areaCenters,
      debugRouteMode,
    }

    const anchorCtx = {
      isL1View,
      scale,
      clearance,
      areaRects,
      deviceRects,
      renderTuning: tuning,
      deviceViewMap: dvMap,
      devicePortList: dpList,
      devicePortSideMap: dpSideMap,
      devicePortOrder: dpOrder,
      devicePortNeighbors: dpNeighbors,
      linkBundleIndex: lbIndex,
      userAnchorOverrides: userPortAnchorOverrides.value,
    }

    // Two-pass: metadata → route → anchor overrides → re-route
    const pass1 = buildLinkMetaData(metaParams)
    const pass1Result = routeLinks(pass1.linkMetas, pass1.laneIndex, pass1.labelObstacles, routeCtx)
    const overrides = buildAnchorOverrides(pass1.linkMetas, pass1Result.cache, anchorCtx)

    let finalResult = pass1Result
    if (overrides.size > 0 || userPortAnchorOverrides.value.size > 0) {
      const pass2 = buildLinkMetaData(metaParams, overrides)
      finalResult = routeLinks(pass2.linkMetas, pass2.laneIndex, pass2.labelObstacles, routeCtx)
    }

    return { links: finalResult.links, cache: finalResult.cache }
  }

  const visibleLinks = computed(() => {
    if (isPanning.value) return buildVisibleLinks(true).links
    return visibleLinkCache.value
  })

  const linkCrossings = computed<Map<string, Crossing[]>>(() => {
    if (isPanning.value) return new Map()
    const links = visibleLinks.value
    if (!links || links.length < 2) return new Map()
    return computeCrossings(links.map(l => ({ id: l.id, points: l.points })))
  })

  const visibleLinkShapes = computed(() => {
    const crossMap = linkCrossings.value
    const R = ARC_RADIUS
    return visibleLinks.value.map(link => {
      const crossings = crossMap.get(link.id) || []
      const cfg = link.config
      return {
        id: link.id,
        config: {
          sceneFunc: (ctx: any, shape: any) => {
            ctx.beginPath()
            drawPolylineWithJumps(ctx, link.points, crossings, R)
            ctx.fillStrokeShape(shape)
          },
          stroke: cfg.stroke,
          strokeWidth: cfg.strokeWidth,
          lineCap: cfg.lineCap,
          lineJoin: cfg.lineJoin,
          dash: cfg.dash,
          opacity: cfg.opacity,
          listening: false,
        },
      }
    })
  })

  const linkPortLabels = computed(() => {
    if (isPanning.value) return []
    if ((props.viewMode || 'L1') !== 'L1') return []
    const linkMap = new Map(visibleLinks.value.map(link => [link.id, link]))
    const labelScale = clamp(layoutViewport.value.scale, LABEL_SCALE_MIN, LABEL_SCALE_MAX)
    const labelHeight = PORT_LABEL_HEIGHT * labelScale
    const labelPadding = PORT_LABEL_PADDING * labelScale
    const labelOffset = (renderTuning.value.port_label_offset ?? 0) * labelScale
    const fontSize = 10 * labelScale
    const textPadX = 4 * labelScale
    const textPadY = 2 * labelScale
    const minLabelWidth = 24 * labelScale
    const charWidth = 6 * labelScale
    const slashWidth = charWidth
    const labelInset = ((props.viewMode || 'L1') === 'L1') ? slashWidth : 0
    const adjustedLabelOffset = Math.max(0, labelOffset - labelInset)
    const deviceLabelPadding = 8
    const deviceFontSize = 13 * labelScale
    const deviceCharWidth = deviceFontSize * 0.6
    const deviceLabelHeight = Math.max(12 * labelScale, deviceFontSize + 3 * labelScale)
    const rectsIntersect = (a: { x: number; y: number; width: number; height: number }, b: { x: number; y: number; width: number; height: number }) => {
      return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y
    }
    const deviceNameMap = new Map(props.devices.map(device => [device.id, device.name || '']))
    const deviceLabelRect = (rect: Rect, deviceId: string) => {
      const name = deviceNameMap.get(deviceId) || ''
      if (!name) return null
      const maxWidth = Math.max(rect.width - deviceLabelPadding * 2, 0)
      if (maxWidth <= 0) return null
      const textWidth = Math.max(0, name.length * deviceCharWidth)
      const width = Math.min(textWidth, maxWidth)
      if (width <= 0) return null
      return {
        x: rect.x + deviceLabelPadding,
        y: rect.y + deviceLabelPadding,
        width,
        height: deviceLabelHeight
      }
    }
    const pathCache = new Map<string, { segments: Array<{ ax: number; ay: number; bx: number; by: number; len: number }>; total: number }>()

    const rawLabels: Array<{
      id: string
      deviceId: string
      areaId: string | null
      side: string
      width: number
      height: number
      text: string
      angle: number
      center: { x: number; y: number }
      rect: Rect
      fontSize: number
      textPadX: number
      textPadY: number
      path: { segments: Array<{ ax: number; ay: number; bx: number; by: number; len: number }>; total: number }
      fromStart: boolean
      distance: number
      originalDistance: number
    }> = []

    const computeAngle = (from: { x: number; y: number }, to: { x: number; y: number }) => {
      const angle = Math.atan2(to.y - from.y, to.x - from.x) * (180 / Math.PI)
      if (angle > 90) return angle - 180
      if (angle < -90) return angle + 180
      return angle
    }

    const buildPathMetrics = (key: string, points: number[]) => {
      const cached = pathCache.get(key)
      if (cached) return cached
      const segments: Array<{ ax: number; ay: number; bx: number; by: number; len: number }> = []
      let total = 0
      for (let i = 0; i + 3 < points.length; i += 2) {
        const ax = points[i]
        const ay = points[i + 1]
        const bx = points[i + 2]
        const by = points[i + 3]
        const len = Math.hypot(bx - ax, by - ay)
        if (len <= 0) continue
        segments.push({ ax, ay, bx, by, len })
        total += len
      }
      const path = { segments, total }
      pathCache.set(key, path)
      return path
    }

    const resolvePointAlongPath = (
      path: { segments: Array<{ ax: number; ay: number; bx: number; by: number; len: number }>; total: number },
      distance: number,
      fromStart: boolean
    ) => {
      if (path.segments.length === 0 || path.total <= 0) return null
      let remaining = Math.max(distance, 0)

      if (fromStart) {
        for (const seg of path.segments) {
          if (remaining <= seg.len) {
            const t = seg.len > 0 ? remaining / seg.len : 0
            const x = seg.ax + (seg.bx - seg.ax) * t
            const y = seg.ay + (seg.by - seg.ay) * t
            return { x, y, angle: computeAngle({ x: seg.ax, y: seg.ay }, { x: seg.bx, y: seg.by }) }
          }
          remaining -= seg.len
        }
        const last = path.segments[path.segments.length - 1]
        return { x: last.bx, y: last.by, angle: computeAngle({ x: last.ax, y: last.ay }, { x: last.bx, y: last.by }) }
      }

      for (let i = path.segments.length - 1; i >= 0; i -= 1) {
        const seg = path.segments[i]
        if (remaining <= seg.len) {
          const t = seg.len > 0 ? remaining / seg.len : 0
          const x = seg.bx + (seg.ax - seg.bx) * t
          const y = seg.by + (seg.ay - seg.by) * t
          return { x, y, angle: computeAngle({ x: seg.bx, y: seg.by }, { x: seg.ax, y: seg.ay }) }
        }
        remaining -= seg.len
      }
      const first = path.segments[0]
      return { x: first.ax, y: first.ay, angle: computeAngle({ x: first.bx, y: first.by }, { x: first.ax, y: first.ay }) }
    }

    props.links.forEach(link => {
      const entry = linkMap.get(link.id)
      if (!entry) return

      const fromText = link.fromPort?.trim()
      const toText = link.toPort?.trim()
      const path = buildPathMetrics(link.id, entry.points)

      const placeLabel = (
        id: string,
        text: string,
        anchor: { x: number; y: number; side?: string },
        center: { x: number; y: number },
        neighbor: { x: number; y: number },
        deviceId: string,
        deviceRect: Rect,
        fromStart: boolean
      ) => {
        if (!text) return
        const width = Math.max(text.length * charWidth + labelPadding, minLabelWidth)
        const desiredDistance = adjustedLabelOffset
        const fallback = computePortLabelPlacement(anchor, center, width, labelHeight, adjustedLabelOffset)
        let safeDistance = path.total > 0
          ? (desiredDistance <= path.total ? desiredDistance : Math.max(path.total * 0.5, 0))
          : 0
        const side = anchor.side || computeSide(deviceRect, neighbor)
        const allowedInset = slashWidth
        const minInsetDistance = (side === 'left' || side === 'right')
          ? Math.max(0, width / 2 - allowedInset)
          : Math.max(0, labelHeight / 2 - allowedInset)
        safeDistance = Math.max(safeDistance, minInsetDistance)
        if (path.total > 0) {
          const labelZone = deviceLabelRect(deviceRect, deviceId)
          if (labelZone) {
            const gap = Math.max(2, 2 * labelScale)
            let minTextDistance = 0
            if (side === 'right') {
              minTextDistance = labelZone.x + labelZone.width + gap + width / 2 - anchor.x
            } else if (side === 'left') {
              minTextDistance = anchor.x - labelZone.x + gap + width / 2
            } else if (side === 'top') {
              minTextDistance = anchor.y - labelZone.y + gap + labelHeight / 2
            } else {
              minTextDistance = labelZone.y + labelZone.height + gap + labelHeight / 2 - anchor.y
            }
            safeDistance = Math.max(safeDistance, minTextDistance)
          }
          safeDistance = Math.min(path.total, safeDistance)
        }
        let pointOnPath = resolvePointAlongPath(path, safeDistance, fromStart)
        if (path.total > 0) {
          const labelZone = deviceLabelRect(deviceRect, deviceId)
          if (labelZone) {
            const step = Math.max(4, labelHeight * 0.6)
            for (let i = 0; i < 6 && safeDistance < path.total; i += 1) {
              const point = resolvePointAlongPath(path, safeDistance, fromStart)
              if (!point) break
              const labelRect = {
                x: point.x - width / 2,
                y: point.y - labelHeight / 2,
                width,
                height: labelHeight
              }
              if (!rectsIntersect(labelRect, labelZone)) break
              safeDistance = Math.min(path.total, safeDistance + step)
            }
            pointOnPath = resolvePointAlongPath(path, safeDistance, fromStart)
          }
        }
        const cx = pointOnPath ? pointOnPath.x : (fallback.x + width / 2)
        const cy = pointOnPath ? pointOnPath.y : (fallback.y + labelHeight / 2)
        const angle = pointOnPath ? pointOnPath.angle : computeAngle(anchor, neighbor)

        rawLabels.push({
          id,
          deviceId,
          areaId: deviceAreaMap.value.get(deviceId) || null,
          side: anchor.side || computeSide(deviceRect, neighbor),
          width,
          height: labelHeight,
          text,
          angle,
          center: { x: cx, y: cy },
          rect: deviceRect,
          fontSize,
          textPadX,
          textPadY,
          path,
          fromStart,
          distance: safeDistance,
          originalDistance: safeDistance
        })
      }

      const fromNeighbor = entry.points.length >= 4
        ? { x: entry.points[2], y: entry.points[3] }
        : entry.toAnchor
      const toNeighbor = entry.points.length >= 4
        ? { x: entry.points[entry.points.length - 4], y: entry.points[entry.points.length - 3] }
        : entry.fromAnchor

      const fromRect = deviceViewMap.value.get(link.fromDeviceId)
      const toRect = deviceViewMap.value.get(link.toDeviceId)
      if (fromRect && fromText) {
        placeLabel(
          `${link.id}-from`,
          fromText,
          entry.fromAnchor,
          entry.fromCenter,
          fromNeighbor,
          link.fromDeviceId,
          fromRect,
          true
        )
      }
      if (toRect && toText) {
        placeLabel(
          `${link.id}-to`,
          toText,
          entry.toAnchor,
          entry.toCenter,
          toNeighbor,
          link.toDeviceId,
          toRect,
          false
        )
      }
    })

    // Single-pass collision avoidance per device-side
    const allowLabelShift = false
    if (allowLabelShift) {
      const bySide = new Map<string, typeof rawLabels>()
      rawLabels.forEach(label => {
        const key = `${label.deviceId}-${label.side}`
        const list = bySide.get(key) || []
        list.push(label)
        bySide.set(key, list)
      })

      const maxDisplacement = 60 * labelScale

      bySide.forEach(list => {
        if (list.length < 2) return
        const side = list[0].side
        const originals = list.map(l => l.originalDistance)

        const isVertical = side === 'left' || side === 'right'
        const sizeFor = (label: (typeof list)[number]) => (isVertical ? label.height : label.width)
        list.sort((a, b) => a.distance - b.distance)
        let cursor = list[0].distance
        list.forEach((label, idx) => {
          if (idx === 0) return
          const minGap = (sizeFor(list[idx - 1]) + sizeFor(label)) / 2 + 2 * labelScale
          if (label.distance < cursor + minGap) {
            label.distance = cursor + minGap
          }
          cursor = label.distance
        })

        list.forEach((label, idx) => {
          const orig = originals[idx]
          const delta = label.distance - orig
          if (Math.abs(delta) > maxDisplacement) {
            label.distance = orig + Math.sign(delta) * maxDisplacement
          }
        })
      })
    }

    rawLabels.forEach(label => {
      const point = resolvePointAlongPath(label.path, label.distance, label.fromStart)
      if (point) {
        label.center = { x: point.x, y: point.y }
        label.angle = point.angle
      }
    })

    return rawLabels.map(label => ({
      id: label.id,
      group: {
        x: label.center.x,
        y: label.center.y,
        rotation: label.angle,
        offsetX: label.width / 2,
        offsetY: label.height / 2
      },
      bg: {
        x: 0,
        y: 0,
        width: label.width,
        height: label.height,
        fill: '#ffffff',
        stroke: '#b0b0b0',
        strokeWidth: Math.max(1, Math.round(1 * labelScale)),
        cornerRadius: 4 * labelScale,
        opacity: 0.92,
        shadowEnabled: false
      },
      text: {
        x: label.textPadX,
        y: label.textPadY,
        width: Math.max(label.width - label.textPadX * 2, 1),
        height: Math.max(label.height - label.textPadY * 2, 1),
        text: label.text,
        fontSize: label.fontSize,
        fill: '#2b2a28',
        align: 'center',
        verticalAlign: 'middle'
      }
    }))
  })

  const refreshLinkCache = () => {
    if (isPanning.value) return
    const result = buildVisibleLinks(false)
    visibleLinkCache.value = result.links
    if (result.cache) {
      linkRouteCache.value = result.cache
      linkRouteCacheViewport.value = { ...layoutViewport.value }
    }
  }

  let refreshLinkRaf = 0
  const scheduleRefreshLinkCache = () => {
    if (isPanning.value) return
    if (refreshLinkRaf) return
    refreshLinkRaf = requestAnimationFrame(() => {
      refreshLinkRaf = 0
      if (isPanning.value) return
      refreshLinkCache()
    })
  }

  watch(
    [
      () => props.links,
      () => props.areas,
      () => props.devices,
      () => props.viewMode,
      () => props.l2Assignments,
      () => props.portAnchorOverrides,
      () => layoutViewport.value.scale,
      () => layoutViewport.value.offsetX,
      () => layoutViewport.value.offsetY,
      renderTuning
    ],
    () => {
      scheduleRefreshLinkCache()
    },
    { immediate: true }
  )

  onBeforeUnmount(() => {
    if (refreshLinkRaf) {
      cancelAnimationFrame(refreshLinkRaf)
      refreshLinkRaf = 0
    }
  })

  return {
    visibleLinks,
    visibleLinkShapes,
    linkPortLabels
  }
}
