import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, Wallet, Shield, Menu, X, LogOut, TrendingUp } from 'lucide-react';
import useStore from '../../store/useStore';
import Navbar from './Navbar';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/wallet',    label: 'Wallet',    icon: Wallet },
  { to: '/kyc',       label: 'KYC',       icon: Shield },
];

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const logout = useStore((s) => s.logout);

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--arcx-bg-primary)]">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-out
          lg:relative lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex h-full flex-col glass border-r border-white/[0.06]">
          {/* Logo */}
          <div className="flex h-16 items-center gap-3 px-6 border-b border-white/[0.06]">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-emerald-400">
              <TrendingUp className="h-5 w-5 text-[#0a0e1a]" strokeWidth={2.5} />
            </div>
            <span className="text-lg font-bold tracking-tight">
              <span className="gradient-text">ARCX</span>
            </span>
            <button
              className="ml-auto lg:hidden p-1 rounded-md hover:bg-white/10 transition"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5 text-[var(--arcx-text-secondary)]" />
            </button>
          </div>

          {/* Nav Links */}
          <nav className="flex-1 px-3 py-4 space-y-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-500/15 to-emerald-500/10 text-cyan-400 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.15)]'
                      : 'text-[var(--arcx-text-secondary)] hover:text-[var(--arcx-text-primary)] hover:bg-white/[0.04]'
                  }`
                }
              >
                <Icon className="h-[18px] w-[18px] shrink-0" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Logout */}
          <div className="px-3 py-4 border-t border-white/[0.06]">
            <button
              onClick={() => { logout(); window.location.href = '/login'; }}
              className="flex w-full items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-[var(--arcx-text-secondary)] hover:text-red-400 hover:bg-red-500/10 transition-all duration-200"
            >
              <LogOut className="h-[18px] w-[18px]" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col min-w-0">
        <Navbar onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl animate-[fadeIn_0.4s_ease-out]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
