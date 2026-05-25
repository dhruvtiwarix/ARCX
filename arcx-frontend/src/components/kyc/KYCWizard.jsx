import { useState } from 'react';
import { ChevronRight, ChevronLeft, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import useStore from '../../store/useStore';
import { clsx } from 'clsx';

const tiers = [
  { value: 'tier_1', label: 'Tier 1 — Basic',    desc: 'Phone + Aadhaar OTP',  limit: '₹10,000/day' },
  { value: 'tier_2', label: 'Tier 2 — Standard',  desc: 'PAN + Selfie',         limit: '₹1,00,000/day' },
  { value: 'tier_3', label: 'Tier 3 — Full',      desc: 'Full address proof',   limit: 'Unlimited' },
];

const documentTypes = [
  { value: 'aadhaar',  label: 'Aadhaar Card' },
  { value: 'pan',      label: 'PAN Card' },
  { value: 'passport', label: 'Passport' },
  { value: 'dl',       label: 'Driving License' },
];

const steps = ['Select Tier', 'Document Type', 'Document ID', 'Review & Submit'];

export default function KYCWizard() {
  const [step, setStep] = useState(0);
  const [tier, setTier] = useState('');
  const [docType, setDocType] = useState('');
  const [docRef, setDocRef] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const submitKYC = useStore((s) => s.submitKYC);

  const canNext = () => {
    if (step === 0) return !!tier;
    if (step === 1) return !!docType;
    if (step === 2) return docRef.trim().length > 4;
    return true;
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      await submitKYC({ tier, document_type: docType, document_ref: docRef });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'KYC submission failed');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="glass rounded-2xl border border-emerald-500/15 p-8 text-center animate-[slideUp_0.4s_ease-out]">
        <CheckCircle2 className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-[var(--arcx-text-primary)] mb-2">KYC Submitted</h3>
        <p className="text-sm text-[var(--arcx-text-secondary)]">
          Your documents are under review. You'll be notified once verified (typically 24-48 hours).
        </p>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl border border-white/[0.06] p-5 animate-[fadeIn_0.4s_ease-out]">
      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <div className={clsx(
                'flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-all duration-300',
                i <= step
                  ? 'bg-gradient-to-br from-cyan-500 to-emerald-500 text-[#0a0e1a]'
                  : 'bg-white/[0.06] text-[var(--arcx-text-secondary)]'
              )}>
                {i + 1}
              </div>
              <span className={clsx(
                'text-xs font-medium hidden sm:inline',
                i <= step ? 'text-[var(--arcx-text-primary)]' : 'text-[var(--arcx-text-secondary)]'
              )}>
                {s}
              </span>
              {i < steps.length - 1 && (
                <ChevronRight className="h-3.5 w-3.5 text-white/10 mx-1 hidden sm:inline" />
              )}
            </div>
          ))}
        </div>
        <div className="h-1 rounded-full bg-white/[0.06]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-500"
            style={{ width: `${((step + 1) / steps.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Step Content */}
      <div className="min-h-[200px]">
        {step === 0 && (
          <div className="space-y-3 animate-[fadeIn_0.3s_ease-out]">
            <h4 className="text-sm font-semibold text-[var(--arcx-text-primary)] mb-3">Select Verification Tier</h4>
            {tiers.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setTier(t.value)}
                className={clsx(
                  'w-full p-4 rounded-xl border text-left transition-all duration-200',
                  tier === t.value
                    ? 'border-cyan-500/30 bg-cyan-500/[0.06] shadow-[inset_0_0_0_1px_rgba(34,211,238,0.15)]'
                    : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]'
                )}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-[var(--arcx-text-primary)]">{t.label}</p>
                    <p className="text-xs text-[var(--arcx-text-secondary)] mt-0.5">{t.desc}</p>
                  </div>
                  <span className="text-xs font-medium text-cyan-400 font-mono">{t.limit}</span>
                </div>
              </button>
            ))}
          </div>
        )}

        {step === 1 && (
          <div className="space-y-3 animate-[fadeIn_0.3s_ease-out]">
            <h4 className="text-sm font-semibold text-[var(--arcx-text-primary)] mb-3">Select Document Type</h4>
            <div className="grid grid-cols-2 gap-3">
              {documentTypes.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => setDocType(d.value)}
                  className={clsx(
                    'p-4 rounded-xl border text-center transition-all duration-200',
                    docType === d.value
                      ? 'border-cyan-500/30 bg-cyan-500/[0.06]'
                      : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]'
                  )}
                >
                  <p className="text-sm font-medium text-[var(--arcx-text-primary)]">{d.label}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="animate-[fadeIn_0.3s_ease-out]">
            <h4 className="text-sm font-semibold text-[var(--arcx-text-primary)] mb-3">Enter Document Reference</h4>
            <p className="text-xs text-[var(--arcx-text-secondary)] mb-4">
              Enter your document number. We store only the reference — actual documents are verified via DigiLocker/NSDL.
            </p>
            <input
              id="kyc-doc-ref"
              type="text"
              value={docRef}
              onChange={(e) => setDocRef(e.target.value)}
              placeholder={docType === 'aadhaar' ? 'XXXX XXXX XXXX' : docType === 'pan' ? 'ABCDE1234F' : 'Document Number'}
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm font-mono placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
            />
          </div>
        )}

        {step === 3 && (
          <div className="animate-[fadeIn_0.3s_ease-out]">
            <h4 className="text-sm font-semibold text-[var(--arcx-text-primary)] mb-4">Review & Submit</h4>
            <div className="space-y-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="flex justify-between">
                <span className="text-xs text-[var(--arcx-text-secondary)]">Tier</span>
                <span className="text-sm font-medium text-[var(--arcx-text-primary)]">{tiers.find(t => t.value === tier)?.label}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-[var(--arcx-text-secondary)]">Document</span>
                <span className="text-sm font-medium text-[var(--arcx-text-primary)]">{documentTypes.find(d => d.value === docType)?.label}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-[var(--arcx-text-secondary)]">Reference</span>
                <span className="text-sm font-medium text-[var(--arcx-text-primary)] font-mono">{docRef}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 p-3 rounded-xl bg-red-500/[0.08] border border-red-500/15">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <span className="text-sm text-red-400">{error}</span>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex gap-3 mt-6">
        {step > 0 && (
          <button
            onClick={() => setStep(step - 1)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/[0.06] border border-white/[0.08] text-sm font-medium text-[var(--arcx-text-secondary)] hover:bg-white/[0.1] transition"
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </button>
        )}
        <div className="flex-1" />
        {step < 3 ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!canNext()}
            className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 text-[#0a0e1a] text-sm font-semibold transition-all hover:shadow-[0_0_20px_-3px_rgba(34,211,238,0.3)] disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 text-[#0a0e1a] text-sm font-semibold transition-all hover:shadow-[0_0_20px_-3px_rgba(34,211,238,0.3)] disabled:opacity-40"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {loading ? 'Submitting...' : 'Submit KYC'}
          </button>
        )}
      </div>
    </div>
  );
}
