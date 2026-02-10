import type { LinkModel } from '../../models/types'
import type { Rect, AnchorOverrideMap, LinkMeta } from './linkRoutingTypes'
import { clamp } from './linkRoutingUtils'

export type BuildLinkMetaDataParams = {
  links: LinkModel[]
  deviceViewMap: Map<string, Rect>
  areaViewMap: Map<string, Rect>
  deviceAreaMap: Map<string, string>
  layoutScale: number
  isL1View: boolean
  resolvePortAnchorWithOverrides: (
    deviceId: string,
    deviceRect: Rect,
    target: { x: number; y: number },
    port: string | undefined,
    overrides?: AnchorOverrideMap
  ) => { x: number; y: number; side?: string }
}

const PORT_LABEL_PADDING = 8
const LABEL_SCALE_MIN = 0.6
const LABEL_SCALE_MAX = 1.15

export function buildLinkMetaData(
  params: BuildLinkMetaDataParams,
  anchorOverrides?: AnchorOverrideMap
) {
  const {
    links, deviceViewMap, areaViewMap, deviceAreaMap,
    layoutScale, isL1View,
    resolvePortAnchorWithOverrides,
  } = params
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

  if (isL1View) {
    const labelScale = clamp(layoutScale, LABEL_SCALE_MIN, LABEL_SCALE_MAX)
    const labelPadding = PORT_LABEL_PADDING * labelScale
    const minLabelWidth = 24 * labelScale
    const charWidth = 6 * labelScale
    const computeLabelWidth = (text: string) => Math.max(text.length * charWidth + labelPadding, minLabelWidth)

    linkMetas.forEach(meta => {
      if (!meta) return
      const fromText = meta.link.fromPort?.trim()
      const toText = meta.link.toPort?.trim()
      if (fromText) {
        const width = computeLabelWidth(fromText)
        meta.fromLabelWidth = width
      }
      if (toText) {
        const width = computeLabelWidth(toText)
        meta.toLabelWidth = width
      }
    })
  }

  return { linkMetas }
}
