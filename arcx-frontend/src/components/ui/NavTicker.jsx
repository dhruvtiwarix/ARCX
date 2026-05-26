import { useState, useEffect, useRef } from 'react'
import { oracleApi } from '../../api/index'
import { TrendingUp, TrendingDown, Activity } from 'lucide-react'

/**
 * NavTicker — Phase 12
 * Live ARCX price widget that auto-refreshes every 60 seconds.
 * Shows real NAV from /api/v1/oracle/price (real yfinance data).
 */
export default function NavTicker() {
  const [data,     setData]    = useState(null)
  const [prev,     setPrev]    = useState(null)
  const [pulsing,  setPulsing] = useState(false)
  const [error,    setError]   = useState(false)
  const intervalRef = useRef(null)

  const fetchPrice = async () => {
    try {
      const res = await oracleApi.getLivePrice()
      setData(d => {
        setPrev(d)  // keep previous for delta
        return res
      })
      setError(false)
      // Trigger pulse animation on update
      setPulsing(true)
      setTimeout(() => setPulsing(false), 800)
    } catch {
      setError(true)
    }
  }

  useEffect(() => {
    fetchPrice()
    intervalRef.current = setInterval(fetchPrice, 60_000) // every 60 seconds
    return () => clearInterval(intervalRef.current)
  }, [])

  if (!data && !error) return (
    <div className="px-4 py-3 flex items-center gap-2 opacity-50">
      <Activity size={14} className="animate-pulse text-slate-400" />
      <span className="text-xs text-slate-400">Loading price...</span>
    </div>
  )

  if (error && !data) return (
    <div className="px-4 py-3 flex items-center gap-2 opacity-50">
      <Activity size={14} className="text-slate-400" />
      <span className="text-xs text-slate-400">Price unavailable</span>
    </div>
  )

  const nav     = Number(data?.nav_inr || 0)
  const prevNav = Number(prev?.nav_inr || nav)
  const delta   = nav - prevNav
  const isUp    = delta >= 0

  return (
    <div className="px-4 pb-3">
      <div
        className={`
          glassContainer p-3 rounded-2xl cursor-default
          transition-all duration-500
          ${pulsing ? 'scale-[1.02]' : 'scale-100'}
        `}
        title="Live ARCX NAV — updates every 60s"
      >
        {/* Header row */}
        <div className="flex items-center justify-between mb-1.5 z-10">
          <div className="flex items-center gap-1.5">
            {/* Live pulse dot */}
            <span className="relative flex h-2 w-2">
              <span
                className={`
                  animate-ping absolute inline-flex h-full w-full rounded-full opacity-75
                  ${error ? 'bg-red-400' : 'bg-emerald-400'}
                `}
              />
              <span
                className={`
                  relative inline-flex rounded-full h-2 w-2
                  ${error ? 'bg-red-500' : 'bg-emerald-500'}
                `}
              />
            </span>
            <span className="text-[10px] font-bold tracking-widest uppercase text-slate-400 z-10">ARCX</span>
          </div>
          <span className="text-[9px] text-slate-500 z-10">Live</span>
        </div>

        {/* Price row */}
        <div className="flex items-baseline gap-2 z-10">
          <span
            className={`
              font-display font-semibold text-[18px] leading-none tracking-tight
              transition-colors duration-500 z-10
              ${isUp ? 'text-[#1D1D1F] dark:text-[#F5F5F7]' : 'text-[#1D1D1F] dark:text-[#F5F5F7]'}
            `}
          >
            &#8377;{nav.toFixed(4)}
          </span>
          {prev && delta !== 0 && (
            <span
              className={`
                text-[11px] font-bold flex items-center gap-0.5 z-10
                ${isUp ? 'text-emerald-500' : 'text-red-500'}
              `}
            >
              {isUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
              {isUp ? '+' : ''}{delta.toFixed(4)}
            </span>
          )}
        </div>

        {/* Sub-row: USD price */}
        <div className="mt-1 flex items-center justify-between z-10">
          <span className="text-[10px] text-slate-500 z-10">
            ${Number(data?.nav_usd || 0).toFixed(6)}
          </span>
          <span className="text-[9px] text-slate-500 z-10">
            SPY ${Number(data?.spy_usd || 0).toFixed(0)} · GLD ${Number(data?.gld_usd || 0).toFixed(0)}
          </span>
        </div>
      </div>
    </div>
  )
}
