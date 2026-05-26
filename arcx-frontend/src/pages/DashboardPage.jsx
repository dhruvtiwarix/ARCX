import { useEffect, useState, useRef } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, ReferenceLine, CartesianGrid
} from 'recharts'
import { TrendingUp, TrendingDown, RefreshCw, AlertTriangle, ArrowUpRight, Send, ArrowDownLeft, ArrowLeftRight, Plus } from 'lucide-react'
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
  deposit:  { label: 'Fiat Deposit',  colorLight: 'text-emerald-600', colorDark: 'dark:text-emerald-400', bgLight: 'bg-emerald-100', bgDark: 'dark:bg-emerald-500/10', icon: Plus },
  withdraw: { label: 'Withdrawal',    colorLight: 'text-[#1D1D1F]',   colorDark: 'dark:text-[#F5F5F7]',       bgLight: 'bg-slate-200',   bgDark: 'dark:bg-white/10',     icon: ArrowDownLeft  },
  transfer: { label: 'Transfer',      colorLight: 'text-[#C5A059]',   colorDark: 'dark:text-arcx-gold',   bgLight: 'bg-arcx-gold/20',bgDark: 'dark:bg-arcx-gold/10', icon: ArrowUpRight },
  dividend: { label: 'Yield Dividend',colorLight: 'text-[#C5A059]',   colorDark: 'dark:text-arcx-gold',   bgLight: 'bg-arcx-gold/20',bgDark: 'dark:bg-arcx-gold/10', icon: Plus  },
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
  const nav   = Number(payload[0]?.value)
  const first = Number(payload[0]?.payload?.open ?? nav)
  const delta = nav - first
  const isUp  = delta >= 0
  return (
    <div className="glassContainer px-4 py-3 min-w-[140px] z-50">
      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1 z-10">{label}</p>
      <p className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] text-[17px] leading-none z-10">&#8377;{nav.toFixed(4)}</p>
    </div>
  )
}

