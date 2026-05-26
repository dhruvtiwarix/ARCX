import { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { 
  Search, LayoutDashboard, Wallet, Briefcase, Settings, 
  Menu, X, ShieldCheck, FileText, ChevronRight, ChevronDown, Folder
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useThemeStore } from '../../store/themeStore'
import { Sun, Moon } from 'lucide-react'

function ThemeToggle() {
  const { theme, setTheme } = useThemeStore()
  const isDark = theme === 'dark' || (theme === 'system' && document.documentElement.classList.contains('dark'))

  return (
    <button 
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className="p-2 rounded-full bg-white/20 dark:bg-black/20 hover:bg-white/30 dark:hover:bg-black/40 backdrop-blur-md transition-colors"
      title="Toggle Theme"
    >
      {isDark ? <Sun size={18} className="text-white" /> : <Moon size={18} className="text-black" />}
    </button>
  )
}

function SidebarItem({ to, label, icon: Icon, exact = false }) {
  return (
    <NavLink
      to={to}
      end={exact}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-300 font-medium text-[14px]
         ${isActive 
           ? 'bg-black/10 dark:bg-white/10 text-black dark:text-white shadow-sm' 
           : 'text-slate-600 dark:text-slate-400 hover:text-black dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'
         }`
      }
    >
      <Icon size={18} />
      {label}
    </NavLink>
  )
}

function SidebarFolder({ label, icon: Icon, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-2">
      <div 
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between px-3 py-2 rounded-xl cursor-pointer text-slate-600 dark:text-slate-400 hover:text-black dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 transition-all duration-300"
      >
        <div className="flex items-center gap-3 font-medium text-[14px]">
          <Icon size={18} />
          {label}
        </div>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </div>
      {open && (
        <div className="ml-5 mt-1 pl-3 border-l border-black/10 dark:border-white/10 flex flex-col gap-1">
          {children}
        </div>
      )}
    </div>
  )
}

import NavTicker from '../ui/NavTicker'

export default function AppLayout() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'AR'

  return (
    <div className="flex h-screen overflow-hidden">
      
      {/* ── Mobile Header ──────────────────────────────────────────────── */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-14 glassContainer rounded-none border-t-0 border-l-0 border-r-0 flex items-center justify-between px-4 z-50">
        <div className="font-display font-bold text-lg">ARCX</div>
        <button onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* ── Sidebar (App Shell) ────────────────────────────────────────── */}
      <aside className={`
        fixed md:static inset-y-0 left-0 z-40 w-64 glassContainer rounded-none border-y-0 border-l-0 
        transform transition-transform duration-300 ease-in-out flex flex-col
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        {/* Logo */}
        <div className="h-20 flex items-center px-6 cursor-pointer" onClick={() => navigate('/dashboard')}>
          <span className="font-display font-bold text-xl tracking-tight text-black dark:text-white">ARCX</span>
        </div>

        {/* Scrollable Nav */}
        <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-6">
          
          <div>
            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 px-3">Menu</div>
            <div className="flex flex-col gap-1">
              <SidebarItem to="/dashboard" icon={LayoutDashboard} label="Dashboard" />
              <SidebarItem to="/portfolio" icon={Briefcase} label="Portfolio" />
            </div>
          </div>

          <div>
            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 px-3">Finance</div>
            <SidebarFolder label="Wallet" icon={Wallet}>
              <SidebarItem to="/wallet" exact icon={Folder} label="Overview" />
              {/* Ready for future separate Deposit/Withdraw pages */}
              {/* <SidebarItem to="/wallet/deposit" icon={ArrowDownToLine} label="Deposit" /> */}
              {/* <SidebarItem to="/wallet/withdraw" icon={ArrowUpFromLine} label="Withdraw" /> */}
            </SidebarFolder>
          </div>

          <div>
            <div className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 px-3">Account</div>
            <div className="flex flex-col gap-1">
              <SidebarItem to="/kyc" icon={ShieldCheck} label="KYC Status" />
              <SidebarItem to="/profile" icon={Settings} label="Settings" />
              {user?.is_staff && (
                <SidebarItem to="/admin-ops" icon={FileText} label="Treasury Ops" />
              )}
            </div>
          </div>

        </div>

        {/* Live ARCX Price Ticker */}
        <NavTicker />

        {/* User Profile Footer */}
        <div className="p-4 border-t border-black/5 dark:border-white/5">
          <div className="flex items-center justify-between p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer transition-colors" onClick={() => navigate('/profile')}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-black dark:bg-white flex items-center justify-center text-white dark:text-black text-xs font-bold shadow-md">
                {initials}
              </div>
              <div className="overflow-hidden">
                <div className="text-sm font-semibold truncate text-black dark:text-white">{user?.full_name || 'User'}</div>
                <div className="text-xs text-slate-500 truncate">{user?.email || ''}</div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main Content Area ──────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto h-screen relative pt-14 md:pt-0">
        
        {/* Top Header inside main content for search and theme toggle */}
        <header className="sticky top-0 z-30 h-16 px-8 flex items-center justify-between backdrop-blur-md bg-transparent">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input 
                type="text" 
                placeholder="Search..." 
                className="w-full bg-white/40 dark:bg-black/40 border border-white/50 dark:border-white/10 rounded-full pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 dark:focus:ring-white/20 transition-all placeholder:text-slate-500"
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <ThemeToggle />
          </div>
        </header>

        <div className="max-w-[1200px] mx-auto w-full p-6 md:p-8 pb-24">
          <Outlet />
        </div>
      </main>
      
      {/* Mobile overlay */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

    </div>
  )
}