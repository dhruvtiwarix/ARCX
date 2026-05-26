import { useState, useEffect } from 'react'
import { Shield, CheckCircle, Clock, ChevronRight, FileText, CreditCard, BookOpen, Car } from 'lucide-react'
import { kycApi } from '../api/index'
import { useAuthStore } from '../store/authStore'
import { format as formatDate } from 'date-fns'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'

const TIERS = [
  {
    id:    'tier_1',
    label: 'Tier 1 — Basic',
    limit: '₹10,000 / day',
    docs:  [
      { value: 'aadhaar', label: 'Aadhaar Card', icon: CreditCard },
      { value: 'dl',      label: 'Driving License', icon: Car },
    ],
  },
  {
    id:    'tier_2',
    label: 'Tier 2 — Standard',
    limit: '₹1,00,000 / day',
    docs:  [
      { value: 'pan',      label: 'PAN Card', icon: CreditCard },
      { value: 'passport', label: 'Passport', icon: BookOpen },
    ],
  },
  {
    id:    'tier_3',
    label: 'Tier 3 — Full',
    limit: 'Unlimited',
    docs:  [
      { value: 'passport', label: 'Passport', icon: BookOpen },
    ],
  },
]

const STATUS_ICON = {
  approved: <CheckCircle size={14} className="text-emerald-600 dark:text-emerald-400" />,
  pending:  <Clock       size={14} className="text-amber-600 dark:text-amber-400" />,
  rejected: <span className="text-xs text-red-600 dark:text-red-400 font-medium">✗</span>,
}

