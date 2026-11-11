/**
 * Application router: the admin back office (Phase 5e).
 *
 * Everything a user does lives on the public site (Next.js). Here, a visitor
 * signs in as an administrator; anyone else is sent to the site. The old user
 * addresses (sign-up, "warn me") forward to their place on the site.
 */

import { Navigate, Route, Routes, useLocation, useSearchParams } from 'react-router-dom'
import { ToSite } from '@/components/common/ToSite'
import { AppLayout } from '@/components/layout/AppLayout'
import { useAuth } from '@/context/AuthContext'
import { AdminDashboardPage } from '@/pages/AdminDashboardPage'
import { AlertsPage } from '@/pages/AlertsPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { PlansPage } from '@/pages/PlansPage'
import { ProductDetailPage } from '@/pages/ProductDetailPage'
import { ProductsPage } from '@/pages/ProductsPage'
import { SearchConfigsPage } from '@/pages/SearchConfigsPage'
import { SourceWebsitesPage } from '@/pages/SourceWebsitesPage'
import { UsersPage } from '@/pages/UsersPage'
import { safeNextPath, withNext } from '@/lib/nextPath'

/** Where a signed-in administrator starts. */
const ADMIN_HOME = '/admin'

/**
 * The back office: not signed in → /login (coming back here); signed in but
 * not an administrator → the user's alerts on the site.
 */
function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isStaff, isSuperuser } = useAuth()
  const location = useLocation()
  if (!isAuthenticated) {
    return <Navigate to={withNext('/login', location.pathname + location.search)} replace />
  }
  if (!isStaff && !isSuperuser) return <ToSite path="/alertas" />
  return <>{children}</>
}

/** Login: a signed-in visitor goes to ?next= or the start page. */
function GuestOnly({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  const [params] = useSearchParams()
  if (!isAuthenticated) return <>{children}</>
  return <Navigate to={safeNextPath(params.get('next')) ?? '/'} replace />
}

/** The site's "warn me" page, with the same book, condition and price. */
function NewAlertOnSite() {
  const { search } = useLocation()
  return <ToSite path={`/alertas/novo${search}`} />
}

export function AppRouter() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <RequireAdmin>
            <Navigate to={ADMIN_HOME} replace />
          </RequireAdmin>
        }
      />
      <Route
        path="/login"
        element={
          <GuestOnly>
            <LoginPage />
          </GuestOnly>
        }
      />

      {/* User addresses from before Phase 5e: they live on the site now */}
      <Route path="/register" element={<ToSite path="/cadastro" />} />
      <Route path="/alertas/novo" element={<NewAlertOnSite />} />

      {/* Back office — administrators only, inside AppLayout */}
      <Route
        element={
          <RequireAdmin>
            <AppLayout />
          </RequireAdmin>
        }
      >
        <Route path="/admin" element={<AdminDashboardPage />} />
        <Route path="/admin/users" element={<UsersPage />} />
        <Route path="/admin/search-configs" element={<SearchConfigsPage />} />
        <Route path="/admin/source-websites" element={<SourceWebsitesPage />} />

        {/* Keyword alerts and plans in the menu; dashboard and products off it (Phase 5e) */}
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/plans" element={<PlansPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/products/:id" element={<ProductDetailPage />} />

        {/* Legacy redirects */}
        <Route path="/users" element={<Navigate to="/admin/users" replace />} />
        <Route path="/search-configs" element={<Navigate to="/admin/search-configs" replace />} />
        <Route path="/source-websites" element={<Navigate to="/admin/source-websites" replace />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
