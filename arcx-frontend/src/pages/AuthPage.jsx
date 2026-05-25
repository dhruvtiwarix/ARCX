import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, ArrowRight, Loader2, BarChart2, ShieldCheck, CreditCard, ChevronRight, ChevronLeft } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

function LoginForm({ onSwitch }) {
  const [form, setForm]   = useState({ email: '', password: '' })
  const [show, setShow]   = useState(false)
  const { login, loading, error, clearError } = useAuthStore()
  const navigate = useNavigate()

  const handle = e => { clearError(); setForm(p => ({ ...p, [e.target.name]: e.target.value })) }

  const submit = async e => {
    e.preventDefault()
    const res = await login(form)
    if (res.success) navigate('/dashboard')
  }

  return (
    <form onSubmit={submit} className="space-y-5 animate-fade-in">
      <div>
        <label className="block text-[14px] font-medium text-text-secondary mb-2">Email</label>
        <input className="input" type="email" name="email" value={form.email}
               onChange={handle} placeholder="you@example.com" required autoFocus />
      </div>
      <div>
        <label className="block text-[14px] font-medium text-text-secondary mb-2">Password</label>
        <div className="relative">
          <input className="input pr-10" type={show ? 'text' : 'password'}
                 name="password" value={form.password} onChange={handle}
                 placeholder="••••••••" required />
          <button type="button" onClick={() => setShow(p => !p)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors">
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-[13px] text-arcx-red bg-arcx-red/10 border border-arcx-red/20 rounded-xl px-4 py-3">
          {error}
        </p>
      )}

      <button type="submit" className="btn-primary w-full mt-4" disabled={loading}>
        {loading ? <Loader2 size={18} className="animate-spin" /> : <>Sign In <ArrowRight size={18} /></>}
      </button>

      <p className="text-center text-[14px] text-text-secondary mt-6">
        Don't have an account?{' '}
        <button type="button" onClick={onSwitch} className="text-arcx-gold font-semibold hover:text-white transition-colors">
          Create one
        </button>
      </p>
    </form>
  )
}

function RegisterForm({ onSwitch }) {
  const [form, setForm] = useState({ email: '', password: '', full_name: '', phone: '' })
  const [show, setShow] = useState(false)
  const { register, loading, error, clearError } = useAuthStore()
  const navigate = useNavigate()

  const handle = e => { clearError(); setForm(p => ({ ...p, [e.target.name]: e.target.value })) }

  const submit = async e => {
    e.preventDefault()
    const res = await register(form)
    if (res.success) navigate('/dashboard')
  }

  return (
    <form onSubmit={submit} className="space-y-5 animate-fade-in">
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="block text-[14px] font-medium text-text-secondary mb-2">Full name</label>
          <input className="input" type="text" name="full_name" value={form.full_name}
                 onChange={handle} placeholder="John Doe" required autoFocus />
        </div>
        <div className="col-span-2">
          <label className="block text-[14px] font-medium text-text-secondary mb-2">Email</label>
          <input className="input" type="email" name="email" value={form.email}
                 onChange={handle} placeholder="you@example.com" required />
        </div>
        <div className="col-span-2">
          <label className="block text-[14px] font-medium text-text-secondary mb-2">Password</label>
          <div className="relative">
            <input className="input pr-10" type={show ? 'text' : 'password'}
                   name="password" value={form.password} onChange={handle}
                   placeholder="At least 8 characters" minLength={8} required />
            <button type="button" onClick={() => setShow(p => !p)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors">
              {show ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <p className="text-[13px] text-arcx-red bg-arcx-red/10 border border-arcx-red/20 rounded-xl px-4 py-3">
          {error}
        </p>
      )}

      <button type="submit" className="btn-primary w-full mt-4" disabled={loading}>
        {loading
          ? <Loader2 size={18} className="animate-spin" />
          : <>Create Account <ArrowRight size={18} /></>}
      </button>

      <p className="text-center text-[14px] text-text-secondary mt-6">
        Already have an account?{' '}
        <button type="button" onClick={onSwitch} className="text-arcx-gold font-semibold hover:text-white transition-colors">
          Sign In
        </button>
      </p>
    </form>
  )
}

