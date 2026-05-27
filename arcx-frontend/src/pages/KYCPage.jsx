import { useState, useEffect } from 'react'
import { Shield, CheckCircle, Clock, CreditCard } from 'lucide-react'
import { kycApi } from '../api/index'
import { useAuthStore } from '../store/authStore'
import { format as formatDate } from 'date-fns'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'

const STATUS_ICON = {
  approved: <CheckCircle size={14} className="text-emerald-600 dark:text-emerald-400" />,
  pending:  <Clock       size={14} className="text-amber-600 dark:text-amber-400" />,
  rejected: <span className="text-xs text-red-600 dark:text-red-400 font-medium">✗</span>,
}

export default function KYCPage() {
  const { user, fetchMe } = useAuthStore()
  const navigate = useNavigate()
  const [kycData, setKycData]     = useState(null)
  const [panNumber, setPanNumber] = useState('')
  const [pin, setPin]             = useState('')
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [success, setSuccess]     = useState(false)

  const loadKYC = async () => {
    try {
      const d = await kycApi.getKYCStatus()
      setKycData(d)
    } catch {}
  }

  useEffect(() => { loadKYC() }, [])

  const handleSubmit = async () => {
    if (panNumber.length !== 10) { setError('Enter a valid 10-character PAN.'); return }
    if (pin.length !== 6) { setError('6-digit transaction PIN is required.'); return }
    setLoading(true); setError('')
    try {
      await kycApi.submitKYC({
        pan_number: panNumber,
        pin:        pin,
      })
      await loadKYC()
      await fetchMe()
      setSuccess(true)
    } catch (e) {
      setError(e.error || 'Submission failed. Try again.')
    }
    setLoading(false)
  }

  const isApproved = kycData?.kyc_status === 'approved'

  return (
    <div className="p-8 max-w-3xl mx-auto transition-colors duration-300">
      <div className="mb-8 animate-fade-up relative">
        <button 
          onClick={() => navigate('/profile')} 
          className="absolute -top-6 left-0 text-[12px] font-medium text-slate-500 hover:text-slate-900 dark:hover:text-slate-300 flex items-center gap-1 transition-colors"
        >
          ← Back to Settings
        </button>
        <h1 className="font-display font-bold text-[28px] text-[#1D1D1F] dark:text-[#F5F5F7] mt-4 transition-colors">KYC Verification</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1 transition-colors">
          Complete identity verification to unlock unlimited transaction limits
        </p>
      </div>

      {/* Current status card */}
      <div className="glassContainer border border-black/5 dark:border-white/5 rounded-2xl p-6 mb-6 animate-fade-up shadow-sm dark:shadow-none transition-colors duration-300">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-widest mb-1 font-bold">Current Status</div>
            <div className="flex items-center gap-2">
              <Shield size={16} className={isApproved ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'} />
              <span className={clsx(
                'font-bold capitalize transition-colors',
                isApproved ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'
              )}>
                {kycData?.kyc_status || 'Pending'}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-500 uppercase tracking-widest mb-1 font-bold">Daily Limit</div>
            <div className="font-display font-bold text-lg text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">
              {kycData?.daily_limit_inr || '₹0'}
            </div>
          </div>
        </div>
      </div>

      {/* Past submissions */}
      {kycData?.records?.length > 0 && (
        <div className="glassContainer border border-black/5 dark:border-white/5 rounded-2xl p-6 mb-6 animate-fade-up delay-100 shadow-sm dark:shadow-none transition-colors duration-300">
          <h2 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Submission History</h2>
          <div className="space-y-2">
            {kycData.records.map(r => (
              <div key={r.id} className="flex items-center justify-between py-3 border-b border-black/5 dark:border-white/5 last:border-0 transition-colors">
                <div className="flex items-center gap-3">
                  {STATUS_ICON[r.status]}
                  <span className="text-sm font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{r.pan_number.slice(0,2)}••••{r.pan_number.slice(-2)}</span>
                  <span className="text-xs text-slate-500 font-medium">· PAN Card</span>
                </div>
                <span className="text-xs text-slate-500 font-medium">{formatDate(r.submitted_at, 'MMM dd, yyyy')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KYC Form */}
      {!isApproved && !success && (
        <div className="glassContainer border border-black/5 dark:border-white/5 rounded-2xl p-6 animate-fade-up delay-200 shadow-sm dark:shadow-none transition-colors duration-300 space-y-5">
          <div>
            <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest transition-colors">PAN Number</label>
            <input
              type="text"
              maxLength="10"
              value={panNumber}
              onChange={e => setPanNumber(e.target.value.toUpperCase())}
              placeholder="e.g. ABCDE1234F"
              className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl px-4 py-3 text-[#1D1D1F] dark:text-[#F5F5F7] font-mono text-sm focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors uppercase"
            />
          </div>
          <div>
            <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest transition-colors">Setup 6-Digit Transaction PIN</label>
            <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-2 transition-colors">
              This PIN will be required to authorize all future deposits, withdrawals, and transfers.
            </p>
            <input
              type="password"
              maxLength="6"
              pattern="[0-9]{6}"
              value={pin}
              onChange={e => setPin(e.target.value.replace(/[^0-9]/g, ''))}
              placeholder="••••••"
              className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl px-4 py-3 text-[#1D1D1F] dark:text-[#F5F5F7] font-mono text-lg tracking-[0.5em] focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors"
              required
            />
          </div>
          {error && (
            <div className="text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-xl p-3 transition-colors">
              {error}
            </div>
          )}
          <button
            onClick={handleSubmit}
            disabled={loading || panNumber.length !== 10 || pin.length !== 6}
            className="w-full py-3.5 bg-[#1D1D1F] dark:bg-arcx-gold text-white dark:text-black font-bold rounded-xl hover:bg-black dark:hover:bg-[#E5C009] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Verifying…' : 'Submit Verification'}
          </button>
        </div>
      )}

      {/* Success */}
      {success && (
        <div className="glassContainer border border-emerald-200 dark:border-emerald-500/20 rounded-2xl p-8 text-center animate-fade-up shadow-sm dark:shadow-none transition-colors duration-300 mt-6">
          <CheckCircle size={48} className="text-emerald-500 mx-auto mb-5" />
          <h3 className="font-display font-bold text-2xl text-[#1D1D1F] dark:text-[#F5F5F7] mb-2 transition-colors">Verification Complete</h3>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400 transition-colors">
            Your KYC has been approved. Transaction limits are now <span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7]">Unlimited</span>.
          </p>
        </div>
      )}
    </div>
  )
}