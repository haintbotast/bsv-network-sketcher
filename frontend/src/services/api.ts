const TOKEN_KEY = 'bsv_ns_token'
let cachedToken: string | null = null

export function getApiBase() {
  return import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
}

export function getToken() {
  if (cachedToken !== null) return cachedToken
  if (typeof localStorage === 'undefined') return null
  cachedToken = localStorage.getItem(TOKEN_KEY)
  return cachedToken
}

export function setToken(token: string | null) {
  cachedToken = token
  if (typeof localStorage === 'undefined') return
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

async function parseError(response: Response) {
  try {
    const data = await response.json()
    if (typeof data?.detail === 'string') return data.detail
    if (typeof data?.message === 'string') return data.message
    return JSON.stringify(data)
  } catch {
    return `HTTP ${response.status}`
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {})
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${getApiBase()}${path}`, {
    ...options,
    headers
  })

  if (!response.ok) {
    const errorMessage = await parseError(response)
    throw new Error(errorMessage)
  }

  if (response.status === 204) {
    return null as T
  }

  return response.json() as Promise<T>
}
