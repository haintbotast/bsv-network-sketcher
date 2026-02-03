import type { LinkModel } from '../../models/types'
import type { Rect, RenderTuning, AnchorOverrideMap, LinkMeta } from './linkRoutingTypes'
import { clamp, computePortLabelPlacement } from './linkRoutingUtils'

export type BuildLinkMetaDataParams = {
  links: LinkModel[]
  deviceViewMap: Map<string, Rect>
  areaViewMap: Map<string, Rect>
  deviceAreaMap: Map<string, string>
  devicePortOrder: Map<string, Map<string, number>>
  devicePortList: Map<string, string[]>
  linkBundleIndex: Map<string, { index: number; total: number }>
  renderTuning: RenderTuning
  layoutScale: number
  isL1View: boolean
  resolvePortAnchorWithOverrides: (
    deviceId: string,
    deviceRect: Rect,
    target: { x: number; y: number },
    port: string | undefined,
    overrides?: AnchorOverrideMap
  ) => { x: number; y: number; side?: string }
  areaCenters: Map<string, { x: number; y: number }>
}

const PORT_LABEL_HEIGHT = 16
const PORT_LABEL_PADDING = 8
const LABEL_SCALE_MIN = 0.6
const LABEL_SCALE_MAX = 1.15

export function buildLinkMetaData(
  params: BuildLinkMetaDataParams,
  anchorOverrides?: AnchorOverrideMap
) {
  const {
    links, deviceViewMap, areaViewMap, deviceAreaMap,
    devicePortOrder, devicePortList, linkBundleIndex,
    renderTuning, layoutScale, isL1View,
    resolvePortAnchorWithOverrides, areaCenters,
  } = params

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

  const laneGroups = new Map<string, Array<{ id: string; order: number; portBias: number }>>()
  const linkMetas = links.map(link => {
    const fromView = deviceViewMap.get(link.fromDeviceId)
    const toView = deviceViewMap.get(link.toDeviceId)
    if (!fromView || !toView) return null
    const fromCenter = { x: fromView.x + fromView.width / 2, y: fromView.y + fromView.height / 2 }
    const toCenter = { x: toView.x + toView.width / 2, y: toView.y + toView.height / 2 }
    const fromAnchor = resolvePortAnchorWithOverrides(link.fromDeviceId, fromView, toCenter, link.fromPort, anchorOverrides)
    const toAnchor = resolvePortAnchorWithOverrides(link.toDeviceId, toView, fromCenter, link.toPort, anchorOverrides)
    const fromAreaId = deviceAreaMap.get(link.fromDeviceId)
    const toAreaId = deviceAreaMap.get(link.toDeviceId)
    const fromArea = fromAreaId ? areaViewMap.get(fromAreaId) : null
    const toArea = toAreaId ? areaViewMap.get(toAreaId) : null

    if (fromAreaId && toAreaId && fromAreaId !== toAreaId && fromArea && toArea) {
      const axis = resolveLaneAxis(fromAreaId, toAreaId)
      const order = axis === 'y'
        ? (fromAnchor.y + toAnchor.y) / 2
        : (fromAnchor.x + toAnchor.x) / 2
      const fromOrder = link.fromPort
        ? devicePortOrder.get(link.fromDeviceId)?.get(link.fromPort)
        : null
      const toOrder = link.toPort
        ? devicePortOrder.get(link.toDeviceId)?.get(link.toPort)
        : null
      const fromCount = link.fromPort
        ? (devicePortList.get(link.fromDeviceId)?.length ?? 0)
        : 0
      const toCount = link.toPort
        ? (devicePortList.get(link.toDeviceId)?.length ?? 0)
        : 0
      const fromNorm = fromOrder != null && fromCount > 1 ? fromOrder / (fromCount - 1) : null
      const toNorm = toOrder != null && toCount > 1 ? toOrder / (toCount - 1) : null
      const portBias = ((fromNorm ?? 0.5) + (toNorm ?? 0.5)) / 2
      const key = getPairKey(fromAreaId, toAreaId)
      const list = laneGroups.get(key) || []
      list.push({ id: link.id, order, portBias })
      laneGroups.set(key, list)
    }

    return {
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
    } as LinkMeta
  })

  const labelObstacles: Array<{ linkId: string; rect: Rect }> = []
  if (isL1View) {
    const labelScale = clamp(layoutScale, LABEL_SCALE_MIN, LABEL_SCALE_MAX)
    const labelHeight = PORT_LABEL_HEIGHT * labelScale
    const labelPadding = PORT_LABEL_PADDING * labelScale
    const labelOffset = (renderTuning.port_label_offset ?? 0) * labelScale
    const minLabelWidth = 24 * labelScale
    const charWidth = 6 * labelScale
    const baseGap = Math.max(2, Math.min(renderTuning.label_gap_x ?? 0, renderTuning.label_gap_y ?? 0) * 0.5 * labelScale)
    const computeLabelWidth = (text: string) => Math.max(text.length * charWidth + labelPadding, minLabelWidth)

    const buildLabelRect = (
      linkId: string,
      text: string,
      width: number,
      anchor: { x: number; y: number },
      center: { x: number; y: number },
      neighbor: { x: number; y: number }
    ) => {
      const content = text.trim()
      if (!content) return
      const height = labelHeight
      const dx = neighbor.x - anchor.x
      const dy = neighbor.y - anchor.y
      const len = Math.hypot(dx, dy)
      let cx: number
      let cy: number
      if (len < 1) {
        const pos = computePortLabelPlacement(anchor, center, width, height, labelOffset)
        cx = pos.x + width / 2
        cy = pos.y + height / 2
      } else {
        const offset = (width / 2 + 4) / len
        cx = anchor.x + dx * offset
        cy = anchor.y + dy * offset
      }
      labelObstacles.push({
        linkId,
        rect: {
          x: cx - width / 2 - baseGap,
          y: cy - height / 2 - baseGap,
          width: width + baseGap * 2,
          height: height + baseGap * 2,
        }
      })
    }

    linkMetas.forEach(meta => {
      if (!meta) return
      const fromText = meta.link.fromPort?.trim()
      const toText = meta.link.toPort?.trim()
      if (fromText) {
        const width = computeLabelWidth(fromText)
        meta.fromLabelWidth = width
        buildLabelRect(meta.link.id, fromText, width, meta.fromAnchor, meta.fromCenter, meta.toCenter)
      }
      if (toText) {
        const width = computeLabelWidth(toText)
        meta.toLabelWidth = width
        buildLabelRect(meta.link.id, toText, width, meta.toAnchor, meta.toCenter, meta.fromCenter)
      }
    })
  }

  const laneIndex = new Map<string, { index: number; total: number }>()
  laneGroups.forEach(list => {
    list.sort((a, b) => {
      const primary = a.order - b.order
      if (primary !== 0) return primary
      const secondary = a.portBias - b.portBias
      if (secondary !== 0) return secondary
      return a.id.localeCompare(b.id)
    })
    list.forEach((entry, idx) => {
      laneIndex.set(entry.id, { index: idx, total: list.length })
    })
  })

  return { linkMetas, laneIndex, labelObstacles }
}
