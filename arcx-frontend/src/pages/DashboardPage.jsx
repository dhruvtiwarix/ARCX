import { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts'
import { TrendingUp, TrendingDown, RefreshCw, AlertTriangle, ArrowUpRight, Send, ArrowDownLeft, Clock, ArrowLeftRight } from 'lucide-react'
import { oracleApi, walletApi } from '../api/index'
import { useAuthStore } from '../store/authStore'
import { format } from 'date-fns'
import { Link } from 'react-router-dom'

// ── Vault pie data ──────────────────────────────────────────────
const VAULT_ALLOC = [
  { name: 'Stocks',  value: 40, color: '#324A8D' },
  { name: 'Bonds',   value: 30, color: '#C5A059' },
  { name: 'Gold',    value: 20, color: '#30D158' },
  { name: 'Cash',    value: 10, color: '#8E44AD' },
]

// ── Transaction Row Logic ───────────────────────────────────────
const TX_META = {
  deposit:  { label: 'Fiat Deposit',  colorLight: 'text-emerald-600', colorDark: 'dark:text-emerald-400', bgLight: 'bg-emerald-100', bgDark: 'dark:bg-emerald-500/10', icon: ArrowDownLeft },
  withdraw: { label: 'Withdrawal',    colorLight: 'text-[#1D1D1F]',   colorDark: 'dark:text-[#F5F5F7]',       bgLight: 'bg-slate-200',   bgDark: 'dark:bg-white/10',     icon: ArrowUpRight  },
  transfer: { label: 'Transfer',      colorLight: 'text-[#C5A059]',   colorDark: 'dark:text-arcx-gold',   bgLight: 'bg-arcx-gold/20',bgDark: 'dark:bg-arcx-gold/10', icon: Send },
  dividend: { label: 'Yield Dividend',colorLight: 'text-[#C5A059]',   colorDark: 'dark:text-arcx-gold',   bgLight: 'bg-arcx-gold/20',bgDark: 'dark:bg-arcx-gold/10', icon: ArrowDownLeft  },
}

function TxRow({ tx }) {
  const meta = TX_META[tx.tx_type] || TX_META.deposit
  const Icon = meta.icon
  const amt  = Number(tx.amount_arcx)

  return (
    <div className="flex items-center justify-between p-4 border-b border-black/5 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer group">
      <div className="flex items-center gap-4">
        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors ${meta.bgLight} ${meta.bgDark}`}>
          <Icon size={16} className={`${meta.colorLight} ${meta.colorDark} transition-colors`} />
        </div>
        <div>
          <p className="text-sm font-bold text-[#1D1D1F] dark:text-[#F5F5F7] group-hover:text-arcx-gold transition-colors">{meta.label}</p>
          <p className="text-xs text-slate-500 mt-0.5 transition-colors">
            {format(new Date(tx.created_at), 'MMM dd, hh:mm a')}
          </p>
        </div>
      </div>
      <div className="text-right">
        <p className={`text-sm font-bold transition-colors ${amt >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-[#1D1D1F] dark:text-[#F5F5F7]'}`}>
          {amt >= 0 ? '+' : ''}{amt.toFixed(6)} ARCX
        </p>
        <div className="flex items-center justify-end gap-2 mt-0.5">
          {Number(tx.amount_inr) !== 0 && (
            <p className="text-xs text-slate-500 transition-colors">
              ₹{Number(tx.amount_inr).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
            </p>
          )}
          <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider font-bold transition-colors ${tx.status === 'completed' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' : 'bg-slate-200 dark:bg-slate-500/20 text-slate-600 dark:text-slate-400'}`}>
            {tx.status}
          </span>
        </div>
      </div>
    </div>
  )
}

function NavTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const nav = payload[0]?.value
  return (
    <div className="bg-white/95 dark:bg-[#1C1C1E]/95 backdrop-blur-xl border border-black/10 dark:border-white/10 rounded-xl shadow-2xl px-4 py-3 text-sm transition-colors">
      <p className="text-slate-500 dark:text-slate-400 font-medium mb-1 text-[11px] uppercase tracking-widest">{label}</p>
      <p className="font-semibold text-[#1D1D1F] dark:text-[#F5F5F7] text-base">₹{Number(nav).toFixed(4)}</p>
    </div>
  )
}

function BentoCard({ children, className = "" }) {
  return (
    <div className={`bg-white dark:bg-[#1C1C1E] border border-black/5 dark:border-white/5 rounded-[24px] p-6 shadow-sm dark:shadow-none transition-colors duration-300 ${className}`}>
      {children}
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuthStore()
  const [navHistory, setNavHistory] = useState([])
  const [livePrice,  setLivePrice]  = useState(null)
  const [recentTxns, setRecentTxns] = useState([])
  const [loading,    setLoading]    = useState(true)

  const balance = Number(user?.arcx_balance || 0)
  const costBasis = Number(user?.cost_basis_inr || 0)

  const fetchData = async () => {
    try {
      const [histData, priceData, txData] = await Promise.all([
        oracleApi.getNAVHistory(30),
        oracleApi.getLivePrice(),
        walletApi.getHistory(3),
      ])
      const history = histData.history
        .slice()
        .reverse()
        .map(h => ({
          date: format(new Date(h.nav_date), 'dd MMM'),
          nav:  Number(h.nav_inr).toFixed(4),
        }))
      setNavHistory(history)
      setLivePrice(priceData)
      setRecentTxns(txData.transactions || [])
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
    <div className="animate-fade-in transition-colors duration-300">

      {/* KYC Banner */}
      {user?.kyc_status === 'pending' && (
        <div className="flex items-center gap-4 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 backdrop-blur-md rounded-2xl px-6 py-4 mb-8 transition-colors">
          <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-500/20 flex items-center justify-center flex-shrink-0 transition-colors">
            <AlertTriangle size={18} className="text-amber-600 dark:text-amber-400" />
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-bold text-amber-900 dark:text-[#F5F5F7] transition-colors">Verification Required</h4>
            <p className="text-xs text-amber-700 dark:text-slate-400 mt-0.5 transition-colors">Complete KYC to unlock full deposits and transfers.</p>
          </div>
          <Link to="/profile" className="px-4 py-2 bg-amber-500 text-white dark:text-black text-xs font-bold uppercase tracking-wider rounded-lg hover:bg-amber-600 dark:hover:bg-amber-400 transition-colors">
            Verify Now
          </Link>
        </div>
      )}

      {/* Hero Section */}
      <div className="mb-10">
        <h2 className="text-[11px] font-bold text-slate-500 dark:text-slate-500 uppercase tracking-widest mb-2 transition-colors">Total Portfolio Value</h2>
        <div className="flex items-end gap-4">
          <h1 className="font-display font-light text-[56px] leading-none text-[#1D1D1F] dark:text-[#F5F5F7] tracking-tight transition-colors">
            ₹{currentValue.toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })}
          </h1>
          <div className={`flex items-center gap-1 mb-2 px-2.5 py-1 rounded-full text-xs font-bold transition-colors ${pnl >= 0 ? 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-400' : 'bg-red-100 dark:bg-red-500/15 text-red-700 dark:text-red-400'}`}>
            {pnl >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {pnl >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
          </div>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-3 transition-colors">
          {balance.toLocaleString('en-US', { maximumFractionDigits: 4 })} ARCX • Cost Basis: ₹{costBasis.toLocaleString('en-IN')}
        </p>
      </div>

      {/* Bento Box Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">

        {/* Span-2 Chart */}
        <BentoCard className="lg:col-span-2 relative min-h-[360px] flex flex-col">
          <div className="flex items-start justify-between mb-8">
            <div>
              <h2 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-1 transition-colors">ARCX NAV Price</h2>
              <div className="flex items-center gap-3">
                <span className="text-2xl font-display font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">₹{navInr.toFixed(4)}</span>
                <span className={`text-xs font-bold transition-colors ${navTrend >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {navTrend >= 0 ? '+' : ''}{navTrend.toFixed(4)} (30D)
                </span>
              </div>
            </div>
            <div className="flex bg-slate-100 dark:bg-white/5 rounded-lg p-1 border border-black/5 dark:border-white/5 transition-colors">
              {['1D', '1W', '1M', '1Y'].map(t => (
                <button key={t} className={`px-3 py-1 text-[11px] font-bold rounded-md transition-colors ${t === '1M' ? 'bg-white dark:bg-white/10 text-[#1D1D1F] dark:text-[#F5F5F7] shadow-sm dark:shadow-none' : 'text-slate-500 hover:text-[#1D1D1F] dark:hover:text-slate-300'}`}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">Loading chart…</div>
          ) : navHistory.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">No NAV data yet.</div>
          ) : (
            <div className="flex-1 w-full min-h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={navHistory} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                  <XAxis dataKey="date" hide />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip content={<NavTooltip />} cursor={{ stroke: 'rgba(128,128,128,0.2)', strokeWidth: 1 }} />
                  <Line type="monotone" dataKey="nav" stroke="#C5A059" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: '#C5A059', strokeWidth: 0 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </BentoCard>

        {/* Right Column Stack */}
        <div className="flex flex-col gap-6">
          
          {/* Quick Actions */}
          <BentoCard className="flex-1">
            <h2 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-5 transition-colors">Quick Actions</h2>
            <div className="grid grid-cols-3 gap-4">
              <Link to="/wallet" className="flex flex-col items-center gap-2 group">
                <div className="w-12 h-12 rounded-full bg-slate-50 dark:bg-white/5 border border-black/5 dark:border-white/5 flex items-center justify-center group-hover:bg-arcx-gold/10 group-hover:border-arcx-gold/20 transition-all">
                  <ArrowDownLeft size={18} className="text-slate-400 dark:text-slate-300 group-hover:text-arcx-gold" />
                </div>
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 group-hover:text-[#1D1D1F] dark:group-hover:text-white transition-colors">Deposit</span>
              </Link>
              <Link to="/wallet" className="flex flex-col items-center gap-2 group">
                <div className="w-12 h-12 rounded-full bg-slate-50 dark:bg-white/5 border border-black/5 dark:border-white/5 flex items-center justify-center group-hover:bg-arcx-gold/10 group-hover:border-arcx-gold/20 transition-all">
                  <Send size={18} className="text-slate-400 dark:text-slate-300 group-hover:text-arcx-gold" />
                </div>
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 group-hover:text-[#1D1D1F] dark:group-hover:text-white transition-colors">Transfer</span>
              </Link>
              <Link to="/wallet" className="flex flex-col items-center gap-2 group">
                <div className="w-12 h-12 rounded-full bg-slate-50 dark:bg-white/5 border border-black/5 dark:border-white/5 flex items-center justify-center group-hover:bg-arcx-gold/10 group-hover:border-arcx-gold/20 transition-all">
                  <ArrowUpRight size={18} className="text-slate-400 dark:text-slate-300 group-hover:text-arcx-gold" />
                </div>
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 group-hover:text-[#1D1D1F] dark:group-hover:text-white transition-colors">Withdraw</span>
              </Link>
            </div>
          </BentoCard>

          {/* Vault Allocation Mini */}
          <BentoCard className="flex-1">
            <h2 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-4 transition-colors">Vault Allocation</h2>
            <div className="flex items-center gap-4">
              <div className="w-[80px] h-[80px] flex-shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={VAULT_ALLOC} cx="50%" cy="50%" innerRadius={25} outerRadius={40} dataKey="value" stroke="none">
                      {VAULT_ALLOC.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex-1 grid grid-cols-2 gap-y-2">
                {VAULT_ALLOC.map(a => (
                  <div key={a.name} className="flex flex-col">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: a.color }} />
                      <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">{a.name}</span>
                    </div>
                    <span className="text-xs font-bold text-[#1D1D1F] dark:text-[#F5F5F7] pl-3 transition-colors">{a.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          </BentoCard>

        </div>
      </div>

      {/* Recent Activity Mini-Feed */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest transition-colors">Recent Activity</h2>
          <Link to="/wallet" className="text-[11px] font-bold text-arcx-gold hover:text-[#1D1D1F] dark:hover:text-white transition-colors uppercase tracking-widest">View All</Link>
        </div>
        <div className="bg-white dark:bg-[#1C1C1E] border border-black/5 dark:border-white/5 rounded-[24px] overflow-hidden shadow-sm dark:shadow-none transition-colors duration-300">
          
          {loading ? (
            <div className="flex items-center justify-center py-10 text-slate-500 text-sm gap-2">
              <RefreshCw size={16} className="animate-spin" /> Loading recent activity…
            </div>
          ) : recentTxns.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-slate-500 transition-colors">
              <ArrowLeftRight size={24} className="mb-2 opacity-50" />
              <p className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] mb-1 transition-colors">No activity yet</p>
            </div>
          ) : (
            <div className="divide-y divide-black/5 dark:divide-white/5 transition-colors">
              {recentTxns.map(tx => <TxRow key={tx.id} tx={tx} />)}
            </div>
          )}

        </div>
      </div>

    </div>
  )
}