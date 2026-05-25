import { useEffect } from 'react';
import { Menu, TrendingUp, TrendingDown } from 'lucide-react';
import useStore from '../../store/useStore';
import { formatINR } from '../../utils/format';

export default function Navbar({ onMenuClick }) {
  const livePrice = useStore((s) => s.livePrice);
  const fetchLivePrice = useStore((s) => s.fetchLivePrice);

  useEffect(() => {
    fetchLivePrice();
    const interval = setInterval(fetchLivePrice, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, [fetchLivePrice]);

  const navINR = livePrice?.nav_inr ? parseFloat(livePrice.nav_inr) : null;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-white/[0.06] bg-[var(--arcx-bg-primary)]/80 backdrop-blur-xl px-4 md:px-6">
      {/* Mobile menu button */}
      <button
        onClick={onMenuClick}
        className="p-2 rounded-lg hover:bg-white/[0.06] transition lg:hidden"
      >
        <Menu className="h-5 w-5 text-[var(--arcx-text-secondary)]" />
      </button>

      {/* Page title area - left spacer on desktop */}
      <div className="hidden lg:block" />

      {/* Live NAV Ticker */}
      <div className="flex items-center gap-4">
        {navINR !== null && (
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl glass border border-white/[0.06]">
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-medium text-[var(--arcx-text-secondary)] uppercase tracking-wider">
                Live NAV
              </span>
            </div>
            <span className="text-sm font-semibold text-[var(--arcx-text-primary)] font-mono">
              {formatINR(navINR)}
            </span>
            {livePrice?.nav_usd && (
              <span className="text-xs text-[var(--arcx-text-secondary)] font-mono">
                (${parseFloat(livePrice.nav_usd).toFixed(4)})
              </span>
            )}
          </div>
        )}

        {/* Sources indicator */}
        {livePrice?.sources_used && (
          <div className="hidden md:flex items-center gap-1.5 text-xs text-[var(--arcx-text-secondary)]">
            <div className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            {livePrice.sources_used.join(', ')}
          </div>
        )}
      </div>
    </header>
  );
}
