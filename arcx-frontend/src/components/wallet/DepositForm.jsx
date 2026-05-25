import { useState } from 'react';
import { ArrowDownToLine, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import useStore from '../../store/useStore';
import { formatINR } from '../../utils/format';

export default function DepositForm({ currentNAV }) {
  const [amount, setAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const deposit = useStore((s) => s.deposit);

  const navINR = currentNAV ? parseFloat(currentNAV) : null;
  const amountNum = parseFloat(amount) || 0;
  const estimatedArcx = navINR && amountNum >= 100 ? (amountNum / navINR).toFixed(6) : null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (amountNum < 100) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await deposit(amount);
      setResult(data);
      setAmount('');
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Deposit failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const quickAmounts = [1000, 5000, 10000, 25000];

  return (
    <div className="glass rounded-2xl border border-white/[0.06] p-5">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/15 border border-emerald-500/10">
          <ArrowDownToLine className="h-4 w-4 text-emerald-400" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[var(--arcx-text-primary)]">Deposit INR</h3>
          <p className="text-xs text-[var(--arcx-text-secondary)]">Convert INR → ARCX tokens</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Amount Input */}
        <div>
          <label className="block text-xs font-medium text-[var(--arcx-text-secondary)] mb-1.5">
            Amount (₹)
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--arcx-text-secondary)] text-sm">₹</span>
            <input
              id="deposit-amount"
              type="number"
              min="100"
              step="0.01"
              value={amount}
              onChange={(e) => { setAmount(e.target.value); setResult(null); setError(null); }}
              placeholder="5,000.00"
              className="w-full pl-7 pr-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm font-mono placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
            />
          </div>
        </div>

        {/* Quick amount buttons */}
        <div className="flex gap-2 flex-wrap">
          {quickAmounts.map((qa) => (
            <button
              key={qa}
              type="button"
              onClick={() => { setAmount(String(qa)); setResult(null); setError(null); }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-[var(--arcx-text-secondary)] hover:text-[var(--arcx-text-primary)] hover:bg-white/[0.08] transition"
            >
              ₹{qa.toLocaleString('en-IN')}
            </button>
          ))}
        </div>

        {/* Preview */}
        {estimatedArcx && (
          <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/10">
            <span className="text-xs text-[var(--arcx-text-secondary)]">You'll receive approx.</span>
            <span className="text-sm font-semibold text-emerald-400 font-mono">{estimatedArcx} ARCX</span>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || amountNum < 100}
          className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-[#0a0e1a] text-sm font-semibold transition-all duration-200 hover:shadow-[0_0_20px_-3px_rgba(52,211,153,0.4)] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            'Deposit'
          )}
        </button>
      </form>

      {/* Success */}
      {result && (
        <div className="mt-4 p-3 rounded-xl bg-emerald-500/[0.08] border border-emerald-500/15 animate-[slideUp_0.3s_ease-out]">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span className="text-sm font-medium text-emerald-400">Deposit Successful</span>
          </div>
          <div className="space-y-1 text-xs text-[var(--arcx-text-secondary)]">
            <p>Credited: <span className="text-[var(--arcx-text-primary)] font-mono">{result.arcx_credited} ARCX</span></p>
            <p>NAV at Tx: <span className="font-mono">{formatINR(result.nav_at_tx)}</span></p>
            <p>New Balance: <span className="text-[var(--arcx-text-primary)] font-mono">{result.new_balance} ARCX</span></p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 p-3 rounded-xl bg-red-500/[0.08] border border-red-500/15 animate-[slideUp_0.3s_ease-out]">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <span className="text-sm text-red-400">{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}
