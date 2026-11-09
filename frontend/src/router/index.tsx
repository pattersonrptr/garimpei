/**
 * Application router.
 * Uses React Router v6 with lazy-loaded pages for better performance.
 */

import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { useAuth } from '@/context/AuthContext'
import { AdminDashboardPage } from '@/pages/AdminDashboardPage'
import { AlertsPage } from '@/pages/AlertsPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { LandingPage } from '@/pages/LandingPage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { PlansPage } from '@/pages/PlansPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { ProductDetailPage } from '@/pages/ProductDetailPage'
import { ProductsPage } from '@/pages/ProductsPage'
import { SearchConfigsPage } from '@/pages/SearchConfigsPage'
import { SourceWebsitesPage } from '@/pages/SourceWebsitesPage'
import { UsersPage } from '@/pages/UsersPage'

/** Wraps protected routes — redirects to /login if not authenticated. */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

/** Wraps admin routes — redirects to /dashboard if not staff/superuser. */
function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { isStaff, isSuperuser } = useAuth()
  return isStaff || isSuperuser ? (
    <>{children}</>
  ) : (
    <Navigate to="/dashboard" replace />
  )
}

export function AppRouter() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <LandingPage />
          )
        }
      />
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        path="/register"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <RegisterPage />
          )
        }
      />

      {/* Protected routes — all inside AppLayout (Header + Sidebar + Footer) */}
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        {/* User pages */}
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/products/:id" element={<ProductDetailPage />} />
        <Route path="/plans" element={<PlansPage />} />

        {/* Admin pages (staff/superuser only) */}
        <Route
          path="/admin"
          element={
            <RequireAdmin>
              <AdminDashboardPage />
            </RequireAdmin>
          }
        />
        <Route
          path="/admin/users"
          element={
            <RequireAdmin>
              <UsersPage />
            </RequireAdmin>
          }
        />
        <Route
          path="/admin/search-configs"
          element={
            <RequireAdmin>
              <SearchConfigsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="/admin/source-websites"
          element={
            <RequireAdmin>
              <SourceWebsitesPage />
            </RequireAdmin>
          }
        />

        {/* Legacy redirects */}
        <Route
          path="/users"
          element={<Navigate to="/admin/users" replace />}
        />
        <Route
          path="/search-configs"
          element={<Navigate to="/admin/search-configs" replace />}
        />
        <Route
          path="/source-websites"
          element={<Navigate to="/admin/source-websites" replace />}
        />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
