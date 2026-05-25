import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Wallet, ShieldCheck, LogOut,
  Bell, ChevronRight, Search, PieChart
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/wallet',    icon: Wallet,          label: 'Wallet'    },
  { to: '/portfolio', icon: PieChart,        label: 'Portfolio' },
  { to: '/kyc',       icon: ShieldCheck,     label: 'KYC'       },
]

function KYCBadge({ status }) {
  if (status === 'approved') return <span className="text-[10px] uppercase font-bold tracking-widest text-arcx-green">Verified</span>
  if (status === 'pending')  return <span className="text-[10px] uppercase font-bold tracking-widest text-arcx-gold">Pending</span>
  return <span className="text-[10px] uppercase font-bold tracking-widest text-arcx-red">Unverified</span>
}

export default function AppLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth')
  }

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'AR'

  return (
    <div className="flex h-screen overflow-hidden bg-[#000000]">

      {/* ── Sidebar ───────────────────────────────────────────────────── */}
      <aside className="w-[260px] flex-shrink-0 bg-[#000000] border-r border-white/5 flex flex-col pt-8">

        {/* Logo */}
        <div className="flex items-center gap-3.5 px-8 pb-10">
          <div className="w-9 h-9 rounded-[10px] bg-gradient-to-br from-arcx-gold/30 to-arcx-gold/5 flex items-center justify-center border border-arcx-gold/20 shadow-lg shadow-arcx-gold/10">
            <span className="font-display font-bold text-arcx-gold text-lg">A</span>
          </div>
          <span className="font-display font-semibold text-text-primary text-xl tracking-wider">ARCX</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-5 space-y-2.5">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3.5 px-4 py-3 rounded-2xl text-[14px] font-medium transition-all duration-300 group
                 ${isActive
                   ? 'bg-white/10 text-text-primary shadow-sm backdrop-blur-md'
                   : 'text-text-secondary hover:bg-white/5 hover:text-text-primary'}`
              }
            >
              <Icon size={20} className="transition-transform group-hover:scale-110 duration-300" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="p-5 border-t border-white/5 bg-gradient-to-t from-black/50 to-transparent">
          <div className="flex items-center gap-3.5 px-2 mb-5">
            <div className="w-10 h-10 rounded-full bg-[#111111] border border-white/10 flex items-center justify-center text-arcx-gold text-sm font-bold shadow-md">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-text-primary text-[14px] font-medium truncate">
                {user?.full_name || 'Loading…'}
              </p>
              {user?.kyc_status && (
                <div className="mt-0.5">
                  <KYCBadge status={user.kyc_status} />
                </div>
              )}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-2xl
                       bg-white/5 border border-white/5 text-text-secondary hover:bg-white/10 hover:text-arcx-red hover:border-arcx-red/20
                       text-[14px] font-medium transition-all duration-300"
          >
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#0A0A0A] rounded-tl-[40px] border-l border-t border-white/5 mt-2 shadow-2xl">

        {/* Top bar */}
        <header className="h-[80px] flex items-center justify-between px-10 flex-shrink-0 backdrop-blur-xl bg-[#0A0A0A]/80 border-b border-white/5 sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-medium text-text-secondary tracking-wide">
              {new Date().toLocaleDateString('en-US', {
                weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
              })}
            </span>
          </div>
          <div className="flex items-center gap-6">
            <div className="relative hidden md:block w-72">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-secondary" size={16} />
              <input 
                type="text" 
                placeholder="Search anything..." 
                className="w-full bg-[#111111] border border-white/5 rounded-full py-2.5 pl-11 pr-5 text-[14px] text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-arcx-gold/50 focus:bg-[#151515] transition-all duration-300"
              />
            </div>
            <button className="w-10 h-10 rounded-full bg-white/5 border border-white/5 flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-white/10 transition-all duration-300">
              <Bell size={18} />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-10 pt-8 scroll-smooth">
          <Outlet />
        </main>
      </div>
    </div>
  )
}