import { useState, useEffect } from 'react'
import { ArrowDownLeft, ArrowUpRight, Send, Clock, Loader2,
         CheckCircle2, XCircle, ArrowLeftRight } from 'lucide-react'
import { walletApi, oracleApi } from '../api/index'
import { useAuthStore } from '../store/authStore'
import { format } from 'date-fns'

function genKey() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

// ── Action tab component ──────────────────────────────────────────────────────
function ActionTabs({ active, onSelect }) {
  const tabs = [
    { id: 'deposit',  label: 'Deposit',  icon: ArrowDownLeft  },
    { id: 'withdraw', label: 'Withdraw', icon: ArrowUpRight    },
    { id: 'transfer', label: 'Transfer', icon: Send            },
  ]
  return (
    <div className="flex gap-2">
      {tabs.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onSelect(id)}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                      transition-all duration-150 border
            ${active === id
              ? 'bg-arcx-600 text-white border-arcx-600'
              : 'bg-white text-slate-600 border-slate-200 hover:border-arcx-300'}`}
        >
          <Icon size={15} />
          {label}
        </button>
      ))}
    </div>
  )
}

// ── Success / error flash ─────────────────────────────────────────────────────
function Flash({ type, msg }) {
  if (!msg) return null
  return (
    <div className={`flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium
      ${type === 'ok'
        ? 'bg-emerald-50 border border-emerald-200 text-emerald-700'
        : 'bg-red-50 border border-red-100 text-red-600'}`}>
      {type === 'ok'
        ? <CheckCircle2 size={16} className="flex-shrink-0" />
        : <XCircle size={16} className="flex-shrink-0" />}
      {msg}
    </div>
  )
}

// ── Transaction row ───────────────────────────────────────────────────────────
const TX_META = {
  deposit:  { label: 'Deposit',  color: 'text-emerald-600', bg: 'bg-emerald-50', icon: ArrowDownLeft },
  withdraw: { label: 'Withdraw', color: 'text-red-500',     bg: 'bg-red-50',     icon: ArrowUpRight  },
  transfer: { label: 'Transfer', color: 'text-arcx-600',    bg: 'bg-arcx-50',    icon: ArrowLeftRight },
  dividend: { label: 'Dividend', color: 'text-sky-600',     bg: 'bg-sky-50',     icon: ArrowDownLeft  },
}

function TxRow({ tx }) {
  const meta = TX_META[tx.tx_type] || TX_META.deposit
  const Icon = meta.icon
  const amt  = Number(tx.amount_arcx)

  return (
    <div className="flex items-center gap-4 py-3.5 border-b border-slate-50 last:border-0">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${meta.bg}`}>
        <Icon size={16} className={meta.color} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800">{meta.label}</p>
        <p className="text-xs text-slate-400 mt-0.5">
          NAV ₹{Number(tx.nav_at_tx).toFixed(4)} ·{' '}
          {format(new Date(tx.created_at), 'dd MMM, hh:mm a')}
        </p>
      </div>
      <div className="text-right">
        <p className={`text-sm font-semibold font-mono ${amt >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
          {amt >= 0 ? '+' : ''}{amt.toFixed(6)} ARCX
        </p>
        {Number(tx.amount_inr) !== 0 && (
          <p className="text-xs text-slate-400 mt-0.5">
            ₹{Number(tx.amount_inr).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </p>
        )}
      </div>
      <span className={`badge ml-2 ${tx.status === 'completed' ? 'badge-green' : 'badge-gray'}`}>
        {tx.status}
      </span>
    </div>
  )
}

export default function WalletPage() {
  const { user, fetchMe } = useAuthStore()
  const [tab,     setTab]     = useState('deposit')
  const [form,    setForm]    = useState({ amount_inr: '', amount_arcx: '', to_user_email: '', note: '' })
  const [flash,   setFlash]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [txns,    setTxns]    = useState([])
  const [nav,     setNav]     = useState(null)
  const [txLoad,  setTxLoad]  = useState(true)

  const kyc_ok = user?.kyc_status === 'approved'
  const balance = Number(user?.arcx_balance || 0)

  const showFlash = (type, msg) => {
    setFlash({ type, msg })
    setTimeout(() => setFlash(null), 4000)
  }

  const loadHistory = async () => {
    setTxLoad(true)
    try {
      const data = await walletApi.getHistory(30)
      setTxns(data.transactions || [])
    } catch (_) {}
    setTxLoad(false)
  }

  const loadNav = async () => {
    try {
      const data = await oracleApi.getLivePrice()
      setNav(Number(data.nav_inr))
    } catch (_) {}
  }

  useEffect(() => { loadHistory(); loadNav() }, [])

  const handleChange = e => setForm(p => ({ ...p, [e.target.name]: e.target.value }))

  const handleDeposit = async e => {
    e.preventDefault()
    if (!kyc_ok) return showFlash('err', 'Complete KYC before depositing.')
    setLoading(true)
    try {
      const d = await walletApi.deposit(form.amount_inr)
      showFlash('ok', `Deposited! +${Number(d.arcx_credited).toFixed(6)} ARCX · NAV ₹${Number(d.nav_at_tx).toFixed(4)}`)
      setForm(p => ({ ...p, amount_inr: '' }))
      fetchMe(); loadHistory()
    } catch (err) {
      showFlash('err', err.response?.data?.error || 'Deposit failed.')
    }
    setLoading(false)
  }

  const handleWithdraw = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      const d = await walletApi.withdraw(form.amount_arcx)
      showFlash('ok', `Withdrawn! ₹${Number(d.inr_returned).toFixed(2)} credited · NAV ₹${Number(d.nav_at_tx).toFixed(4)}`)
      setForm(p => ({ ...p, amount_arcx: '' }))
      fetchMe(); loadHistory()
    } catch (err) {
      showFlash('err', err.response?.data?.error || 'Withdrawal failed.')
    }
    setLoading(false)
  }

  const handleTransfer = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      await walletApi.transfer({
        to_user_email: form.to_user_email,
        amount_arcx:   form.amount_arcx,
        note:          form.note,
      }, genKey())
      showFlash('ok', `Sent ${form.amount_arcx} ARCX to ${form.to_user_email}. Fee: ₹0.00`)
      setForm(p => ({ ...p, amount_arcx: '', to_user_email: '', note: '' }))
      fetchMe(); loadHistory()
    } catch (err) {
      showFlash('err', err.response?.data?.error || 'Transfer failed.')
    }
    setLoading(false)
  }

  // Estimated ARCX for deposit preview
  const estimatedArcx = nav && form.amount_inr
    ? (Number(form.amount_inr) / nav).toFixed(6)
    : null

  // Estimated INR for withdraw preview
  const estimatedInr = nav && form.amount_arcx
    ? (Number(form.amount_arcx) * nav).toFixed(2)
    : null

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display font-semibold text-2xl text-slate-900">Wallet</h1>
        <p className="text-sm text-slate-500 mt-0.5">Deposit, withdraw, or transfer ARCX instantly</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* ── Left: action panel ─────────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-4">

          {/* Balance card */}
          <div className="card p-5 bg-vault text-white">
            <p className="text-slate-400 text-xs uppercase tracking-wider mb-2">ARCX Balance</p>
            <p className="font-display font-bold text-3xl">{balance.toFixed(6)}</p>
            {nav && (
              <p className="text-slate-400 text-sm mt-1">
                ≈ ₹{(balance * nav).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </p>
            )}
          </div>

          {/* Action tabs */}
          <ActionTabs active={tab} onSelect={setTab} />

          {flash && <Flash type={flash.type} msg={flash.msg} />}

          {/* Forms */}
          {tab === 'deposit' && (
            <form onSubmit={handleDeposit} className="card p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Amount in INR
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm">₹</span>
                  <input className="input pl-7" type="number" name="amount_inr"
                         value={form.amount_inr} onChange={handleChange}
                         placeholder="1000.00" min="100" step="0.01" required />
                </div>
                {estimatedArcx && (
                  <p className="text-xs text-arcx-600 mt-1.5 font-medium">
                    ≈ {estimatedArcx} ARCX at live NAV ₹{nav?.toFixed(4)}
                  </p>
                )}
              </div>
              {!kyc_ok && (
                <p className="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                  KYC verification required to deposit.
                </p>
              )}
              <button type="submit" className="btn-primary w-full" disabled={loading || !kyc_ok}>
                {loading
                  ? <Loader2 size={16} className="animate-spin" />
                  : <><ArrowDownLeft size={16} /> Deposit</>}
              </button>
            </form>
          )}

          {tab === 'withdraw' && (
            <form onSubmit={handleWithdraw} className="card p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Amount in ARCX
                </label>
                <div className="relative">
                  <input className="input pr-14" type="number" name="amount_arcx"
                         value={form.amount_arcx} onChange={handleChange}
                         placeholder="10.00" min="0.01" step="0.000001" required />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-xs font-medium">ARCX</span>
                </div>
                {estimatedInr && (
                  <p className="text-xs text-arcx-600 mt-1.5 font-medium">
                    ≈ ₹{Number(estimatedInr).toLocaleString('en-IN')} at live NAV ₹{nav?.toFixed(4)}
                  </p>
                )}
              </div>
              <button type="submit" className="btn-primary w-full" disabled={loading}>
                {loading
                  ? <Loader2 size={16} className="animate-spin" />
                  : <><ArrowUpRight size={16} /> Withdraw</>}
              </button>
            </form>
          )}

          {tab === 'transfer' && (
            <form onSubmit={handleTransfer} className="card p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Recipient email</label>
                <input className="input" type="email" name="to_user_email"
                       value={form.to_user_email} onChange={handleChange}
                       placeholder="friend@example.com" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Amount (ARCX)</label>
                <div className="relative">
                  <input className="input pr-14" type="number" name="amount_arcx"
                         value={form.amount_arcx} onChange={handleChange}
                         placeholder="5.00" min="0.000001" step="0.000001" required />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-xs font-medium">ARCX</span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Note <span className="text-slate-400">(optional)</span>
                </label>
                <input className="input" type="text" name="note"
                       value={form.note} onChange={handleChange}
                       placeholder="Splitting dinner" maxLength={140} />
              </div>
              <div className="bg-emerald-50 border border-emerald-100 rounded-xl px-4 py-2.5 text-sm text-emerald-700 font-medium flex items-center gap-2">
                <CheckCircle2 size={14} />
                Zero fees · Instant settlement
              </div>
              <button type="submit" className="btn-primary w-full" disabled={loading}>
                {loading
                  ? <Loader2 size={16} className="animate-spin" />
                  : <><Send size={16} /> Send ARCX</>}
              </button>
            </form>
          )}
        </div>

        {/* ── Right: transaction history ─────────────────────────────── */}
        <div className="lg:col-span-3 card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display font-semibold text-base text-slate-900">
              Recent Transactions
            </h3>
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Clock size={12} />
              Last 30
            </div>
          </div>

          {txLoad ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-sm gap-2">
              <Loader2 size={16} className="animate-spin" />
              Loading…
            </div>
          ) : txns.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <ArrowLeftRight size={28} className="mb-3 opacity-30" />
              <p className="text-sm">No transactions yet.</p>
              <p className="text-xs mt-1">Make your first deposit to get started.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {txns.map(tx => <TxRow key={tx.id} tx={tx} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}