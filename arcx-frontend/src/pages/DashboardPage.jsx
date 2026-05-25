import { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, PieChart, Pie, Cell
} from 'recharts'
import { TrendingUp, TrendingDown, RefreshCw, AlertTriangle, Plus, ArrowUpRight, Send } from 'lucide-react'
import { oracleApi } from '../api/index'
import { useAuthStore } from '../store/authStore'
import { format } from 'date-fns'
import { Link } from 'react-router-dom'

// ── Vault pie data matching screenshot ─────────────────────────
const VAULT_ALLOC = [
  { name: 'Stocks',  value: 35, color: '#324A8D' }, // Blue
  { name: 'Bonds',   value: 25, color: '#C5A059' }, // Gold
  { name: 'Cash',    value: 20, color: '#30D158' }, // Green
  { name: 'Crypto',  value: 20, color: '#8E44AD' }, // Purple
]

function QuickAction({ icon: Icon, label, to }) {
  return (
    <Link to={to} className="flex flex-col items-center gap-3 group">
      <div className="w-[60px] h-[60px] rounded-full bg-white/5 border border-white/10 backdrop-blur-md flex items-center justify-center transition-all duration-300 group-hover:bg-white/10 group-hover:scale-105 group-hover:shadow-[0_0_20px_rgba(255,255,255,0.05)]">
        <Icon size={24} className="text-text-primary transition-transform duration-300 group-hover:-translate-y-0.5" />
      </div>
      <span className="text-[13px] font-medium text-text-secondary group-hover:text-text-primary transition-colors">{label}</span>
    </Link>
  )
}

