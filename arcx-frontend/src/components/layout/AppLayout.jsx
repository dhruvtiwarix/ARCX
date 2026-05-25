import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'

const NAV = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/wallet',    label: 'Wallet'    },
  { to: '/portfolio', label: 'Portfolio' },
  { to: '/profile',   label: 'Settings'  },
]

export default function AppLayout() {
  const { user } = useAuthStore()
  const navigate = useNavigate()

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'AR'

  return (
    <div className="flex flex-col min-h-screen bg-[#F5F5F7] dark:bg-[#000000] transition-colors duration-300">
      
      {/* ── Apple-Style Global Nav ──────────────────────────────────────── */}
      <header className="h-[56px] w-full bg-[#FFFFFF]/80 dark:bg-[#000000]/80 backdrop-blur-xl border-b border-black/5 dark:border-white/5 sticky top-0 z-50 flex items-center justify-center transition-colors duration-300">
        <div className="max-w-[1024px] w-full px-4 flex items-center justify-between">
          
          {/* Left: Logo */}
          <div className="flex-shrink-0 flex items-center cursor-pointer" onClick={() => navigate('/dashboard')}>
            <span className="font-display font-bold text-[#1D1D1F] dark:text-[#F5F5F7] text-lg tracking-tighter transition-colors">A R C X</span>
          </div>

          {/* Center: Navigation Links */}
          <nav className="hidden md:flex items-center gap-8">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `text-[13px] font-inter tracking-wide transition-all duration-300
                   ${isActive 
                     ? 'text-[#1D1D1F] dark:text-[#F5F5F7] font-medium' 
                     : 'text-slate-500 dark:text-[#F5F5F7]/70 hover:text-[#1D1D1F] dark:hover:text-white'
                   }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Right: Search & Avatar */}
          <div className="flex items-center gap-5">
            <button className="text-slate-500 dark:text-[#F5F5F7]/70 hover:text-[#1D1D1F] dark:hover:text-white transition-colors">
              <Search size={16} strokeWidth={2} />
            </button>
            <NavLink to="/profile" className="flex items-center">
              <div className="w-[22px] h-[22px] rounded-full bg-black/5 dark:bg-white/10 flex items-center justify-center text-[9px] font-bold text-[#1D1D1F] dark:text-[#F5F5F7] hover:bg-black/10 dark:hover:bg-white/20 transition-colors">
                {initials}
              </div>
            </NavLink>
          </div>

        </div>
      </header>

      {/* ── Main content ──────────────────────────────────────────────── */}
      <main className="flex-1 w-full bg-[#F5F5F7] dark:bg-[#0A0A0A] transition-colors duration-300">
        <div className="max-w-[1024px] mx-auto w-full h-full px-4 pt-8 pb-20">
          <Outlet />
        </div>
      </main>

    </div>
  )
}