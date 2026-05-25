import { Shield, CheckCircle2, Clock, XCircle, AlertTriangle } from 'lucide-react';
import { clsx } from 'clsx';

const statusConfig = {
  pending:   { icon: Clock,         label: 'Pending Review',  color: 'text-amber-400',   bg: 'from-amber-500/15 to-amber-600/5',   border: 'border-amber-500/15',   desc: 'Your KYC documents are under review. This usually takes 24-48 hours.' },
  approved:  { icon: CheckCircle2,  label: 'Approved',        color: 'text-emerald-400', bg: 'from-emerald-500/15 to-emerald-600/5', border: 'border-emerald-500/15', desc: 'Your identity is verified. You have full access to deposit, withdraw, and transfer ARCX.' },
  rejected:  { icon: XCircle,       label: 'Rejected',        color: 'text-red-400',     bg: 'from-red-500/15 to-red-600/5',       border: 'border-red-500/15',     desc: 'Your verification was not successful. Please re-submit with valid documents.' },
  suspended: { icon: AlertTriangle, label: 'Suspended',       color: 'text-orange-400',  bg: 'from-orange-500/15 to-orange-600/5', border: 'border-orange-500/15',  desc: 'Your account has been temporarily suspended by compliance. Contact support.' },
};

export default function KYCStatusCard({ status }) {
  if (!status) {
    return (
      <div className="glass rounded-2xl border border-white/[0.06] p-6 text-center">
        <Shield className="h-10 w-10 text-[var(--arcx-text-secondary)] mx-auto mb-3 opacity-40" />
        <h3 className="text-base font-semibold text-[var(--arcx-text-primary)] mb-1">KYC Not Submitted</h3>
        <p className="text-sm text-[var(--arcx-text-secondary)]">
          Complete your identity verification to unlock deposits, withdrawals, and transfers.
        </p>
      </div>
    );
  }

  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <div className={clsx(
      'rounded-2xl border p-6',
      config.border,
      `bg-gradient-to-r ${config.bg}`,
      'animate-[fadeIn_0.4s_ease-out]'
    )}>
      <div className="flex items-start gap-4">
        <div className={clsx('flex h-12 w-12 items-center justify-center rounded-xl bg-white/[0.06] shrink-0', config.color)}>
          <Icon className="h-6 w-6" />
        </div>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-base font-semibold text-[var(--arcx-text-primary)]">KYC Status</h3>
            <span className={clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', config.color, 'bg-white/[0.06]')}>
              {config.label}
            </span>
          </div>
          <p className="text-sm text-[var(--arcx-text-secondary)]">{config.desc}</p>
        </div>
      </div>
    </div>
  );
}
