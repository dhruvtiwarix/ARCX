import { useState } from 'react';
import { ArrowUpFromLine, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import useStore from '../../store/useStore';
import { formatINR } from '../../utils/format';

export default function WithdrawForm({ currentNAV, balance }) {
  const [amount, setAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const withdraw = useStore((s) => s.withdraw);

  const navINR = currentNAV ? parseFloat(currentNAV) : null;
  const amountNum = parseFloat(amount) || 0;
  const balanceNum = parseFloat(balance) || 0;
  const estimatedINR = navINR && amountNum > 0 ? (amountNum * navINR).toFixed(2) : null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (amountNum < 0.01 || amountNum > balanceNum) return;
    setShowConfirm(true);
  };

  const handleConfirm = async () => {
    setShowConfirm(false);
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await withdraw(amount);
      setResult(data);
      setAmount('');
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Withdrawal failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const quickPercentages = [25, 50, 75, 100];

  return (
    <div className="glass rounded-2xl border border-white/[0.06] p-5">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-red-500/15 border border-red-500/10">
          <ArrowUpFromLine className="h-4 w-4 text-red-400" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[var(--arcx-text-primary)]">Withdraw ARCX</h3>
          <p className="text-xs text-[var(--arcx-text-secondary)]">Convert ARCX → INR</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Amount Input */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-medium text-[var(--arcx-text-secondary)]">
              Amount (ARCX)
            </label>
            <span className="text-xs text-[var(--arcx-text-secondary)] font-mono">
              Balance: {balanceNum > 0 ? parseFloat(balanceNum.toFixed(6)) : '0'}
            </span>
          </div>
          <input
            id="withdraw-amount"
            type="number"
            min="0.01"
            step="0.000001"
            max={balanceNum}
            value={amount}
            onChange={(e) => { setAmount(e.target.value); setResult(null); setError(null); setShowConfirm(false); }}
            placeholder="10.000000"
            className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[var(--arcx-text-primary)] text-sm font-mono placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/30 transition"
          />
        </div>

        {/* Quick percentage buttons */}
        <div className="flex gap-2">
          {quickPercentages.map((pct) => (
            <button
              key={pct}
              type="button"
              onClick={() => {
                const val = (balanceNum * pct / 100).toFixed(6);
                setAmount(val);
                setResult(null);
                setError(null);
                setShowConfirm(false);
              }}
              className="flex-1 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-[var(--arcx-text-secondary)] hover:text-[var(--arcx-text-primary)] hover:bg-white/[0.08] transition"
            >
              {pct}%
            </button>
          ))}
        </div>

        {/* Preview */}
        {estimatedINR && (
          <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-cyan-500/[0.06] border border-cyan-500/10">
            <span className="text-xs text-[var(--arcx-text-secondary)]">You'll receive approx.</span>
            <span className="text-sm font-semibold text-cyan-400 font-mono">{formatINR(estimatedINR)}</span>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || amountNum < 0.01 || amountNum > balanceNum}
          className="w-full py-2.5 rounded-xl bg-gradient-to-r from-red-500/80 to-orange-500/80 text-white text-sm font-semibold transition-all duration-200 hover:shadow-[0_0_20px_-3px_rgba(248,113,113,0.4)] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            'Withdraw'
          )}
        </button>
      </form>

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-[fadeIn_0.2s_ease-out]">
          <div className="glass rounded-2xl border border-white/[0.1] p-6 max-w-sm mx-4 w-full shadow-2xl animate-[slideUp_0.3s_ease-out]">
            <h4 className="text-base font-semibold text-[var(--arcx-text-primary)] mb-2">Confirm Withdrawal</h4>
            <p className="text-sm text-[var(--arcx-text-secondary)] mb-4">
              You are about to withdraw <span className="text-[var(--arcx-text-primary)] font-semibold font-mono">{amount} ARCX</span>
              {estimatedINR && (
                <> for approximately <span className="text-[var(--arcx-text-primary)] font-semibold font-mono">{formatINR(estimatedINR)}</span></>
              )}.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 py-2 rounded-xl bg-white/[0.06] border border-white/[0.08] text-sm font-medium text-[var(--arcx-text-secondary)] hover:bg-white/[0.1] transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className="flex-1 py-2 rounded-xl bg-gradient-to-r from-red-500 to-orange-500 text-white text-sm font-semibold hover:shadow-[0_0_20px_-3px_rgba(248,113,113,0.4)] transition"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="mt-4 p-3 rounded-xl bg-emerald-500/[0.08] border border-emerald-500/15 animate-[slideUp_0.3s_ease-out]">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span className="text-sm font-medium text-emerald-400">Withdrawal Successful</span>
          </div>
          <div className="space-y-1 text-xs text-[var(--arcx-text-secondary)]">
            <p>INR Returned: <span className="text-[var(--arcx-text-primary)] font-mono">{formatINR(result.inr_returned)}</span></p>
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
