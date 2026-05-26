import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

export default function AdminRoute() {
  const { user, isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  // If user profile hasn't loaded yet (but is authenticated), we wait
  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#F5F5F7] dark:bg-black">
        <div className="text-slate-500 font-medium">Authenticating...</div>
      </div>
    );
  }

  // Strict RBAC check
  if (!user.is_staff) {
    // Hidden completely from standard users
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
