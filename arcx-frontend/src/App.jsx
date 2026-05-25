import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import AppLayout       from './components/layout/AppLayout'
import AuthPage        from './pages/AuthPage'
import DashboardPage   from './pages/DashboardPage'
import WalletPage      from './pages/WalletPage'
import KYCPage         from './pages/KYCPage'

// ── Protected route wrapper ────────────────────────────────────────────────────
function Protected({ children }) {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  return isAuthenticated ? children : <Navigate to="/auth" replace />
}

export default function App() {
  const { logout, fetchMe, isAuthenticated } = useAuthStore()

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
          <Route path="kyc"       element={<KYCPage />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}