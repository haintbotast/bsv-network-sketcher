import { computed, type ComputedRef } from 'vue'
import type { AreaModel, LinkModel } from '../../models/types'
import type { Rect } from './linkRoutingTypes'

export function useLinkBundles(deps: {
  props: {
    links: LinkModel[]
    areas: AreaModel[]
  }
  deviceAreaMap: ComputedRef<Map<string, string>>
  areaViewMap: ComputedRef<Map<string, Rect>>
}) {
  const { props, deviceAreaMap, areaViewMap } = deps

  const linkBundleIndex = computed(() => {
    const map = new Map<string, { index: number; total: number }>()
    const grouped = new Map<string, string[]>()

    const linkKey = (link: LinkModel) => {
      const from = link.fromDeviceId
      const to = link.toDeviceId
      return from < to ? `${from}|${to}` : `${to}|${from}`
    }

    props.links.forEach(link => {
      const key = linkKey(link)
      const list = grouped.get(key) || []
      list.push(link.id)
      grouped.set(key, list)
    })

    grouped.forEach(list => {
      list.sort()
      list.forEach((id, idx) => {
        map.set(id, { index: idx, total: list.length })
      })
    })
    return map
  })

  const areaBundleIndex = computed(() => {
    const map = new Map<string, { index: number; total: number }>()
    const grouped = new Map<string, string[]>()

    const areaKey = (fromArea: string, toArea: string) =>
      fromArea < toArea ? `${fromArea}|${toArea}` : `${toArea}|${fromArea}`

    props.links.forEach(link => {
      const fromArea = deviceAreaMap.value.get(link.fromDeviceId)
      const toArea = deviceAreaMap.value.get(link.toDeviceId)
      if (!fromArea || !toArea || fromArea === toArea) return
      const key = areaKey(fromArea, toArea)
      const list = grouped.get(key) || []
      list.push(link.id)
      grouped.set(key, list)
    })

    grouped.forEach(list => {
      list.sort()
      list.forEach((id, idx) => {
        map.set(id, { index: idx, total: list.length })
      })
    })

    return map
  })

  const waypointAreaMap = computed(() => {
    const map = new Map<string, { cx: number; cy: number; rect: Rect }>()
    const wpAreas = props.areas.filter(a => a.name.endsWith('_wp_'))
    if (wpAreas.length === 0) return map

    const nonWpAreas = props.areas.filter(a => !a.name.endsWith('_wp_'))
    const areaKey = (a: string, b: string) => a < b ? `${a}|${b}` : `${b}|${a}`

    for (const wp of wpAreas) {
      const rect = areaViewMap.value.get(wp.id)
      if (!rect) continue
      for (let i = 0; i < nonWpAreas.length; i += 1) {
        for (let j = i + 1; j < nonWpAreas.length; j += 1) {
          const names = [nonWpAreas[i].name, nonWpAreas[j].name].sort()
          if (wp.name === `${names[0]}_${names[1]}_wp_`) {
            map.set(areaKey(nonWpAreas[i].id, nonWpAreas[j].id), {
              cx: rect.x + rect.width / 2,
              cy: rect.y + rect.height / 2,
              rect
            })
          }
        }
      }
    }
    return map
  })

  return {
    linkBundleIndex,
    areaBundleIndex,
    waypointAreaMap,
  }
}
