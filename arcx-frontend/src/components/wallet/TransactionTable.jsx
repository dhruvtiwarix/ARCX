import { useMemo } from 'react';
import { ArrowDownToLine, ArrowUpFromLine, ArrowRightLeft, Sparkles } from 'lucide-react';
import { formatINR, formatDate, formatArcx, shortenUUID } from '../../utils/format';
import { clsx } from 'clsx';

const txTypeConfig = {
  deposit:  { icon: ArrowDownToLine, label: 'Deposit',  color: 'text-emerald-400', bg: 'bg-emerald-500/15', border: 'border-emerald-500/10' },
  withdraw: { icon: ArrowUpFromLine, label: 'Withdraw', color: 'text-red-400',     bg: 'bg-red-500/15',     border: 'border-red-500/10' },
  transfer: { icon: ArrowRightLeft,  label: 'Transfer', color: 'text-cyan-400',    bg: 'bg-cyan-500/15',    border: 'border-cyan-500/10' },
  dividend: { icon: Sparkles,        label: 'Dividend', color: 'text-purple-400',  bg: 'bg-purple-500/15',  border: 'border-purple-500/10' },
};

const statusConfig = {
  completed: { label: 'Completed', dot: 'bg-emerald-400' },
  pending:   { label: 'Pending',   dot: 'bg-amber-400' },
  failed:    { label: 'Failed',    dot: 'bg-red-400' },
  reversed:  { label: 'Reversed',  dot: 'bg-gray-400' },
};

export default function TransactionTable({ transactions = [], loading }) {
  if (loading) {
    return (
      <div className="glass rounded-2xl border border-white/[0.06] p-6">
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 rounded-xl bg-white/[0.03] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl border border-white/[0.06] overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/[0.06]">
        <h3 className="text-base font-semibold text-[var(--arcx-text-primary)]">Transaction History</h3>
        <p className="text-xs text-[var(--arcx-text-secondary)] mt-0.5">
          {transactions.length} transaction{transactions.length !== 1 ? 's' : ''}
        </p>
      </div>

      {transactions.length === 0 ? (
        <div className="p-8 text-center">
          <div className="text-4xl mb-3 opacity-40">📜</div>
          <p className="text-sm text-[var(--arcx-text-secondary)]">No transactions yet.</p>
          <p className="text-xs text-[var(--arcx-text-secondary)] mt-1 opacity-60">
            Your deposit and withdrawal history will appear here.
          </p>
        </div>
      ) : (
        <>
          {/* Desktop table header */}
          <div className="hidden md:grid grid-cols-[1fr_1fr_1fr_1fr_0.8fr_0.8fr] gap-4 px-5 py-2.5 border-b border-white/[0.04] text-xs font-medium text-[var(--arcx-text-secondary)] uppercase tracking-wider">
            <span>Type</span>
            <span>ARCX</span>
            <span>INR</span>
            <span>NAV</span>
            <span>Status</span>
            <span>Date</span>
          </div>

          {/* Rows */}
          <div className="divide-y divide-white/[0.04]">
            {transactions.map((tx, idx) => {
              const type = txTypeConfig[tx.tx_type] || txTypeConfig.deposit;
              const status = statusConfig[tx.status] || statusConfig.pending;
              const Icon = type.icon;

              return (
                <div
                  key={tx.id}
                  className="px-5 py-3 hover:bg-white/[0.02] transition-colors duration-150 animate-[fadeIn_0.3s_ease-out]"
                  style={{ animationDelay: `${idx * 50}ms`, animationFillMode: 'both' }}
                >
                  {/* Mobile layout */}
                  <div className="md:hidden space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={clsx('flex h-7 w-7 items-center justify-center rounded-lg', type.bg, type.border, 'border')}>
                          <Icon className={clsx('h-3.5 w-3.5', type.color)} />
                        </div>
                        <div>
                          <span className={clsx('text-sm font-medium', type.color)}>{type.label}</span>
                          <p className="text-xs text-[var(--arcx-text-secondary)]">{formatDate(tx.created_at)}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-[var(--arcx-text-primary)] font-mono">
                          {tx.tx_type === 'withdraw' ? '-' : '+'}{formatArcx(tx.amount_arcx)}
                        </p>
                        <p className="text-xs text-[var(--arcx-text-secondary)] font-mono">{formatINR(tx.amount_inr)}</p>
                      </div>
                    </div>
                  </div>

                  {/* Desktop layout */}
                  <div className="hidden md:grid grid-cols-[1fr_1fr_1fr_1fr_0.8fr_0.8fr] gap-4 items-center">
                    <div className="flex items-center gap-2">
                      <div className={clsx('flex h-7 w-7 items-center justify-center rounded-lg', type.bg, type.border, 'border')}>
                        <Icon className={clsx('h-3.5 w-3.5', type.color)} />
                      </div>
                      <span className={clsx('text-sm font-medium', type.color)}>{type.label}</span>
                    </div>
                    <span className="text-sm font-mono text-[var(--arcx-text-primary)]">
                      {tx.tx_type === 'withdraw' ? '-' : '+'}{formatArcx(tx.amount_arcx)}
                    </span>
                    <span className="text-sm font-mono text-[var(--arcx-text-secondary)]">
                      {formatINR(tx.amount_inr)}
                    </span>
                    <span className="text-sm font-mono text-[var(--arcx-text-secondary)]">
                      {formatINR(tx.nav_at_tx)}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <div className={clsx('h-1.5 w-1.5 rounded-full', status.dot)} />
                      <span className="text-xs text-[var(--arcx-text-secondary)]">{status.label}</span>
                    </div>
                    <span className="text-xs text-[var(--arcx-text-secondary)]">
                      {formatDate(tx.created_at)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
