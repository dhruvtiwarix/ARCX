import { AlertTriangle, ShieldAlert, XOctagon } from 'lucide-react';

const tierConfig = {
  tier_1: {
    icon: AlertTriangle,
    label: 'Tier 1 — Caution',
    bg: 'from-amber-500/15 to-amber-600/5',
    border: 'border-amber-500/20',
    text: 'text-amber-400',
    description: 'Market volatility detected. New deposits temporarily suspended.',
  },
  tier_2: {
    icon: ShieldAlert,
    label: 'Tier 2 — Warning',
    bg: 'from-orange-500/15 to-red-500/5',
    border: 'border-orange-500/20',
    text: 'text-orange-400',
    description: 'Elevated market stress. Deposits and transfers are suspended.',
  },
  tier_3: {
    icon: XOctagon,
    label: 'Tier 3 — Emergency Halt',
    bg: 'from-red-500/20 to-red-600/5',
    border: 'border-red-500/25',
    text: 'text-red-400',
    description: 'Circuit breaker active. All transactions halted for safety. Read-only mode.',
  },
};

export default function CircuitBreakerBanner({ tier, reason, marketDrop }) {
  if (!tier || !tierConfig[tier]) return null;

  const config = tierConfig[tier];
  const Icon = config.icon;

  return (
    <div
      className={`
        relative overflow-hidden rounded-2xl border ${config.border}
        bg-gradient-to-r ${config.bg} p-4 md:p-5
        animate-[fadeIn_0.3s_ease-out]
      `}
    >
      {/* Animated pulse background */}
      <div className="absolute inset-0 opacity-30">
        <div className={`absolute -top-1/2 -left-1/2 w-full h-full rounded-full ${config.text} blur-[100px] animate-pulse`}
             style={{ background: tier === 'tier_3' ? 'rgba(248,113,113,0.15)' : 'rgba(251,191,36,0.1)' }} />
      </div>

      <div className="relative flex items-start gap-3">
        <div className={`shrink-0 p-2 rounded-xl bg-white/[0.06] ${config.text}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className={`text-sm font-semibold ${config.text}`}>{config.label}</h4>
            {marketDrop && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-white/[0.06] text-[var(--arcx-text-secondary)] font-mono">
                Market drop: {marketDrop}%
              </span>
            )}
          </div>
          <p className="text-sm text-[var(--arcx-text-secondary)] mt-1">{config.description}</p>
          {reason && (
            <p className="text-xs text-[var(--arcx-text-secondary)] mt-2 opacity-70">
              Reason: {reason}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
