/**
 * ARCX Formatting Utilities
 *
 * All monetary values from the API arrive as strings.
 * Every formatter defensively coerces its input to a Number before formatting.
 */

// ─── Helpers ────────────────────────────────────────────────────────────────

/**
 * Safely coerce a value to a finite number.
 * Returns 0 for null, undefined, NaN, or non-numeric strings.
 */
function toNumber(value) {
  if (value === null || value === undefined) return 0
  const n = typeof value === 'string' ? parseFloat(value) : Number(value)
  return Number.isFinite(n) ? n : 0
}

// ─── Currency Formatters ────────────────────────────────────────────────────

const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const usdFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/**
 * Format a value as Indian Rupees.
 * e.g. ₹1,23,456.78
 *
 * @param {string|number} value
 * @returns {string}
 */
export function formatINR(value) {
  return inrFormatter.format(toNumber(value))
}

/**
 * Format a value as US Dollars.
 * e.g. $1,234.56
 *
 * @param {string|number} value
 * @returns {string}
 */
export function formatUSD(value) {
  return usdFormatter.format(toNumber(value))
}

// ─── Number Formatters ──────────────────────────────────────────────────────

/**
 * Format a number with commas and fixed decimal places.
 *
 * @param {string|number} value
 * @param {number} [decimals=2]
 * @returns {string}
 */
export function formatNumber(value, decimals = 2) {
  const n = toNumber(value)
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

/**
 * Format an ARCX token amount with up to 6 decimal places.
 * Trailing zeros are trimmed for cleaner display.
 * e.g. 1,234.5 ARCX  or  0.000042 ARCX
 *
 * @param {string|number} value
 * @returns {string}
 */
export function formatArcx(value) {
  const n = toNumber(value)
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  }).format(n)
  return `${formatted} ARCX`
}

// ─── Date Formatters ────────────────────────────────────────────────────────

/**
 * Format a date string as "Jan 15, 2025".
 *
 * @param {string|Date} dateStr
 * @returns {string}
 */
export function formatDate(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

/**
 * Format a date string as "Jan 15, 2025, 2:30 PM".
 *
 * @param {string|Date} dateStr
 * @returns {string}
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(date)
}

// ─── Misc Formatters ────────────────────────────────────────────────────────

/**
 * Shorten a UUID to the first 8 characters followed by '...'
 * e.g. "a1b2c3d4..."
 *
 * @param {string} uuid
 * @returns {string}
 */
export function shortenUUID(uuid) {
  if (!uuid || typeof uuid !== 'string') return '—'
  return uuid.length > 8 ? `${uuid.slice(0, 8)}...` : uuid
}

/**
 * Format a numeric value as a percentage with a sign prefix.
 * e.g. "+2.45%" or "-1.23%"
 *
 * @param {string|number} value
 * @returns {string}
 */
export function formatPercent(value) {
  const n = toNumber(value)
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}%`
}
