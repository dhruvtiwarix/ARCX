import { useState, useEffect } from 'react'
import { Shield, CheckCircle, Clock, ChevronRight, FileText, CreditCard, BookOpen, Car } from 'lucide-react'
import { kycApi } from '../api/index'
import { useAuthStore } from '../store/authStore'
import { format as formatDate } from 'date-fns'
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
  approved: <CheckCircle size={14} className="text-emerald-400" />,
  pending:  <Clock       size={14} className="text-amber-400" />,
  rejected: <span className="text-xs text-red-400 font-medium">✗</span>,
}

export default function KYCPage() {
  const { user, fetchMe } = useAuthStore()
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
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8 animate-fade-up">
        <h1 className="font-display text-3xl text-slate-100">KYC Verification</h1>
        <p className="text-slate-500 text-sm mt-1">
          Complete identity verification to unlock higher transaction limits
        </p>
      </div>

      {/* Current status card */}
      <div className="bg-vault-card border border-vault-border rounded-xl p-5 mb-6 animate-fade-up">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-widest mb-1">Current Status</div>
            <div className="flex items-center gap-2">
              <Shield size={16} className={kycData?.kyc_status === 'approved' ? 'text-emerald-400' : 'text-slate-500'} />
              <span className={clsx(
                'font-medium capitalize',
                kycData?.kyc_status === 'approved' ? 'text-emerald-400' : 'text-amber-400'
              )}>
                {kycData?.kyc_status || 'Pending'}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-500 mb-1">Daily Limit</div>
            <div className="font-display text-lg text-gold">
              {kycData?.daily_limit_inr || '₹0'}
            </div>
          </div>
        </div>

        {/* Tier progress */}
        <div className="mt-4 flex gap-2">
          {TIERS.map(t => {
            const isApproved = approvedTiers.includes(t.id)
            return (
              <div key={t.id} className={clsx(
                'flex-1 p-2.5 rounded-lg border text-xs text-center transition-all',
                isApproved
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                  : 'bg-vault border-vault-border text-slate-600'
              )}>
                <div className="font-medium mb-0.5">{t.id.replace('_', ' ').toUpperCase()}</div>
                <div className="text-xs opacity-70">{t.limit}</div>
                {isApproved && <CheckCircle size={12} className="mx-auto mt-1" />}
              </div>
            )
          })}
        </div>
      </div>

      {/* Past submissions */}
      {kycData?.records?.length > 0 && (
        <div className="bg-vault-card border border-vault-border rounded-xl p-5 mb-6 animate-fade-up delay-100">
          <h2 className="text-sm font-medium text-slate-300 mb-3">Submission History</h2>
          <div className="space-y-2">
            {kycData.records.map(r => (
              <div key={r.id} className="flex items-center justify-between py-2 border-b border-vault-border last:border-0">
                <div className="flex items-center gap-2">
                  {STATUS_ICON[r.status]}
                  <span className="text-sm text-slate-300 capitalize">{r.tier.replace('_', ' ')}</span>
                  <span className="text-xs text-slate-600">· {r.document_type}</span>
                </div>
                <span className="text-xs text-slate-600">{formatDate(r.submitted_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KYC Wizard */}
      {step < 3 && (
        <div className="bg-vault-card border border-vault-border rounded-xl overflow-hidden animate-fade-up delay-200">

          {/* Step indicator */}
          <div className="flex border-b border-vault-border">
            {['Choose Tier', 'Choose Document', 'Submit'].map((s, i) => (
              <div key={i} className={clsx(
                'flex-1 py-3 text-center text-xs font-medium border-b-2 transition-all',
                step === i ? 'border-gold text-gold' : 'border-transparent text-slate-600'
              )}>
                <span className={clsx('mr-1.5 inline-flex w-4 h-4 rounded-full text-xs items-center justify-center',
                  step > i ? 'bg-emerald-500 text-white' : step === i ? 'bg-gold text-vault-surface' : 'bg-vault text-slate-600'
                )}>{step > i ? '✓' : i + 1}</span>
                {s}
              </div>
            ))}
          </div>

          <div className="p-6">

            {/* Step 0: Choose tier */}
            {step === 0 && (
              <div className="space-y-3">
                <p className="text-sm text-slate-400 mb-4">Select the KYC tier you want to complete.</p>
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
                          ? 'border-emerald-500/20 bg-emerald-500/5 opacity-60 cursor-not-allowed'
                          : 'border-vault-border hover:border-gold/40 hover:bg-white/5 cursor-pointer'
                      )}
                    >
                      <div>
                        <div className="text-sm font-medium text-slate-200 flex items-center gap-2">
                          {t.label}
                          {isApproved && <CheckCircle size={13} className="text-emerald-400" />}
                        </div>
                        <div className="text-xs text-slate-500 mt-0.5">Daily limit: {t.limit}</div>
                      </div>
                      {!isApproved && <ChevronRight size={16} className="text-slate-600" />}
                    </button>
                  )
                })}
              </div>
            )}

            {/* Step 1: Choose document */}
            {step === 1 && selectedTier && (
              <div className="space-y-3">
                <p className="text-sm text-slate-400 mb-4">
                  Select a document for <span className="text-gold">{selectedTier.label}</span>
                </p>
                {selectedTier.docs.map(doc => {
                  const Icon = doc.icon
                  return (
                    <button
                      key={doc.value}
                      onClick={() => { setDoc(doc); setStep(2) }}
                      className="w-full flex items-center gap-3 p-4 rounded-xl border border-vault-border hover:border-gold/40 hover:bg-white/5 text-left transition-all"
                    >
                      <Icon size={18} className="text-slate-400 flex-shrink-0" />
                      <span className="text-sm text-slate-200">{doc.label}</span>
                      <ChevronRight size={16} className="text-slate-600 ml-auto" />
                    </button>
                  )
                })}
                <button onClick={() => setStep(0)} className="text-xs text-slate-600 hover:text-slate-400 mt-2">
                  ← Back
                </button>
              </div>
            )}

            {/* Step 2: Enter reference */}
            {step === 2 && selectedDoc && (
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-slate-400 mb-1">
                    Enter the reference ID for your <span className="text-gold">{selectedDoc.label}</span>
                  </p>
                  <p className="text-xs text-slate-600 mb-4">
                    In production, this comes from DigiLocker / KYC provider. For demo, use any string like <code className="text-gold font-mono">DEMO_REF_001</code>
                  </p>
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1.5 uppercase tracking-wider">Document Reference ID</label>
                  <input
                    type="text"
                    value={docRef}
                    onChange={e => setDocRef(e.target.value)}
                    placeholder="e.g. DEMO_REF_001"
                    className="w-full bg-vault border border-vault-border rounded-lg px-3.5 py-3 text-slate-200 font-mono text-sm focus:border-gold transition-colors"
                  />
                </div>
                {error && (
                  <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                    {error}
                  </div>
                )}
                <div className="flex gap-3">
                  <button onClick={() => setStep(1)} className="text-xs text-slate-600 hover:text-slate-400">
                    ← Back
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={loading}
                    className="flex-1 py-3 bg-gold text-vault-surface font-medium rounded-lg text-sm hover:bg-gold-light transition-colors disabled:opacity-40"
                  >
                    {loading ? 'Submitting…' : 'Submit KYC'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 3: Success */}
      {step === 3 && (
        <div className="bg-vault-card border border-emerald-500/20 rounded-xl p-8 text-center animate-fade-up">
          <CheckCircle size={40} className="text-emerald-400 mx-auto mb-4" />
          <h3 className="font-display text-xl text-slate-100 mb-2">KYC Approved</h3>
          <p className="text-sm text-slate-400 mb-6">
            Your {selectedTier?.id} has been verified. Transaction limits updated.
          </p>
          <button
            onClick={reset}
            className="px-6 py-2.5 bg-vault border border-vault-border text-slate-300 rounded-lg text-sm hover:bg-white/5 transition-colors"
          >
            Submit another tier
          </button>
        </div>
      )}
    </div>
  )
}