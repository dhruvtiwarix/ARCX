import { useState, useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { formatINR, formatDate } from '../../utils/format';

const timeRanges = [
  { label: '7D',   days: 7 },
  { label: '30D',  days: 30 },
  { label: '90D',  days: 90 },
  { label: '365D', days: 365 },
];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="glass rounded-xl p-3 border border-white/[0.1] shadow-2xl min-w-[180px]">
      <p className="text-xs text-[var(--arcx-text-secondary)] mb-2">{formatDate(d.nav_date)}</p>
      <div className="space-y-1">
        <div className="flex justify-between gap-4">
          <span className="text-xs text-[var(--arcx-text-secondary)]">NAV (INR)</span>
          <span className="text-sm font-semibold text-[var(--arcx-text-primary)] font-mono">{formatINR(d.nav_inr)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-xs text-[var(--arcx-text-secondary)]">NAV (USD)</span>
          <span className="text-sm font-semibold text-[var(--arcx-text-primary)] font-mono">${parseFloat(d.nav_usd).toFixed(4)}</span>
        </div>
        {parseFloat(d.dividend_accrued_inr) > 0 && (
          <div className="flex justify-between gap-4">
            <span className="text-xs text-[var(--arcx-text-secondary)]">Dividend</span>
            <span className="text-sm font-medium text-emerald-400 font-mono">+{formatINR(d.dividend_accrued_inr)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function NAVChart({ data = [], onRangeChange, activeRange = 30 }) {
  // Sort chronologically for the chart (API returns newest first)
  const chartData = useMemo(() => [...data].reverse(), [data]);

  const priceChange = useMemo(() => {
    if (chartData.length < 2) return null;
    const first = parseFloat(chartData[0].nav_inr);
    const last  = parseFloat(chartData[chartData.length - 1].nav_inr);
    if (first === 0) return null;
    return ((last - first) / first * 100).toFixed(2);
  }, [chartData]);

  const isPositive = priceChange !== null && parseFloat(priceChange) >= 0;
  const gradientId = 'navGradient';

  return (
    <div className="glass rounded-2xl border border-white/[0.06] p-5 animate-[fadeIn_0.6s_ease-out]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h3 className="text-base font-semibold text-[var(--arcx-text-primary)]">NAV Price History</h3>
          {priceChange !== null && (
            <p className={`text-sm font-medium mt-0.5 ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
              {isPositive ? '+' : ''}{priceChange}% over {activeRange} days
            </p>
          )}
        </div>
        <div className="flex gap-1 p-1 rounded-xl bg-white/[0.04] border border-white/[0.06]">
          {timeRanges.map(({ label, days }) => (
            <button
              key={days}
              onClick={() => onRangeChange?.(days)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                activeRange === days
                  ? 'bg-gradient-to-r from-cyan-500/20 to-emerald-500/15 text-cyan-400 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.2)]'
                  : 'text-[var(--arcx-text-secondary)] hover:text-[var(--arcx-text-primary)] hover:bg-white/[0.04]'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      {chartData.length > 0 ? (
        <div className="h-[320px] -mx-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={isPositive ? '#34d399' : '#f87171'} stopOpacity={0.3} />
                  <stop offset="50%" stopColor={isPositive ? '#34d399' : '#f87171'} stopOpacity={0.08} />
                  <stop offset="100%" stopColor={isPositive ? '#34d399' : '#f87171'} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="nav_date"
                tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                tick={{ fill: '#64748b', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                tickLine={false}
                minTickGap={40}
              />
              <YAxis
                tickFormatter={(v) => `₹${v}`}
                tick={{ fill: '#64748b', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={65}
                domain={['auto', 'auto']}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="nav_inr"
                stroke={isPositive ? '#34d399' : '#f87171'}
                strokeWidth={2}
                fill={`url(#${gradientId})`}
                dot={false}
                activeDot={{
                  r: 5,
                  fill: isPositive ? '#34d399' : '#f87171',
                  stroke: '#0a0e1a',
                  strokeWidth: 2,
                }}
                animationDuration={1200}
                animationEasing="ease-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[320px] flex items-center justify-center">
          <div className="text-center">
            <div className="text-4xl mb-3 opacity-40">📊</div>
            <p className="text-sm text-[var(--arcx-text-secondary)]">No NAV history data available yet.</p>
            <p className="text-xs text-[var(--arcx-text-secondary)] mt-1 opacity-60">
              Data populates after the first EOD NAV publish.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
