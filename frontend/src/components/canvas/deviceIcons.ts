const ICON_URLS: Record<string, string> = {
  router: new URL('../../assets/icons/mdi/router-network.svg', import.meta.url).href,
  switch: new URL('../../assets/icons/mdi/ethernet.svg', import.meta.url).href,
  firewall: new URL('../../assets/icons/mdi/shield-lock.svg', import.meta.url).href,
  server: new URL('../../assets/icons/mdi/server.svg', import.meta.url).href,
  ap: new URL('../../assets/icons/mdi/access-point-network.svg', import.meta.url).href,
  pc: new URL('../../assets/icons/mdi/desktop-classic.svg', import.meta.url).href,
  storage: new URL('../../assets/icons/mdi/nas.svg', import.meta.url).href,
  unknown: new URL('../../assets/icons/mdi/help-circle-outline.svg', import.meta.url).href,
}

const iconCache = new Map<string, HTMLImageElement>()

function normalizeType(type: string) {
  return type.trim().toLowerCase()
}

export function resolveDeviceIconKey(deviceType: string) {
  const normalized = normalizeType(deviceType || 'unknown')
  if (normalized.includes('router')) return 'router'
  if (normalized.includes('switch')) return 'switch'
  if (normalized.includes('firewall') || normalized.includes('fw')) return 'firewall'
  if (normalized.includes('server')) return 'server'
  if (normalized === 'ap' || normalized.includes('access point') || normalized.includes('access-point')) return 'ap'
  if (normalized.includes('pc') || normalized.includes('desktop') || normalized.includes('laptop')) return 'pc'
  if (normalized.includes('storage') || normalized.includes('nas')) return 'storage'
  return 'unknown'
}

export function getDeviceIconUrl(deviceType: string) {
  const key = resolveDeviceIconKey(deviceType)
  return ICON_URLS[key] || ICON_URLS.unknown
}

export function getDeviceIconImage(deviceType: string) {
  const url = getDeviceIconUrl(deviceType)
  if (!url) return null
  const cached = iconCache.get(url)
  if (cached) return cached
  const img = new Image()
  img.src = url
  iconCache.set(url, img)
  return img
}
