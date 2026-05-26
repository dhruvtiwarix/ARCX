import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { useThemeStore } from './store/themeStore'
import AppLayout       from './components/layout/AppLayout'
import AuthPage        from './pages/AuthPage'
import DashboardPage   from './pages/DashboardPage'
import WalletPage      from './pages/WalletPage'
import KYCPage         from './pages/KYCPage'
import ProfilePage     from './pages/ProfilePage'
import PortfolioPage   from './pages/PortfolioPage'
import AdminPage       from './pages/AdminPage'
import AdminRoute      from './components/layout/AdminRoute'

// ── Protected route wrapper ────────────────────────────────────────────────────
function Protected({ children }) {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  return isAuthenticated ? children : <Navigate to="/auth" replace />
}

export default function App() {
  const { logout, fetchMe, isAuthenticated } = useAuthStore()

  // Init Theme
  useEffect(() => {
    useThemeStore.getState().initTheme()
  }, [])

  // Listen for forced logout (token refresh failure)
  useEffect(() => {
    const handler = () => logout()
    window.addEventListener('arcx:logout', handler)
    return () => window.removeEventListener('arcx:logout', handler)
  }, [logout])

  // Re-hydrate user profile on page refresh
  useEffect(() => {
    if (isAuthenticated) fetchMe()
  }, [isAuthenticated])

  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/auth" element={<AuthPage />} />

        {/* Protected — all inside AppLayout */}
        <Route path="/" element={
          <Protected><AppLayout /></Protected>
        }>
          <Route index            element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="wallet"    element={<WalletPage />} />
          <Route path="portfolio" element={<PortfolioPage />} />
          <Route path="kyc"       element={<KYCPage />} />
          <Route path="profile"   element={<ProfilePage />} />
          {/* Admin Operations (Hidden Route) */}
          <Route element={<AdminRoute />}>
            <Route path="admin-ops" element={<AdminPage />} />
          </Route>
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}