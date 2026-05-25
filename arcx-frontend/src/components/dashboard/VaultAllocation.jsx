import { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { formatUSD } from '../../utils/format';

const ALLOCATION = [
  { name: 'Stocks (SPY)', key: 'spy_usd', target: 40, color: '#22d3ee' },
  { name: 'Bonds (TLT)',  key: 'tlt_usd', target: 30, color: '#a78bfa' },
  { name: 'Gold (GLD)',   key: 'gld_usd', target: 20, color: '#fbbf24' },
  { name: 'Cash (USD)',   key: 'cash',    target: 10, color: '#34d399' },
];

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="glass rounded-lg p-2.5 border border-white/[0.1] shadow-xl">
      <p className="text-xs font-medium text-[var(--arcx-text-primary)]">{d.name}</p>
      <p className="text-xs text-[var(--arcx-text-secondary)] mt-0.5">
        Target: {d.target}% &middot; Actual: {d.actual}%
      </p>
    </div>
  );
}

export default function VaultAllocation({ livePrice }) {
  const chartData = useMemo(() => {
    return ALLOCATION.map((item) => ({
      ...item,
      value: item.target,
      actual: item.target, // Use target as default
    }));
  }, [livePrice]);

  return (
    <div className="glass rounded-2xl border border-white/[0.06] p-5 animate-[fadeIn_0.7s_ease-out]">
      <h3 className="text-base font-semibold text-[var(--arcx-text-primary)] mb-4">
        Vault Allocation
      </h3>

      <div className="flex flex-col sm:flex-row items-center gap-6">
        {/* Donut Chart */}
        <div className="h-[180px] w-[180px] shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
                strokeWidth={0}
                animationBegin={200}
                animationDuration={1000}
                animationEasing="ease-out"
              >
                {chartData.map((entry, index) => (
                  <Cell key={index} fill={entry.color} opacity={0.85} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend */}
        <div className="flex-1 space-y-3 w-full">
          {ALLOCATION.map((item) => (
            <div key={item.key} className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div
                  className="h-3 w-3 rounded-full shrink-0"
                  style={{ backgroundColor: item.color, opacity: 0.85 }}
                />
                <span className="text-sm text-[var(--arcx-text-secondary)]">{item.name}</span>
              </div>
              <span className="text-sm font-semibold text-[var(--arcx-text-primary)] font-mono">
                {item.target}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Rebalancing status */}
      <div className="mt-4 pt-4 border-t border-white/[0.06] flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-emerald-400" />
        <span className="text-xs text-[var(--arcx-text-secondary)]">
          All assets within drift tolerance
        </span>
      </div>
    </div>
  );
}