function StatCard({ label, value, sub, isUp, iconLabel, iconBg }) {
  return (
    <div className="card p-6 flex flex-col gap-4 group hover:border-white/20 transition-all duration-500">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold ${iconBg}`}>
            {iconLabel}
          </div>
          <span className="text-text-secondary text-[14px] font-medium tracking-wide">{label}</span>
        </div>
        <div className="px-2.5 py-1 bg-white/5 border border-white/10 rounded-lg text-[10px] text-text-secondary font-semibold uppercase tracking-wider">
          Price
        </div>
      </div>
      <div className="mt-2">
        <p className="font-display font-semibold text-3xl text-text-primary tracking-tight mb-1.5">{value}</p>
        {sub && (
          <p className={`text-[13px] font-medium ${isUp ? 'text-arcx-green' : 'text-arcx-red'}`}>
            {sub}
          </p>
        )}
      </div>
    </div>
  )
}

function NavTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const nav = payload[0]?.value
  return (
    <div className="bg-[#1C1C1E]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-4 text-sm">
      <p className="text-text-secondary font-medium mb-1.5">{label}</p>
      <p className="font-semibold text-arcx-gold text-lg">₹{Number(nav).toFixed(4)}</p>
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuthStore()
  const [navHistory, setNavHistory] = useState([])
  const [livePrice,  setLivePrice]  = useState(null)
  const [loading,    setLoading]    = useState(true)

  const balance = Number(user?.arcx_balance || 0)
  const costBasis = Number(user?.cost_basis_inr || 0)

  const fetchData = async () => {
    try {
      const [histData, priceData] = await Promise.all([
        oracleApi.getNAVHistory(30),
        oracleApi.getLivePrice(),
      ])
      const history = histData.history
        .slice()
        .reverse()
        .map(h => ({
          date: format(new Date(h.nav_date), 'dd'), // Just day numbers
          nav:  Number(h.nav_inr).toFixed(4),
        }))
      setNavHistory(history)
      setLivePrice(priceData)
    } catch (_) {}
    setLoading(false)
  }

  useEffect(() => {
    fetchData()
    const id = setInterval(fetchData, 30_000)
    return () => clearInterval(id)
  }, [])

  const navInr       = Number(livePrice?.nav_inr  || 0)
  const currentValue = balance * navInr
  const pnl          = currentValue - costBasis
  const pnlPct       = costBasis > 0 ? (pnl / costBasis) * 100 : 0

  const navTrend = navHistory.length >= 2
    ? Number(navHistory.at(-1)?.nav) - Number(navHistory[0]?.nav)
    : 0

  return (
    <div className="space-y-10 animate-fade-in pb-12 max-w-[1600px] mx-auto">

      {/* KYC banner */}
      {user?.kyc_status === 'pending' && (
        <div className="flex items-center gap-4 bg-arcx-gold/10 border border-arcx-gold/20 backdrop-blur-md rounded-[20px] px-6 py-4 shadow-lg">
          <div className="w-10 h-10 rounded-full bg-arcx-gold/20 flex items-center justify-center flex-shrink-0">
            <AlertTriangle size={20} className="text-arcx-gold" />
          </div>
          <div className="flex-1">
            <h4 className="text-[15px] font-semibold text-text-primary mb-0.5">Verification Required</h4>
            <p className="text-[14px] text-text-secondary">Complete KYC verification to unlock full deposit and transfer capabilities.</p>
          </div>
          <Link to="/kyc" className="btn-primary py-2 px-4 text-sm rounded-xl">Verify Now</Link>
        </div>
      )}

      {/* Quick Actions */}
      <div>
        <h2 className="font-display font-semibold text-2xl text-text-primary mb-6 tracking-tight">Quick Actions</h2>
        <div className="flex items-center gap-8">
          <QuickAction to="/wallet" icon={Plus} label="Deposit" />
          <QuickAction to="/wallet" icon={Send} label="Send" />
          <QuickAction to="/wallet" icon={ArrowUpRight} label="Withdraw" />
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="ARCX Balance"
          value={`₹${(balance * navInr).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`}
          sub="● Stable Value"
          isUp={true}
          iconLabel="A"
          iconBg="bg-arcx-gold/20 text-arcx-gold"
        />
        <StatCard
          label="Portfolio Value"
          value={`₹${currentValue.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`}
          sub={costBasis > 0 ? `+${pnlPct.toFixed(1)}%` : '+0.0%'}
          isUp={pnl >= 0}
          iconLabel={<TrendingUp size={16} />}
          iconBg="bg-arcx-gold/20 text-arcx-gold"
        />
        <StatCard
          label="Live NAV"
          value={`₹${navInr.toFixed(2)}`}
          sub={navTrend !== 0 ? `+${Math.abs(navTrend).toFixed(2)}` : '+0.00'}
          isUp={navTrend >= 0}
          iconLabel="$"
          iconBg="bg-arcx-gold/20 text-arcx-gold"
        />
        <StatCard
          label="Market Index (SPY)"
          value={`₹${(Number(livePrice?.spy_usd || 0) * Number(livePrice?.usd_inr || 0)).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`}
          sub="-0.11%"
          isUp={false}
          iconLabel={<TrendingUp size={16} />}
          iconBg="bg-[#324A8D]/30 text-[#324A8D]"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* NAV History */}
        <div className="card p-6 lg:col-span-2 relative">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h3 className="font-display font-semibold text-lg text-text-primary">NAV History</h3>
              <p className="text-sm text-text-secondary mt-1">1 ARCX price in INR — last 30 days</p>
            </div>
            <div className="flex bg-[#1A1A1A] rounded-lg p-1">
              {['1D', '1W', '1M', '1Y'].map(t => (
                <button key={t} className={`px-3 py-1 text-[13px] font-medium rounded-md ${t === '1M' ? 'bg-[#2C2C2E] text-arcx-gold' : 'text-text-secondary hover:text-text-primary'}`}>
                  {t}
                </button>
              ))}
            </div>
          </div>
          {loading ? (
            <div className="h-[250px] flex items-center justify-center text-text-secondary">Loading chart…</div>
          ) : navHistory.length === 0 ? (
            <div className="h-[250px] flex items-center justify-center text-text-secondary">No NAV data yet.</div>
          ) : (
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={navHistory} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorNav" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#C5A059" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#30D158" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="0" vertical={false} stroke="#2C2C2E" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#A0A0A0' }} tickLine={false} axisLine={false} dy={10} />
                  <YAxis tick={{ fontSize: 12, fill: '#A0A0A0' }} tickLine={false} axisLine={false} tickFormatter={v => `₹${v}`} domain={['auto', 'auto']} />
                  <Tooltip content={<NavTooltip />} cursor={{ stroke: '#2C2C2E', strokeWidth: 1, strokeDasharray: '4 4' }} />
                  {/* We use two lines to fake the gradient + line in Recharts or use an AreaChart. Let's just use AreaChart style with Line overlay if needed, or stick to Line */}
                  <Line type="monotone" dataKey="nav" stroke="#C5A059" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: '#C5A059', strokeWidth: 0 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Vault allocation */}
        <div className="card p-6">
          <h3 className="font-display font-semibold text-lg text-text-primary mb-1">Vault Allocation</h3>
          <p className="text-sm text-text-secondary mb-6">Backing asset split</p>
          <div className="h-[200px] mb-8">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={VAULT_ALLOC} cx="50%" cy="50%" innerRadius={0} outerRadius={100} dataKey="value" stroke="none">
                  {VAULT_ALLOC.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => `${v}%`} contentStyle={{ backgroundColor: '#1C1C1E', borderColor: '#2C2C2E', borderRadius: '8px' }} itemStyle={{ color: '#FFF' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-y-4 gap-x-2">
            {VAULT_ALLOC.map(a => (
              <div key={a.name} className="flex items-center gap-2 text-sm text-text-secondary">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: a.color }} />
                <span>{a.name}</span>
                <span className="ml-auto font-medium text-text-primary">{a.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}