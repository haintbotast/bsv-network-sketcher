import type { TokenResponse, UserRecord } from '../models/api'
import { apiRequest, setToken } from './api'

export async function registerUser(payload: { email: string; password: string; display_name?: string }) {
  return apiRequest<UserRecord>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function loginUser(payload: { email: string; password: string }) {
  const token = await apiRequest<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
  setToken(token.access_token)
  return token
}

export async function getMe() {
  return apiRequest<UserRecord>('/api/v1/auth/me')
}

export function logout() {
  setToken(null)
}