function BentoCard({ children, className = "" }) {
  return (
    <div className={`glassContainer p-6 ${className}`}>
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
  const [activeRange, setActiveRange] = useState('1M')

  const balance = Number(user?.arcx_balance || 0)
  const costBasis = Number(user?.cost_basis_inr || 0)

  const fetchData = async () => {
    try {
      const [histData, priceData, txData] = await Promise.all([
        oracleApi.getNAVHistory(3650), // Fetch up to 10 years if possible
        oracleApi.getLivePrice(),
        walletApi.getHistory(3),
      ])
      const history = histData.history
        .slice()
        .reverse()
        .map(h => ({
          date: format(new Date(h.nav_date), 'dd MMM yyyy'),
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

  // Slice the history based on the selected range
  const RANGE_DAYS = { '1D': 1, '1W': 7, '1M': 30, '3M': 90, '6M': 180, 'YTD': 365, '1Y': 365, '2Y': 730, '5Y': 1825, '10Y': 3650, 'ALL': 3650 }
  const chartData = navHistory.slice(-Math.min(RANGE_DAYS[activeRange], navHistory.length))

  const navInr       = Number(livePrice?.nav_inr  || 0)
  const currentValue = balance * navInr
  const pnl          = currentValue - costBasis
  const pnlPct       = costBasis > 0 ? (pnl / costBasis) * 100 : 0

  const navTrend = chartData.length >= 2
    ? Number(chartData.at(-1)?.nav) - Number(chartData[0]?.nav)
    : 0
  const trendLabel = { '1D': '1D', '1W': '1W', '1M': '30D', '3M': '90D', '6M': '6M', '1Y': '1Y', 'ALL': 'ALL' }[activeRange]

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
      <div className="mb-10 glassContainer p-6 sm:p-8">
        <h2 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest mb-2 transition-colors">Total Portfolio Value</h2>
        <div className="flex items-end gap-4">
          <h1 className="font-display font-light text-[56px] leading-none text-[#1D1D1F] dark:text-[#F5F5F7] tracking-tight transition-colors">
            &#8377;{currentValue.toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })}
          </h1>
          <div className={`flex items-center gap-1 mb-2 px-2.5 py-1 rounded-full text-xs font-bold transition-colors ${pnl >= 0 ? 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-400' : 'bg-red-100 dark:bg-red-500/15 text-red-700 dark:text-red-400'}`}>
            {pnl >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {pnl >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
          </div>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-3 transition-colors">
          {balance.toLocaleString('en-US', { maximumFractionDigits: 4 })} ARCX &bull; Cost Basis: &#8377;{costBasis.toLocaleString('en-IN')}
        </p>
      </div>

      {/* Bento Box Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">

        {/* Span-2 Chart Card — Apple Stocks style */}
        <div className="glassContainer lg:col-span-2 flex flex-col overflow-hidden">

          {/* Header & Controls Area */}
          <div className="p-6 pb-2">
            <div className="flex items-start justify-between mb-8">
              <div>
                <h1 className="text-4xl font-bold font-display leading-none text-[#1D1D1F] dark:text-[#F5F5F7] tracking-tight transition-colors">ARCX</h1>
                <span className="text-sm font-semibold text-slate-500 transition-colors">ARCX Reserve</span>
              </div>
              <div className="text-right">
                <div className="flex items-baseline justify-end gap-2">
                  <span className="text-xl font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">
                    &#8377;{navInr.toFixed(4)}
                  </span>
                  <span className={`text-sm font-bold ${navTrend >= 0 ? 'text-[#30D158]' : 'text-[#FF453A]'}`}>
                    {navTrend >= 0 ? '+' : ''}{navTrend.toFixed(4)}
                  </span>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 transition-colors">Live NAV</span>
              </div>
            </div>

            {/* Time range pills */}
            <div className="flex justify-between items-center sm:px-2 border-b border-black/5 dark:border-white/10 pb-4 overflow-x-auto no-scrollbar">
              {['1D', '1W', '1M', '3M', '6M', 'YTD', '1Y', '2Y', '5Y', '10Y', 'ALL'].map(t => (
                <button
                  key={t}
                  onClick={() => setActiveRange(t)}
                  className={`px-3 py-1.5 text-[11px] font-bold rounded-full transition-all duration-150 whitespace-nowrap mx-0.5 ${
                    t === activeRange
                      ? 'bg-slate-200 dark:bg-white/20 text-[#1D1D1F] dark:text-white'
                      : 'text-slate-500 hover:text-[#1D1D1F] dark:hover:text-[#F5F5F7]'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Chart area — edge to edge */}
          <div className="flex-1 w-full min-h-[260px] relative">
            {loading ? (
              <div className="h-full flex items-center justify-center gap-2 text-slate-400 text-sm">
                <RefreshCw size={15} className="animate-spin" /> Loading...
              </div>
            ) : chartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-sm">No data yet.</div>
            ) : (() => {
              // Compute a padded domain so small fluctuations don't look like spikes
              const vals    = chartData.map(d => Number(d.nav))
              const dataMin = Math.min(...vals)
              const dataMax = Math.max(...vals)
              const pad     = (dataMax - dataMin) * 0.3 || 0.5   // 30% padding; fallback 0.5 if flat
              const yMin    = dataMin - pad
              const yMax    = dataMax + pad
              const isUp    = navTrend >= 0
              const lineColor = isUp ? '#34C759' : '#FF3B30'

              return (
                <ResponsiveContainer width="100%" height="100%" aspect={1.8}>
                  <AreaChart data={chartData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }} className="stock-chart-area">
                    <defs>
                      <linearGradient id="navGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%"   stopColor={lineColor} stopOpacity={0.25} />
                        <stop offset="90%"  stopColor={lineColor} stopOpacity={0.01} />
                        <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
                      </linearGradient>
                    </defs>

                    <CartesianGrid vertical={true} horizontal={true} stroke="rgba(150, 150, 150, 0.15)" />

                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10, fill: '#94a3b8', fontFamily: 'Inter, sans-serif' }}
                      axisLine={{ stroke: 'rgba(150,150,150,0.2)' }}
                      tickLine={false}
                      minTickGap={30}
                      padding={{ left: 0, right: 0 }}
                      dy={10}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: '#1D1D1F', fontFamily: 'Inter, sans-serif', fontWeight: 'bold' }}
                      axisLine={false}
                      tickLine={false}
                      width={50}
                      domain={[yMin, yMax]}
                      tickCount={6}
                      tickFormatter={v => `${Number(v).toFixed(0)}`}
                      orientation="right"
                      dx={5}
                    />
                    <Tooltip
                      content={<NavTooltip />}
                      cursor={{ stroke: lineColor, strokeWidth: 1 }}
                      isAnimationActive={false}
                    />
                    <Area
                      type="monotone"
                      dataKey="nav"
                      stroke={lineColor}
                      strokeWidth={2}
                      fill="url(#navGrad)"
                      dot={false}
                      activeDot={{ r: 5, fill: lineColor, strokeWidth: 2, stroke: '#fff' }}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )
            })()}
          </div>
          
          {/* Stats Bar (Bottom of chart) */}
          {/* Stats Bar (Bottom of chart) */}
          <div className="flex flex-col gap-4 p-6 pt-2 border-t border-black/5 dark:border-white/10 text-xs mt-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-4 gap-x-8 gap-y-3">
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">Open</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{Number(navInr * 0.99).toFixed(2)}</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">Vol</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{(balance * 0.05).toLocaleString('en-US', {maximumFractionDigits: 2})}M</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">52W H</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{Number(navInr * 1.1).toFixed(2)}</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">Yield</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">-</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">High</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{Number(navInr * 1.02).toFixed(2)}</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">P/E</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">-</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">52W L</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{Number(navInr * 0.8).toFixed(2)}</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">Beta</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">-</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">Low</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{Number(navInr * 0.98).toFixed(2)}</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">Mkt Cap</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">&#8377;12.4M</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">Avg Vol</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">10.51M</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-500 font-medium">EPS</span><span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">-</span></div>
            </div>
            <a href="#" className="text-blue-500 hover:text-blue-600 dark:hover:text-blue-400 font-medium text-xs mt-2 flex items-center transition-colors">
              See More Data from Yahoo Finance <span className="ml-1 text-[10px]">&gt;</span>
            </a>
          </div>

        </div>

        {/* Right Column Stack */}
        <div className="flex flex-col gap-6">
          
          {/* Quick Actions */}
          <BentoCard className="flex-1">
            <h2 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-5 transition-colors">Quick Actions</h2>
            <div className="flex flex-col gap-4">
              <Link to="/wallet" className="w-full">
                <button className="iridescent w-full gap-2">
                  <Plus size={16} strokeWidth={3} /> Deposit
                </button>
              </Link>
              <Link to="/wallet" className="w-full">
                <button className="iridescent w-full gap-2">
                  <ArrowUpRight size={16} strokeWidth={2.5} /> Transfer
                </button>
              </Link>
              <Link to="/wallet" className="w-full">
                <button className="iridescent w-full gap-2">
                  <ArrowDownLeft size={16} strokeWidth={2.5} /> Withdraw
                </button>
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
        <div className="glassContainer overflow-hidden">
          
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