function OnboardingCarousel() {
  const [currentSlide, setCurrentSlide] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide(p => (p + 1) % 3)
    }, 5000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="flex flex-col h-full relative">
      <div className="flex-1 flex items-center justify-center relative overflow-hidden">
        {/* Slide 1: Meet ARCX */}
        <div className={`absolute inset-0 flex flex-col items-center justify-center transition-opacity duration-1000 ${currentSlide === 0 ? 'opacity-100 z-10' : 'opacity-0 z-0'}`}>
          <div className="w-32 h-32 rounded-full bg-gradient-to-br from-arcx-gold to-yellow-600 shadow-[0_0_80px_rgba(225,195,137,0.4)] flex items-center justify-center mb-10">
            <span className="font-display font-bold text-[#000000] text-5xl">AX</span>
          </div>
          <div className="px-5 py-2 rounded-full bg-[#111111] border border-arcx-gold/30 mb-8">
            <span className="text-arcx-gold text-xs font-semibold tracking-widest uppercase">Yield-Bearing Currency</span>
          </div>
          <h1 className="font-display text-5xl font-semibold text-text-primary mb-6 tracking-tight">Meet ARCX</h1>
          <p className="text-text-secondary text-lg text-center max-w-md leading-relaxed">
            A global financial engine that beats inflation. Your money grows automatically — just by holding it.
          </p>
        </div>

        {/* Slide 2: Asset Backing */}
        <div className={`absolute inset-0 flex flex-col items-center justify-center transition-opacity duration-1000 ${currentSlide === 1 ? 'opacity-100 z-10' : 'opacity-0 z-0'}`}>
          <span className="text-arcx-gold text-xs font-bold tracking-[0.2em] uppercase mb-4">Institutional-Grade</span>
          <h1 className="font-display text-4xl font-semibold text-text-primary mb-10">Asset Backing</h1>
          
          <div className="w-full max-w-sm space-y-3 mb-12">
            {[
              { label: 'Stocks', value: '40%', color: '#324A8D' },
              { label: 'Bonds', value: '30%', color: '#C5A059' },
              { label: 'Gold', value: '20%', color: '#8E44AD' },
              { label: 'Cash Reserves', value: '10%', color: '#30D158' },
            ].map(asset => (
              <div key={asset.label} className="flex items-center justify-between p-4 rounded-2xl bg-[#111111]/80 border border-white/5 backdrop-blur-md">
                <div className="flex items-center gap-4">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: asset.color }} />
                  <span className="text-text-primary font-medium">{asset.label}</span>
                </div>
                <span className="text-text-primary font-semibold ">{asset.value}</span>
              </div>
            ))}
          </div>
          <p className="text-text-secondary text-center max-w-sm">
            Every ARCX is backed by real assets. You own a piece of the global economy.
          </p>
        </div>

        {/* Slide 3: Why Use ARCX */}
        <div className={`absolute inset-0 flex flex-col items-center justify-center transition-opacity duration-1000 ${currentSlide === 2 ? 'opacity-100 z-10' : 'opacity-0 z-0'}`}>
          <div className="w-full max-w-md space-y-4 mb-12">
            {[
              { icon: BarChart2, color: 'text-arcx-green', bg: 'bg-arcx-green/10', title: 'Beat Inflation', sub: 'Your wealth grows automatically, every single day.' },
              { icon: ShieldCheck, color: 'text-[#0A84FF]', bg: 'bg-[#0A84FF]/10', title: 'Zero Volatility', sub: 'Gold & bonds protect you from market crashes.' },
              { icon: CreditCard, color: 'text-arcx-gold', bg: 'bg-arcx-gold/10', title: 'Spend Like Cash', sub: 'Use anywhere UPI is accepted — instant & free.' },
            ].map((f, i) => (
              <div key={i} className="flex items-center gap-5 p-5 rounded-[24px] bg-[#111111] border border-white/5">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${f.bg}`}>
                  <f.icon size={24} className={f.color} />
                </div>
                <div>
                  <h3 className="text-text-primary font-semibold text-lg mb-1">{f.title}</h3>
                  <p className="text-text-secondary text-sm leading-relaxed">{f.sub}</p>
                </div>
              </div>
            ))}
          </div>
          <h1 className="font-display text-4xl font-semibold text-text-primary mb-4">Start Your Journey</h1>
          <p className="text-text-secondary text-center">Join thousands growing their wealth with ARCX.</p>
        </div>
      </div>

      {/* Slide Indicators */}
      <div className="absolute bottom-12 left-0 right-0 flex items-center justify-center gap-3">
        {[0, 1, 2].map(i => (
          <button 
            key={i}
            onClick={() => setCurrentSlide(i)}
            className={`h-1.5 rounded-full transition-all duration-500 ${currentSlide === i ? 'w-8 bg-arcx-gold' : 'w-2 bg-white/20 hover:bg-white/40'}`}
          />
        ))}
      </div>
    </div>
  )
}

export default function AuthPage() {
  const [tab, setTab] = useState('login')

  return (
    <div className="min-h-screen bg-[#000000] flex">

      {/* Left panel — Onboarding Carousel */}
      <div className="hidden lg:block w-[55%] relative">
        {/* Subtle background glow */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-arcx-gold/5 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#0A84FF]/5 rounded-full blur-[120px] pointer-events-none" />
        
        <OnboardingCarousel />
      </div>

      {/* Right panel — Auth Form */}
      <div className="w-full lg:w-[45%] flex items-center justify-center p-6 lg:p-12 z-10">
        <div className="w-full max-w-[440px]">
          
          {/* Auth Card wrapped in Glassmorphism */}
          <div className="bg-[#111111]/80 backdrop-blur-2xl border border-white/5 rounded-[32px] p-8 md:p-10 shadow-2xl shadow-black/80 relative overflow-hidden">
            
            {/* Subtle top glare */}
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />

            {/* Mobile branding */}
            <div className="flex items-center gap-3 mb-10 lg:hidden justify-center">
              <div className="w-10 h-10 rounded-[12px] bg-gradient-to-br from-arcx-gold/30 to-arcx-gold/5 flex items-center justify-center border border-arcx-gold/20 shadow-lg shadow-arcx-gold/10">
                <span className="font-display font-bold text-arcx-gold text-xl">A</span>
              </div>
              <span className="font-display font-semibold text-text-primary text-2xl tracking-wider">ARCX</span>
            </div>

            <div className="mb-10 text-center lg:text-left">
              <h2 className="font-display font-semibold text-3xl text-text-primary tracking-tight mb-3">
                {tab === 'login' ? 'Welcome back' : 'Create an account'}
              </h2>
              <p className="text-[15px] text-text-secondary">
                {tab === 'login' ? 'Enter your details to access your vault.' : 'Start protecting your wealth from inflation today.'}
              </p>
            </div>

            {/* Tab toggle (Optional, we integrated it below the forms as text buttons for a cleaner look, but kept here if requested. Actually, removing the tab toggle pill block makes it look much more Apple-like. Let's rely on the text links at the bottom of the forms.) */}

            {tab === 'login'
              ? <LoginForm    onSwitch={() => setTab('register')} />
              : <RegisterForm onSwitch={() => setTab('login')} />
            }
          </div>

        </div>
      </div>
    </div>
  )
}