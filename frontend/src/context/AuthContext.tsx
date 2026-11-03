/**
 * Authentication context.
 *
 * Provides: token, user state, login/logout actions and session expiry handling.
 * Sets callbacks on the API client so it can trigger session expiry from interceptors.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { jwtDecode } from 'jwt-decode'
import { useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import { useTranslation } from 'react-i18next'
import { setOnSessionExpired, setOnTokenUpdated } from '@/api/client'
import { login as loginService, logout as logoutService } from '@/services/authService'
import { logger } from '@/lib/logger'
import type { JwtPayload } from '@/types/auth'

interface AuthContextValue {
  token: string | null
  isAuthenticated: boolean
  isStaff: boolean
  isSuperuser: boolean
  username: string | null
  userId: number | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function decodeToken(token: string | null): JwtPayload | null {
  if (!token) return null
  try {
    return jwtDecode<JwtPayload>(token)
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem('token'),
  )
  const navigate = useNavigate()
  const { enqueueSnackbar } = useSnackbar()
  const { t } = useTranslation('auth')
  const sessionExpiredRef = useRef(false)

  // Decode JWT claims reactively — no extra state needed
  const claims = useMemo(() => decodeToken(token), [token])

  const logout = useCallback(() => {
    logoutService()
    setToken(null)
    sessionExpiredRef.current = false
    navigate('/login')
    logger.info('User logged out')
  }, [navigate])

  const handleSessionExpired = useCallback(
    (message: string) => {
      if (sessionExpiredRef.current) return
      sessionExpiredRef.current = true
      localStorage.removeItem('token')
      setToken(null)
      // The API client's message is English-only; show the translated one
      enqueueSnackbar(t('session.expired'), { variant: 'error' })
      navigate('/login')
      logger.warn('Session expired', { message })
    },
    [navigate, enqueueSnackbar, t],
  )

  const handleTokenUpdated = useCallback(() => {
    const fresh = localStorage.getItem('token')
    setToken(fresh)
  }, [])

  useEffect(() => {
    setOnSessionExpired(handleSessionExpired)
    setOnTokenUpdated(handleTokenUpdated)
  }, [handleSessionExpired, handleTokenUpdated])

  const login = useCallback(
    async (username: string, password: string) => {
      const auth = await loginService(username, password)
      setToken(auth.accessToken)
      sessionExpiredRef.current = false
      enqueueSnackbar(t('session.loggedIn'), { variant: 'success' })
      navigate('/')
    },
    [navigate, enqueueSnackbar, t],
  )

  return (
    <AuthContext.Provider
      value={{
        token,
        isAuthenticated: !!token,
        isStaff: claims?.is_staff ?? false,
        isSuperuser: claims?.is_superuser ?? false,
        username: claims?.sub ?? null,
        userId: claims?.user_id ?? null,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
