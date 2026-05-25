import { clsx } from 'clsx';

export default function StatCard({ icon: Icon, label, value, subValue, trend, className }) {
  const isPositive = trend === 'up';
  const isNegative = trend === 'down';

  return (
    <div
      className={clsx(
        'glass rounded-2xl p-5 border border-white/[0.06] transition-all duration-300',
        'hover:border-white/[0.12] hover:shadow-[0_0_30px_-5px_rgba(34,211,238,0.08)]',
        'animate-[fadeIn_0.5s_ease-out]',
        className
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/20 to-emerald-500/10 border border-cyan-500/10">
          {Icon && <Icon className="h-5 w-5 text-cyan-400" />}
        </div>
        {trend && (
          <span
            className={clsx(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
              isPositive && 'bg-emerald-500/15 text-emerald-400',
              isNegative && 'bg-red-500/15 text-red-400'
            )}
          >
            {isPositive ? '↑' : '↓'}
            {subValue}
          </span>
        )}
      </div>
      <p className="text-xs font-medium text-[var(--arcx-text-secondary)] uppercase tracking-wider mb-1">
        {label}
      </p>
      <p className="text-xl font-bold text-[var(--arcx-text-primary)] font-mono tracking-tight">
        {value || '—'}
      </p>
      {!trend && subValue && (
        <p className="text-xs text-[var(--arcx-text-secondary)] mt-1 font-mono">{subValue}</p>
      )}
    </div>
  );
}
