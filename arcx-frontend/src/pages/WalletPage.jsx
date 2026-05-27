import { useState, useEffect } from 'react'
import { ArrowDownLeft, ArrowUpRight, Send, Clock, Loader2,
         CheckCircle2, XCircle, ArrowLeftRight, Landmark } from 'lucide-react'
import { b2bApi } from '../api/b2b'
import { walletApi, oracleApi } from '../api/index'
import { useAuthStore } from '../store/authStore'
import { format } from 'date-fns'

function genKey() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

// ── iOS Segmented Control ──────────────────────────────────────────────────
function ActionTabs({ active, onSelect }) {
  const tabs = [
    { id: 'deposit',  label: 'Deposit' },
    { id: 'withdraw', label: 'Withdraw' },
    { id: 'transfer', label: 'Transfer' },
    { id: 'b2b', label: 'B2B (UPI)' },
  ]
  return (
    <div className="flex bg-slate-100 dark:bg-black/50 p-1 rounded-xl border border-black/5 dark:border-white/5 mb-6 transition-colors">
      {tabs.map(({ id, label }) => (
        <button
          key={id}
          onClick={() => onSelect(id)}
          className={`flex-1 py-2 text-xs font-bold uppercase tracking-widest rounded-lg transition-all duration-300
            ${active === id
              ? 'bg-white dark:bg-white/10 text-[#1D1D1F] dark:text-[#F5F5F7] shadow-sm'
              : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'}`}
        >
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
    <div className={`flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium mb-6 animate-fade-in transition-colors
      ${type === 'ok'
        ? 'bg-emerald-100 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
        : 'bg-red-100 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-700 dark:text-red-400'}`}>
      {type === 'ok'
        ? <CheckCircle2 size={16} className="flex-shrink-0" />
        : <XCircle size={16} className="flex-shrink-0" />}
      {msg}
    </div>
  )
}

// ── Transaction row ───────────────────────────────────────────────────────────
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
              {tx.tx_type === 'withdraw' && Number(tx.fee_inr) > 0 && (
                <span className="text-amber-500 ml-1">(+₹{Number(tx.fee_inr).toFixed(2)} fee)</span>
              )}
            </p>
          )}
          <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider font-bold transition-colors ${
            tx.status === 'completed'
              ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
              : 'bg-slate-200 dark:bg-slate-500/20 text-slate-600 dark:text-slate-400'
          }`}>
            {tx.status}
          </span>
        </div>
      </div>
    </div>
  )
}

export default function WalletPage() {
  const { user, fetchMe } = useAuthStore()
  const [tab,     setTab]     = useState('deposit')
  const [form,    setForm]    = useState({ amount_inr: '', amount_arcx: '', to_user_email: '', note: '', pin: '', alias: '' })
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

  useEffect(() => { fetchMe(); loadHistory(); loadNav() }, [])

  const handleChange = e => setForm(p => ({ ...p, [e.target.name]: e.target.value }))

  const extractError = (err) => {
    if (!err) return null
    // Could be pre-thrown object from wallet.js: err.error, err.pin, err.detail
    if (err.error) return err.error
    if (err.detail) return err.detail
    if (err.pin) return Array.isArray(err.pin) ? err.pin[0] : err.pin
    if (err.non_field_errors) return Array.isArray(err.non_field_errors) ? err.non_field_errors[0] : err.non_field_errors
    // Axios response shape
    const d = err.response?.data
    if (!d) return null
    if (d.error) return d.error
    if (d.detail) return d.detail
    if (d.pin) return Array.isArray(d.pin) ? d.pin[0] : d.pin
    if (d.non_field_errors) return Array.isArray(d.non_field_errors) ? d.non_field_errors[0] : d.non_field_errors
    // Last resort: stringify
    if (typeof d === 'string') return d
    return JSON.stringify(d)
  }

  const handleDeposit = async e => {
    e.preventDefault()
    if (form.pin.length !== 6) return showFlash('err', '6-digit PIN required.')
    setLoading(true)
    try {
      const d = await walletApi.deposit(form.amount_inr, form.pin)
      showFlash('ok', `Deposited! +${Number(d.arcx_credited).toFixed(6)} ARCX · NAV ₹${Number(d.nav_at_tx).toFixed(4)}`)
      setForm(p => ({ ...p, amount_inr: '', pin: '' }))
      fetchMe(); loadHistory()
    } catch (err) {
      showFlash('err', extractError(err) || 'Deposit failed.')
    }
    setLoading(false)
  }

  const handleWithdraw = async e => {
    e.preventDefault()
    if (form.pin.length !== 6) return showFlash('err', '6-digit PIN required.')
    setLoading(true)
    try {
      const d = await walletApi.withdraw(form.amount_arcx, form.pin)
      const fee = Number(d.fee_inr || 0)
      const net = Number(d.inr_returned)
      const feeStr = fee > 0 ? ` · Fee ₹${fee.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : ''
      showFlash('ok', `Instant withdrawal! ₹${net.toLocaleString('en-IN', { maximumFractionDigits: 2 })} credited to bank${feeStr}`)
      setForm(p => ({ ...p, amount_arcx: '', pin: '' }))
      fetchMe(); loadHistory()
    } catch (err) {
      showFlash('err', extractError(err) || 'Withdrawal failed.')
    }
    setLoading(false)
  }

  const handleTransfer = async e => {
    e.preventDefault()
    if (form.pin.length !== 6) return showFlash('err', '6-digit PIN required.')
    setLoading(true)
    try {
      await walletApi.transfer({
        to_user_email: form.to_user_email,
        amount_arcx:   form.amount_arcx,
        note:          form.note,
        pin:           form.pin,
      }, genKey())
      showFlash('ok', `Sent ${form.amount_arcx} ARCX to ${form.to_user_email}. Fee: ₹0.00`)
      setForm(p => ({ ...p, amount_arcx: '', to_user_email: '', note: '', pin: '' }))
      fetchMe(); loadHistory()
    } catch (err) {
      showFlash('err', extractError(err) || 'Transfer failed.')
    }
    setLoading(false)
  }

  const handleB2bTransfer = async e => {
    e.preventDefault()
    if (form.pin.length !== 6) return showFlash('err', '6-digit PIN required.')
    setLoading(true)
    try {
      await b2bApi.transfer(form.alias, form.amount_arcx, form.pin, genKey())
      showFlash('ok', `Transfer to ${form.alias} is processing...`)
      setForm(p => ({ ...p, amount_arcx: '', alias: '', pin: '' }))
    } catch (err) {
      showFlash('err', err.response?.data?.error || err.response?.data?.pin?.[0] || 'Transfer failed.')
    }
    setLoading(false)
  }

  const estimatedArcx = nav && form.amount_inr
    ? (Number(form.amount_inr) / nav).toFixed(6)
    : null

  const estimatedInr = nav && form.amount_arcx
    ? (Number(form.amount_arcx) * nav).toFixed(2)
    : null

  // Live fee preview: 0.1% of gross INR, capped at ₹8,300 (≈$100 at ₹83/$)
  const FEE_RATE    = 0.001
  const FEE_CAP_INR = 8300
  const estimatedFee = estimatedInr
    ? Math.min(Number(estimatedInr) * FEE_RATE, FEE_CAP_INR).toFixed(2)
    : null
  const estimatedNet = estimatedFee
    ? (Number(estimatedInr) - Number(estimatedFee)).toFixed(2)
    : null

  return (
    <div className="animate-fade-in pb-12 transition-colors duration-300">
      
      {/* Header */}
      <div className="mb-10">
        <h1 className="font-display font-bold text-[28px] text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">Wallet</h1>
        <p className="text-sm text-slate-500 mt-1 transition-colors">Move your funds. Instant settlement globally.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">

        {/* ── Left: Action Panel ─────────────────────────────────────── */}
        <div className="lg:col-span-2">
          
          <div className="glassContainer border border-black/5 dark:border-white/5 rounded-[24px] p-6 max-w-md mx-auto lg:mx-0 shadow-sm dark:shadow-none transition-colors duration-300">
            
            {/* Balance Card inside Action Panel */}
            <div className="bg-slate-100 dark:bg-gradient-to-br dark:from-[#2C2C2E] dark:to-[#1C1C1E] border border-black/5 dark:border-white/10 rounded-xl p-5 mb-8 shadow-inner relative overflow-hidden transition-colors duration-300">
              <div className="absolute top-0 right-0 p-4 opacity-10 text-slate-900 dark:text-[#F5F5F7]">
                <Landmark size={64} />
              </div>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2">Available Balance</p>
              <p className="font-display font-light text-4xl text-[#1D1D1F] dark:text-[#F5F5F7] tracking-tight transition-colors">{balance.toFixed(6)}</p>
              {nav && (
                <p className="text-sm font-medium text-[#C5A059] dark:text-arcx-gold mt-1 transition-colors">
                  ≈ ₹{(balance * nav).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                </p>
              )}
            </div>

            <ActionTabs active={tab} onSelect={setTab} />
            {flash && <Flash type={flash.type} msg={flash.msg} />}

            {/* Forms */}
            {tab === 'deposit' && (
              <form onSubmit={handleDeposit} className="space-y-5 animate-fade-in">
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                    Amount in INR
                  </label>
                  <div className="relative">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#1D1D1F] dark:text-[#F5F5F7] font-medium transition-colors">₹</span>
                    <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 pl-9 pr-4 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors font-mono text-lg" 
                           type="number" name="amount_inr" value={form.amount_inr} onChange={handleChange} placeholder="1000.00" min="100" step="0.01" required />
                  </div>
                  {estimatedArcx && (
                    <p className="text-xs text-[#C5A059] dark:text-arcx-gold mt-2 font-medium flex items-center gap-1 transition-colors">
                      <ArrowDownLeft size={12} /> Receives ≈ {estimatedArcx} ARCX
                    </p>
                  )}
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">6-Digit PIN</label>
                  <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 px-4 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors text-sm" 
                         type="password" name="pin" value={form.pin} onChange={handleChange} maxLength="6" pattern="[0-9]{6}" placeholder="••••••" required />
                </div>
                {!kyc_ok && user && (
                  <p className="text-[11px] text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-lg px-3 py-2 font-medium transition-colors">
                    KYC verification required to deposit.
                  </p>
                )}
                <button type="submit" className="w-full py-3.5 bg-[#1D1D1F] dark:bg-white text-white dark:text-black font-bold rounded-xl hover:bg-black dark:hover:bg-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2" disabled={loading}>
                  {loading ? <Loader2 size={18} className="animate-spin" /> : 'Deposit Funds'}
                </button>
              </form>
            )}

            {tab === 'withdraw' && (
              <form onSubmit={handleWithdraw} className="space-y-5 animate-fade-in">
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                    Amount in ARCX
                  </label>
                  <div className="relative">
                    <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 pl-4 pr-16 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors font-mono text-lg"
                           type="number" name="amount_arcx" value={form.amount_arcx} onChange={handleChange} placeholder="10.00" min="0.01" step="0.000001" required />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 font-bold text-xs uppercase transition-colors">ARCX</span>
                  </div>

                  {/* Live fee breakdown preview */}
                  {estimatedInr && (
                    <div className="mt-3 rounded-xl border border-black/5 dark:border-white/10 bg-slate-50 dark:bg-black/30 divide-y divide-black/5 dark:divide-white/5 text-xs overflow-hidden">
                      <div className="flex justify-between px-4 py-2.5">
                        <span className="text-slate-500 font-medium">Gross Value</span>
                        <span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7]">₹{Number(estimatedInr).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                      </div>
                      <div className="flex justify-between items-center px-4 py-2.5">
                        <span className="text-slate-500 font-medium flex items-center gap-1.5">
                          Instant Liquidity Fee
                          <span className="bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider">0.1% · max $100</span>
                        </span>
                        <span className="font-bold text-amber-600 dark:text-amber-400">−₹{Number(estimatedFee).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                      </div>
                      <div className="flex justify-between px-4 py-2.5 bg-emerald-50 dark:bg-emerald-500/5">
                        <span className="font-bold text-emerald-700 dark:text-emerald-400">You Receive (Instant)</span>
                        <span className="font-bold text-emerald-700 dark:text-emerald-400">₹{Number(estimatedNet).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                      </div>
                    </div>
                  )}
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">6-Digit PIN</label>
                  <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 px-4 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors text-sm" 
                         type="password" name="pin" value={form.pin} onChange={handleChange} maxLength="6" pattern="[0-9]{6}" placeholder="••••••" required />
                </div>
                <button type="submit" className="w-full py-3.5 bg-[#1D1D1F] dark:bg-white text-white dark:text-black font-bold rounded-xl hover:bg-black dark:hover:bg-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2" disabled={loading}>
                  {loading ? <Loader2 size={18} className="animate-spin" /> : 'Withdraw Instantly via RTGS'}
                </button>
              </form>
            )}

            {tab === 'transfer' && (
              <form onSubmit={handleTransfer} className="space-y-5 animate-fade-in">
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">Recipient Email</label>
                  <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 px-4 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors text-sm" 
                         type="email" name="to_user_email" value={form.to_user_email} onChange={handleChange} placeholder="friend@arcx.com" required />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">Amount (ARCX)</label>
                  <div className="relative">
                    <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 pl-4 pr-16 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors font-mono text-lg" 
                           type="number" name="amount_arcx" value={form.amount_arcx} onChange={handleChange} placeholder="5.00" min="0.000001" step="0.000001" required />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 font-bold text-xs uppercase transition-colors">ARCX</span>
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">6-Digit PIN</label>
                  <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 px-4 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors text-sm" 
                         type="password" name="pin" value={form.pin} onChange={handleChange} maxLength="6" pattern="[0-9]{6}" placeholder="••••••" required />
                </div>
                <button type="submit" className="w-full py-3.5 bg-[#C5A059] dark:bg-arcx-gold text-white dark:text-black font-bold rounded-xl hover:bg-[#B38F48] dark:hover:bg-[#E5C009] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2" disabled={loading}>
                  {loading ? <Loader2 size={18} className="animate-spin" /> : <><Send size={16} /> Send ARCX</>}
                </button>
              </form>
            )}

            {tab === 'b2b' && (
              <form onSubmit={handleB2bTransfer} className="space-y-5 animate-fade-in">
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">Business Alias (VPA)</label>
                  <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 px-4 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors text-sm" 
                         type="text" name="alias" value={form.alias} onChange={handleChange} placeholder="vendor@arcx" required />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">Amount (ARCX)</label>
                  <div className="relative">
                    <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 pl-4 pr-16 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors font-mono text-lg" 
                           type="number" name="amount_arcx" value={form.amount_arcx} onChange={handleChange} placeholder="5.00" min="0.000001" step="0.000001" required />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 font-bold text-xs uppercase transition-colors">ARCX</span>
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">6-Digit PIN</label>
                  <input className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl py-3 px-4 text-[#1D1D1F] dark:text-[#F5F5F7] placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors text-sm" 
                         type="password" name="pin" value={form.pin} onChange={handleChange} maxLength="6" pattern="[0-9]{6}" placeholder="••••••" required />
                </div>
                <button type="submit" className="w-full py-3.5 bg-[#1D1D1F] dark:bg-white text-white dark:text-black font-bold rounded-xl hover:bg-black dark:hover:bg-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2" disabled={loading}>
                  {loading ? <Loader2 size={18} className="animate-spin" /> : 'Pay Instantly'}
                </button>
              </form>
            )}

          </div>
        </div>

        {/* ── Right: Transaction History ─────────────────────────────── */}
        <div className="lg:col-span-3">
          <div className="glassContainer border border-black/5 dark:border-white/5 rounded-[24px] overflow-hidden min-h-[500px] shadow-sm dark:shadow-none transition-colors duration-300">
            <div className="p-6 border-b border-black/5 dark:border-white/10 flex items-center justify-between bg-slate-50 dark:bg-black/20 transition-colors">
              <h3 className="font-display font-bold text-lg text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">Recent Transactions</h3>
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-500 uppercase tracking-widest transition-colors">
                <Clock size={14} /> Last 30 Days
              </div>
            </div>

            {txLoad ? (
              <div className="flex items-center justify-center py-20 text-slate-500 text-sm gap-2">
                <Loader2 size={16} className="animate-spin" /> Loading ledger…
              </div>
            ) : txns.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-24 text-slate-500 transition-colors">
                <ArrowLeftRight size={32} className="mb-4 opacity-50" />
                <p className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] mb-1 transition-colors">No transactions yet</p>
                <p className="text-xs">Make your first deposit to get started.</p>
              </div>
            ) : (
              <div className="divide-y divide-black/5 dark:divide-white/5 transition-colors">
                {txns.map(tx => <TxRow key={tx.id} tx={tx} />)}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}