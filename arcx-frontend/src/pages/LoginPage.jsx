import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TrendingUp, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';
import useStore from '../store/useStore';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const login = useStore((s) => s.login);
  const authLoading = useStore((s) => s.authLoading);
  const authError = useStore((s) => s.authError);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(username, password);
      navigate('/dashboard');
    } catch {
      // Error handled by store
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-center items-center relative overflow-hidden bg-[#060a14]">
        {/* Animated background gradient */}
        <div className="absolute inset-0">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] animate-pulse" />
          <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-emerald-500/10 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '1s' }} />
        </div>

        <div className="relative z-10 text-center px-12">
          <div className="flex items-center justify-center gap-3 mb-8">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-emerald-400 shadow-[0_0_30px_-5px_rgba(34,211,238,0.4)]">
              <TrendingUp className="h-7 w-7 text-[#0a0e1a]" strokeWidth={2.5} />
            </div>
            <span className="text-3xl font-bold tracking-tight gradient-text">ARCX</span>
          </div>
          <h1 className="text-2xl font-bold text-[var(--arcx-text-primary)] mb-3">
            Institutional-Grade<br />Multi-Asset Vault
          </h1>
          <p className="text-sm text-[var(--arcx-text-secondary)] max-w-sm leading-relaxed">
            Real-time NAV tracking. Zero-fee transfers. Automated rebalancing.
            Built with the same architecture that powers Wall Street.
          </p>

          {/* Feature Pills */}
          <div className="flex flex-wrap justify-center gap-2 mt-8">
            {['SHA256 Audit Trail', 'Circuit Breakers', 'TWAP Oracle', 'Atomic Transfers'].map((f) => (
              <span key={f} className="px-3 py-1.5 rounded-full text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-[var(--arcx-text-secondary)]">
                {f}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Right Panel — Login Form */}
      <div className="flex-1 flex items-center justify-center p-6 bg-[var(--arcx-bg-primary)]">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-emerald-400">
              <TrendingUp className="h-5 w-5 text-[#0a0e1a]" strokeWidth={2.5} />
            </div>
            <span className="text-xl font-bold gradient-text">ARCX</span>
          </div>

          <h2 className="text-xl font-bold text-[var(--arcx-text-primary)] mb-1">Welcome back</h2>
          <p className="text-sm text-[var(--arcx-text-secondary)] mb-8">Sign in to your vault dashboard</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="login-username" className="block text-xs font-medium text-[var(--arcx-text-secondary)] mb-1.5">
                Email
              </label>
              <input
                id="login-username"
                type="email"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your email"
                required
                className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
              />
            </div>

            <div>
              <label htmlFor="login-password" className="block text-xs font-medium text-[var(--arcx-text-secondary)] mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  className="w-full px-4 py-2.5 pr-10 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--arcx-text-secondary)] hover:text-[var(--arcx-text-primary)] transition"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {authError && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/[0.08] border border-red-500/15 animate-[slideUp_0.3s_ease-out]">
                <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
                <span className="text-sm text-red-400">{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading || !username || !password}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 text-[#0a0e1a] text-sm font-semibold transition-all duration-200 hover:shadow-[0_0_25px_-5px_rgba(34,211,238,0.4)] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {authLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--arcx-text-secondary)]">
            Don't have an account?{' '}
            <Link to="/register" className="text-cyan-400 hover:text-cyan-300 font-medium transition">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
