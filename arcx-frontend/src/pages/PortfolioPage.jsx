import { useEffect, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts'
import {
  TrendingUp, TrendingDown, ArrowDownLeft, ArrowUpRight,
  Send, RefreshCw, Layers, Percent, DollarSign,
  Gift, BarChart2, AlertCircle
} from 'lucide-react'
import { portfolioApi, walletApi } from '../api/index'
import { format } from 'date-fns'

// ── Colour constants ───────────────────────────────────────────────────────
const TX_COLORS = {
  deposit:  { bg: 'bg-emerald-100 dark:bg-emerald-500/10', text: 'text-emerald-600 dark:text-emerald-400', hex: '#10b981', label: 'Deposits',   icon: ArrowDownLeft },
  withdraw: { bg: 'bg-slate-100   dark:bg-white/5',        text: 'text-slate-600   dark:text-slate-300',   hex: '#94a3b8', label: 'Withdrawals', icon: ArrowUpRight  },
  transfer: { bg: 'bg-amber-100   dark:bg-amber-500/10',   text: 'text-amber-600   dark:text-amber-400',   hex: '#C5A059', label: 'Transfers',   icon: Send          },
  dividend: { bg: 'bg-violet-100  dark:bg-violet-500/10',  text: 'text-violet-600  dark:text-violet-400',  hex: '#8b5cf6', label: 'Dividends',   icon: Gift          },
}

// ── Sub-components ─────────────────────────────────────────────────────────

function StatCard({ label, value, sub, icon: Icon, accent = false }) {
  return (
    <div className="glassContainer border border-black/5 dark:border-white/5 rounded-[24px] p-5 shadow-sm dark:shadow-none transition-colors duration-300">
      <div className="flex items-start justify-between mb-3">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{label}</p>
        {Icon && (
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${accent ? 'bg-[#C5A059]/10' : 'bg-slate-100 dark:bg-white/5'}`}>
            <Icon size={15} className={accent ? 'text-[#C5A059]' : 'text-slate-400'} />
          </div>
        )}
      </div>
      <p className="text-[22px] font-bold text-[#1D1D1F] dark:text-[#F5F5F7] leading-none tracking-tight transition-colors">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1.5 transition-colors">{sub}</p>}
    </div>
  )
}

function PnLTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const pv  = payload.find(p => p.dataKey === 'portfolio_value')?.value ?? 0
  const cb  = payload.find(p => p.dataKey === 'cost_basis')?.value ?? 0
  const pnl = pv - cb
  const up  = pnl >= 0
  return (
    <div className="glassContainer px-4 py-3 min-w-[170px] z-50">
      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">{label}</p>
      <div className="space-y-1">
        <div className="flex justify-between gap-6">
          <span className="text-xs text-slate-400">Value</span>
          <span className="text-xs font-bold text-[#1D1D1F] dark:text-[#F5F5F7]">&#8377;{pv.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
        </div>
        <div className="flex justify-between gap-6">
          <span className="text-xs text-slate-400">Invested</span>
          <span className="text-xs font-bold text-slate-500">&#8377;{cb.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
        </div>
        <div className="flex justify-between gap-6 pt-1 border-t border-black/5 dark:border-white/5">
          <span className="text-xs text-slate-400">P&amp;L</span>
          <span className={`text-xs font-bold ${up ? 'text-emerald-500' : 'text-red-500'}`}>
            {up ? '+' : ''}&#8377;{Math.abs(pnl).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
        </div>
      </div>
    </div>
  )
}

function TxRow({ tx }) {
  const meta = TX_COLORS[tx.tx_type] || TX_COLORS.deposit
  const Icon = meta.icon
  const amt  = Number(tx.amount_arcx)
  return (
    <div className="flex items-center justify-between px-5 py-3.5 border-b border-black/5 dark:border-white/5 last:border-0 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors cursor-default">
      <div className="flex items-center gap-3">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${meta.bg}`}>
          <Icon size={14} className={meta.text} />
        </div>
        <div>
          <p className="text-sm font-semibold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{meta.label}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">{format(new Date(tx.created_at), 'MMM dd, yyyy · hh:mm a')}</p>
        </div>
      </div>
      <div className="text-right">
        <p className={`text-sm font-bold ${amt >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-[#1D1D1F] dark:text-[#F5F5F7]'}`}>
          {amt >= 0 ? '+' : ''}{amt.toFixed(4)} ARCX
        </p>
        {Number(tx.nav_at_tx) > 0 && (
          <p className="text-[11px] text-slate-400 mt-0.5">@ &#8377;{Number(tx.nav_at_tx).toFixed(2)}</p>
        )}
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function PortfolioPage() {
  const [analytics, setAnalytics] = useState(null)
  const [txns,      setTxns]      = useState([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [retry,     setRetry]     = useState(0)
  const [txFilter,  setTxFilter]  = useState('all')

  useEffect(() => {
    const load = async () => {
      try {
        const [data, histData] = await Promise.all([
          portfolioApi.getAnalytics(),
          walletApi.getHistory(100),
        ])
        setAnalytics(data)
        setTxns(histData.transactions || [])
      } catch (e) {
        console.error('Portfolio load error:', e)
        setError(e?.message || 'Failed to load portfolio data.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [retry])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] gap-3 text-slate-400">
        <RefreshCw size={18} className="animate-spin" />
        <span className="text-sm font-medium">Loading portfolio…</span>
      </div>
    )
  }

  if (error || !analytics) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
        <AlertCircle size={28} className="opacity-50" />
        <p className="text-sm font-medium">Could not load portfolio data.</p>
        {error && <p className="text-xs text-slate-400 max-w-sm text-center opacity-70">{error}</p>}
        <button
          onClick={() => { setError(null); setAnalytics(null); setLoading(true); setRetry(r => r + 1) }}
          className="mt-2 px-4 py-2 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-xl text-xs font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors"
        >
          Try again
        </button>
      </div>
    )
  }

  const { holdings, yield_earned, tx_breakdown, pnl_series } = analytics
  const isUp = holdings.unrealized_pnl_inr >= 0

  // Donut chart data
  const donutData = Object.entries(tx_breakdown)
    .filter(([key]) => TX_COLORS[key])
    .map(([key, val]) => ({
      name:  TX_COLORS[key].label,
      value: val.count,
      hex:   TX_COLORS[key].hex,
    }))

  // Filtered transactions
  const filteredTxns = txFilter === 'all' ? txns : txns.filter(t => t.tx_type === txFilter)

  // P&L chart domain
  const pnlVals  = pnl_series.flatMap(d => [d.portfolio_value, d.cost_basis])
  const pnlMin   = Math.min(...pnlVals)
  const pnlMax   = Math.max(...pnlVals)
  const pnlPad   = (pnlMax - pnlMin) * 0.15 || 100
  const yMin     = pnlMin - pnlPad
  const yMax     = pnlMax + pnlPad

  return (
    <div className="animate-fade-in transition-colors duration-300 space-y-8">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="dark:hero-glass-card p-6 -mx-6 sm:mx-0 sm:p-8">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Portfolio Overview</p>
        <div className="flex flex-wrap items-end gap-4">
          <h1 className="font-display font-light text-[52px] leading-none text-[#1D1D1F] dark:text-[#F5F5F7] tracking-tight transition-colors">
            &#8377;{holdings.current_value_inr.toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })}
          </h1>
          <div className={`flex items-center gap-1.5 mb-2 px-3 py-1.5 rounded-full text-sm font-bold transition-colors ${
            isUp
              ? 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-400'
              : 'bg-red-100 dark:bg-red-500/15 text-red-700 dark:text-red-400'
          }`}>
            {isUp ? <TrendingUp size={15} /> : <TrendingDown size={15} />}
            {isUp ? '+' : ''}&#8377;{Math.abs(holdings.unrealized_pnl_inr).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
            <span className="opacity-70">({isUp ? '+' : ''}{holdings.pnl_pct.toFixed(2)}%)</span>
          </div>
        </div>
        <p className="text-sm text-slate-400 mt-2">
          {holdings.arcx_balance.toLocaleString('en-US', { maximumFractionDigits: 4 })} ARCX &bull; Avg buy &#8377;{holdings.avg_buy_price_inr.toFixed(4)} &bull; Live NAV &#8377;{holdings.current_nav_inr.toFixed(4)}
        </p>
      </div>

      {/* ── Stat Cards Row ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Invested"
          value={`\u20B9${holdings.cost_basis_inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          sub="Total deposits made"
          icon={DollarSign}
        />
        <StatCard
          label="Current Value"
          value={`\u20B9${holdings.current_value_inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          sub={`@ \u20B9${holdings.current_nav_inr.toFixed(4)} / ARCX`}
          icon={BarChart2}
          accent
        />
        <StatCard
          label="Yield Earned"
          value={`\u20B9${yield_earned.inr.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`}
          sub={`${yield_earned.arcx.toFixed(4)} ARCX · ${yield_earned.count} payouts`}
          icon={Gift}
        />
        <StatCard
          label="Total Return"
          value={`${isUp ? '+' : ''}${holdings.pnl_pct.toFixed(2)}%`}
          sub={`${isUp ? '+' : ''}\u20B9${holdings.unrealized_pnl_inr.toLocaleString('en-IN', { maximumFractionDigits: 2 })} unrealized`}
          icon={Percent}
        />
      </div>

      {/* ── P&L Chart + Donut ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <div className="lg:col-span-2 glassContainer border border-black/5 dark:border-white/5 rounded-[24px] p-6 shadow-sm dark:shadow-none transition-colors duration-300">
          <div className="mb-5">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Portfolio Value vs. Cost Basis</p>
            <p className="text-xs text-slate-400">Green = Current value &nbsp;·&nbsp; Dashed = What you invested</p>
          </div>
          <div style={{ height: 240, marginLeft: -16, marginRight: -16 }}>
            {pnl_series.length < 2 ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-sm">Not enough data yet.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={pnl_series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="pvGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%"   stopColor={isUp ? '#10b981' : '#ef4444'} stopOpacity={0.18} />
                      <stop offset="100%" stopColor={isUp ? '#10b981' : '#ef4444'} stopOpacity={0.01} />
                    </linearGradient>
                    <linearGradient id="cbGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%"   stopColor="#94a3b8" stopOpacity={0.10} />
                      <stop offset="100%" stopColor="#94a3b8" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#94a3b8', fontFamily: 'Inter, sans-serif' }}
                    axisLine={false} tickLine={false}
                    interval="preserveStartEnd"
                    padding={{ left: 16, right: 16 }} dy={8}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#94a3b8', fontFamily: 'Inter, sans-serif' }}
                    axisLine={false} tickLine={false}
                    width={72} domain={[yMin, yMax]} tickCount={4}
                    tickFormatter={v => `\u20B9${(v / 1000).toFixed(1)}k`}
                    orientation="right"
                  />
                  <Tooltip content={<PnLTooltip />} cursor={{ stroke: '#94a3b8', strokeWidth: 1, strokeDasharray: '3 3' }} isAnimationActive={false} />
                  {/* Cost basis — gray dashed fill */}
                  <Area
                    type="monotone" dataKey="cost_basis"
                    stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="5 4"
                    fill="url(#cbGrad)" dot={false}
                    isAnimationActive={true} animationDuration={300} animationEasing="ease-out"
                  />
                  {/* Portfolio value — colored solid fill */}
                  <Area
                    type="monotone" dataKey="portfolio_value"
                    stroke={isUp ? '#10b981' : '#ef4444'} strokeWidth={2.5}
                    fill="url(#pvGrad)" dot={false}
                    activeDot={{ r: 5, fill: isUp ? '#10b981' : '#ef4444', strokeWidth: 2, stroke: '#fff' }}
                    isAnimationActive={true} animationDuration={300} animationEasing="ease-out"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Transaction Breakdown Donut */}
        <div className="glassContainer border border-black/5 dark:border-white/5 rounded-[24px] p-6 shadow-sm dark:shadow-none transition-colors duration-300">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-5">Activity Breakdown</p>
          <div style={{ height: 140 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={donutData}
                  cx="50%" cy="50%"
                  innerRadius={42} outerRadius={62}
                  dataKey="value" stroke="none"
                  paddingAngle={3}
                >
                  {donutData.map((entry, i) => (
                    <Cell key={i} fill={entry.hex} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v, name) => [v, name]}
                  contentStyle={{
                    background: 'var(--tooltip-bg, #fff)',
                    border: '1px solid rgba(0,0,0,0.06)',
                    borderRadius: 12,
                    fontSize: 12,
                    fontFamily: 'Inter, sans-serif',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2.5 mt-4">
            {Object.entries(tx_breakdown).filter(([k]) => TX_COLORS[k]).map(([key, val]) => {
              const m = TX_COLORS[key]
              const Icon = m.icon
              return (
                <div key={key} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: m.hex }} />
                    <span className="text-xs text-slate-500 dark:text-slate-400">{m.label}</span>
                  </div>
                  <span className="text-xs font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{val.count}x</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── Transaction History ───────────────────────────────────────────── */}
      <div className="glassContainer border border-black/5 dark:border-white/5 rounded-[24px] overflow-hidden shadow-sm dark:shadow-none transition-colors duration-300">
        {/* Header + filter tabs */}
        <div className="px-5 py-4 border-b border-black/5 dark:border-white/10 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Transaction History</p>
          <div className="flex bg-slate-100 dark:bg-black/30 rounded-xl p-1 gap-0.5 border border-black/5 dark:border-white/5">
            {['all', 'deposit', 'withdraw', 'transfer', 'dividend'].map(f => (
              <button
                key={f}
                onClick={() => setTxFilter(f)}
                className={`px-3 py-1.5 text-[11px] font-bold rounded-lg capitalize transition-all duration-150 ${
                  f === txFilter
                    ? 'bg-white dark:bg-white/10 text-[#1D1D1F] dark:text-[#F5F5F7] shadow-sm'
                    : 'text-slate-400 hover:text-[#1D1D1F] dark:hover:text-[#F5F5F7]'
                }`}
              >
                {f === 'all' ? 'All' : TX_COLORS[f]?.label ?? f}
              </button>
            ))}
          </div>
        </div>

        {/* Rows */}
        {filteredTxns.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <Layers size={28} className="mb-3 opacity-40" />
            <p className="text-sm font-medium">No transactions found</p>
          </div>
        ) : (
          <div className="divide-y divide-black/4 dark:divide-white/4">
            {filteredTxns.map(tx => <TxRow key={tx.id} tx={tx} />)}
          </div>
        )}
      </div>

    </div>
  )
}
