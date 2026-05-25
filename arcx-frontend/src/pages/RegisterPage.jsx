import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TrendingUp, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import * as authAPI from '../api/auth';

export default function RegisterPage() {
  const [form, setForm] = useState({ email: '', full_name: '', phone: '', password: '', confirmPassword: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError(null);
  };

  const validate = () => {
    if (!form.email || !form.full_name || !form.password) return 'All fields are required.';
    if (form.password.length < 8) return 'Password must be at least 8 characters.';
    if (form.password !== form.confirmPassword) return 'Passwords do not match.';
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return 'Invalid email address.';
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationError = validate();
    if (validationError) { setError(validationError); return; }

    setLoading(true);
    setError(null);

    try {
      await authAPI.register({
        email: form.email,
        full_name: form.full_name,
        phone: form.phone || undefined,
        password: form.password,
      });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.error || err.detail || 'Registration failed. The endpoint may not be available yet.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--arcx-bg-primary)] p-6">
        <div className="text-center animate-[slideUp_0.4s_ease-out]">
          <CheckCircle2 className="h-16 w-16 text-emerald-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-[var(--arcx-text-primary)] mb-2">Account Created</h2>
          <p className="text-sm text-[var(--arcx-text-secondary)]">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--arcx-bg-primary)] p-6">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-emerald-400">
            <TrendingUp className="h-5 w-5 text-[#0a0e1a]" strokeWidth={2.5} />
          </div>
          <span className="text-xl font-bold gradient-text">ARCX</span>
        </div>

        <h2 className="text-xl font-bold text-[var(--arcx-text-primary)] mb-1">Create your account</h2>
        <p className="text-sm text-[var(--arcx-text-secondary)] mb-8">Start investing in the ARCX vault</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="reg-name" className="block text-xs font-medium text-[var(--arcx-text-secondary)] mb-1.5">Full Name</label>
            <input
              id="reg-name"
              name="full_name"
              type="text"
              value={form.full_name}
              onChange={handleChange}
              placeholder="John Doe"
              required
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
            />
          </div>

          <div>
            <label htmlFor="reg-email" className="block text-xs font-medium text-[var(--arcx-text-secondary)] mb-1.5">Email</label>
            <input
              id="reg-email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              placeholder="you@example.com"
              required
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
            />
          </div>

          <div>
            <label htmlFor="reg-phone" className="block text-xs font-medium text-[var(--arcx-text-secondary)] mb-1.5">Phone <span className="text-white/30">(optional)</span></label>
            <input
              id="reg-phone"
              name="phone"
              type="tel"
              value={form.phone}
              onChange={handleChange}
              placeholder="+91 98765 43210"
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="reg-pass" className="block text-xs font-medium text-[var(--arcx-text-secondary)] mb-1.5">Password</label>
              <input
                id="reg-pass"
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                placeholder="Min 8 characters"
                required
                className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
              />
            </div>
            <div>
              <label htmlFor="reg-confirm" className="block text-xs font-medium text-[var(--arcx-text-secondary)] mb-1.5">Confirm</label>
              <input
                id="reg-confirm"
                name="confirmPassword"
                type="password"
                value={form.confirmPassword}
                onChange={handleChange}
                placeholder="Re-enter password"
                required
                className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
              />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/[0.08] border border-red-500/15 animate-[slideUp_0.3s_ease-out]">
              <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
              <span className="text-sm text-red-400">{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 text-[#0a0e1a] text-sm font-semibold transition-all duration-200 hover:shadow-[0_0_25px_-5px_rgba(34,211,238,0.4)] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Creating account...</> : 'Create Account'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[var(--arcx-text-secondary)]">
          Already have an account?{' '}
          <Link to="/login" className="text-cyan-400 hover:text-cyan-300 font-medium transition">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