export default function KYCPage() {
  const { user, fetchMe } = useAuthStore()
  const navigate = useNavigate()
  const [kycData, setKycData]     = useState(null)
  const [step, setStep]           = useState(0)   // 0=choose tier, 1=choose doc, 2=enter ref, 3=done
  const [selectedTier, setTier]   = useState(null)
  const [selectedDoc, setDoc]     = useState(null)
  const [docRef, setDocRef]       = useState('')
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')

  const loadKYC = async () => {
    try {
      const d = await kycApi.getKYCStatus()
      setKycData(d)
    } catch {}
  }

  useEffect(() => { loadKYC() }, [])

  const handleSubmit = async () => {
    if (!docRef.trim()) { setError('Enter the document reference ID.'); return }
    setLoading(true); setError('')
    try {
      await kycApi.submitKYC({
        tier:          selectedTier.id,
        document_type: selectedDoc.value,
        document_ref:  docRef,
      })
      await loadKYC()
      await fetchMe()
      setStep(3)
    } catch (e) {
      setError(e.error || 'Submission failed. Try again.')
    }
    setLoading(false)
  }

  const reset = () => {
    setStep(0); setTier(null); setDoc(null); setDocRef(''); setError('')
  }

  const approvedTiers = kycData?.records?.filter(r => r.status === 'approved').map(r => r.tier) || []

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
          Complete identity verification to unlock higher transaction limits
        </p>
      </div>

      {/* Current status card */}
      <div className="glassContainer border border-black/5 dark:border-white/5 rounded-2xl p-6 mb-6 animate-fade-up shadow-sm dark:shadow-none transition-colors duration-300">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-widest mb-1 font-bold">Current Status</div>
            <div className="flex items-center gap-2">
              <Shield size={16} className={kycData?.kyc_status === 'approved' ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'} />
              <span className={clsx(
                'font-bold capitalize transition-colors',
                kycData?.kyc_status === 'approved' ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'
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

        {/* Tier progress */}
        <div className="mt-6 flex gap-3">
          {TIERS.map(t => {
            const isApproved = approvedTiers.includes(t.id)
            return (
              <div key={t.id} className={clsx(
                'flex-1 p-3 rounded-xl border text-center transition-colors',
                isApproved
                  ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                  : 'bg-slate-50 dark:bg-black/20 border-black/5 dark:border-white/5 text-slate-600 dark:text-slate-400'
              )}>
                <div className="font-bold text-xs mb-0.5">{t.id.replace('_', ' ').toUpperCase()}</div>
                <div className="text-[10px] uppercase font-bold opacity-70 tracking-wider">{t.limit}</div>
                {isApproved && <CheckCircle size={14} className="mx-auto mt-2" />}
              </div>
            )
          })}
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
                  <span className="text-sm font-bold text-[#1D1D1F] dark:text-[#F5F5F7] capitalize transition-colors">{r.tier.replace('_', ' ')}</span>
                  <span className="text-xs text-slate-500 font-medium">· {r.document_type}</span>
                </div>
                <span className="text-xs text-slate-500 font-medium">{formatDate(r.submitted_at, 'MMM dd, yyyy')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KYC Wizard */}
      {step < 3 && (
        <div className="glassContainer border border-black/5 dark:border-white/5 rounded-2xl overflow-hidden animate-fade-up delay-200 shadow-sm dark:shadow-none transition-colors duration-300">

          {/* Step indicator */}
          <div className="flex border-b border-black/5 dark:border-white/5 bg-slate-50 dark:bg-black/20 transition-colors">
            {['Choose Tier', 'Choose Document', 'Submit'].map((s, i) => (
              <div key={i} className={clsx(
                'flex-1 py-4 text-center text-[11px] uppercase tracking-widest font-bold border-b-2 transition-all',
                step === i ? 'border-[#C5A059] dark:border-arcx-gold text-[#1D1D1F] dark:text-[#F5F5F7]' : 'border-transparent text-slate-400 dark:text-slate-600'
              )}>
                <span className={clsx('mr-2 inline-flex w-5 h-5 rounded-full text-[10px] items-center justify-center transition-colors',
                  step > i ? 'bg-emerald-500 text-white' : step === i ? 'bg-[#1D1D1F] dark:bg-arcx-gold text-white dark:text-black' : 'bg-slate-200 dark:bg-white/10 text-slate-500'
                )}>{step > i ? '✓' : i + 1}</span>
                {s}
              </div>
            ))}
          </div>

          <div className="p-6">

            {/* Step 0: Choose tier */}
            {step === 0 && (
              <div className="space-y-4">
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2 transition-colors">Select the KYC tier you want to complete.</p>
                {TIERS.map(t => {
                  const isApproved = approvedTiers.includes(t.id)
                  return (
                    <button
                      key={t.id}
                      disabled={isApproved}
                      onClick={() => { setTier(t); setStep(1) }}
                      className={clsx(
                        'w-full flex items-center justify-between p-4 rounded-xl border text-left transition-all',
                        isApproved
                          ? 'border-emerald-200 dark:border-emerald-500/20 bg-emerald-50 dark:bg-emerald-500/5 opacity-60 cursor-not-allowed'
                          : 'border-black/10 dark:border-white/10 hover:border-[#C5A059] dark:hover:border-arcx-gold/40 hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer'
                      )}
                    >
                      <div>
                        <div className="text-sm font-bold text-[#1D1D1F] dark:text-[#F5F5F7] flex items-center gap-2 transition-colors">
                          {t.label}
                          {isApproved && <CheckCircle size={14} className="text-emerald-600 dark:text-emerald-400" />}
                        </div>
                        <div className="text-xs font-medium text-slate-500 mt-1 transition-colors">Daily limit: {t.limit}</div>
                      </div>
                      {!isApproved && <ChevronRight size={18} className="text-slate-400" />}
                    </button>
                  )
                })}
              </div>
            )}

            {/* Step 1: Choose document */}
            {step === 1 && selectedTier && (
              <div className="space-y-4">
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2 transition-colors">
                  Select a document for <span className="text-[#C5A059] dark:text-arcx-gold font-bold">{selectedTier.label}</span>
                </p>
                {selectedTier.docs.map(doc => {
                  const Icon = doc.icon
                  return (
                    <button
                      key={doc.value}
                      onClick={() => { setDoc(doc); setStep(2) }}
                      className="w-full flex items-center gap-4 p-4 rounded-xl border border-black/10 dark:border-white/10 hover:border-[#C5A059] dark:hover:border-arcx-gold/40 hover:bg-slate-50 dark:hover:bg-white/5 text-left transition-all"
                    >
                      <Icon size={20} className="text-slate-400 flex-shrink-0" />
                      <span className="text-sm font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{doc.label}</span>
                      <ChevronRight size={18} className="text-slate-400 ml-auto" />
                    </button>
                  )
                })}
                <button onClick={() => setStep(0)} className="text-xs font-bold text-slate-500 hover:text-[#1D1D1F] dark:hover:text-white mt-4 transition-colors">
                  ← Back to Tiers
                </button>
              </div>
            )}

            {/* Step 2: Enter reference */}
            {step === 2 && selectedDoc && (
              <div className="space-y-5">
                <div>
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1 transition-colors">
                    Enter the reference ID for your <span className="text-[#C5A059] dark:text-arcx-gold font-bold">{selectedDoc.label}</span>
                  </p>
                  <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-4 transition-colors">
                    In production, this comes from DigiLocker / KYC provider. For demo, use any string like <code className="text-[#C5A059] dark:text-arcx-gold font-mono font-bold">DEMO_REF_001</code>
                  </p>
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest transition-colors">Document Reference ID</label>
                  <input
                    type="text"
                    value={docRef}
                    onChange={e => setDocRef(e.target.value)}
                    placeholder="e.g. DEMO_REF_001"
                    className="w-full bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-xl px-4 py-3 text-[#1D1D1F] dark:text-[#F5F5F7] font-mono text-sm focus:outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors"
                  />
                </div>
                {error && (
                  <div className="text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-xl p-3 transition-colors">
                    {error}
                  </div>
                )}
                <div className="flex items-center gap-4 pt-2">
                  <button onClick={() => setStep(1)} className="text-xs font-bold text-slate-500 hover:text-[#1D1D1F] dark:hover:text-white transition-colors">
                    ← Back
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={loading}
                    className="flex-1 py-3.5 bg-[#1D1D1F] dark:bg-arcx-gold text-white dark:text-black font-bold rounded-xl hover:bg-black dark:hover:bg-[#E5C009] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Submitting…' : 'Submit Verification'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 3: Success */}
      {step === 3 && (
        <div className="glassContainer border border-emerald-200 dark:border-emerald-500/20 rounded-2xl p-8 text-center animate-fade-up shadow-sm dark:shadow-none transition-colors duration-300">
          <CheckCircle size={48} className="text-emerald-500 mx-auto mb-5" />
          <h3 className="font-display font-bold text-2xl text-[#1D1D1F] dark:text-[#F5F5F7] mb-2 transition-colors">Verification Complete</h3>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-8 transition-colors">
            Your <span className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7]">{selectedTier?.id.replace('_', ' ').toUpperCase()}</span> has been approved. Transaction limits updated immediately.
          </p>
          <button
            onClick={reset}
            className="px-6 py-3 bg-slate-100 dark:bg-white/5 text-[#1D1D1F] dark:text-[#F5F5F7] font-bold rounded-xl text-sm hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
          >
            Submit another tier
          </button>
        </div>
      )}
    </div>
  )
}