import { reactive, ref, computed } from 'vue'
import type { UserRecord } from '../models/api'
import { getMe, loginUser, logout as logoutUser } from '../services/auth'
import { getToken } from '../services/api'

export function useAuth() {
  const statusText = ref('đang kiểm tra...')
  const notice = ref('')
  const noticeType = ref<'info' | 'success' | 'error'>('info')

  const authForm = reactive({
    email: '',
    password: ''
  })
  const currentUser = ref<UserRecord | null>(null)

  const statusClass = computed(() => {
    if (statusText.value === 'healthy') return 'ok'
    if (statusText.value === 'không kết nối được') return 'error'
    if (statusText.value === 'lỗi kết nối') return 'error'
    return 'pending'
  })

  function setNotice(message: string, type: 'info' | 'success' | 'error' = 'info') {
    notice.value = message
    noticeType.value = type
  }

  async function fetchHealth() {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'}/api/v1/health`)
      if (!res.ok) {
        statusText.value = 'lỗi kết nối'
        return
      }
      const data = await res.json()
      statusText.value = data.status ?? 'không xác định'
    } catch {
      statusText.value = 'không kết nối được'
    }
  }

  async function initAuth(callbacks: {
    onSuccess: () => Promise<void>
  }) {
    const token = getToken()
    if (!token) return
    try {
      currentUser.value = await getMe()
      await callbacks.onSuccess()
    } catch {
      logoutUser()
      currentUser.value = null
      setNotice('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error')
    }
  }

  async function handleLogin(callbacks: {
    onSuccess: () => Promise<void>
  }) {
    if (!authForm.email || !authForm.password) {
      setNotice('Vui lòng nhập email và mật khẩu.', 'error')
      return
    }
    try {
      await loginUser({ email: authForm.email, password: authForm.password })
      currentUser.value = await getMe()
      await callbacks.onSuccess()
      setNotice('Đăng nhập thành công.', 'success')
    } catch (error: any) {
      setNotice(error?.message || 'Đăng nhập thất bại.', 'error')
    }
  }

  function handleLogout(callbacks: {
    onLogout: () => void
  }) {
    logoutUser()
    currentUser.value = null
    callbacks.onLogout()
  }

  return {
    statusText,
    notice,
    noticeType,
    authForm,
    currentUser,
    statusClass,
    setNotice,
    fetchHealth,
    initAuth,
    handleLogin,
    handleLogout,
  }
}
