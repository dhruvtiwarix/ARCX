/**
 * ARCX Auth / Token Utilities
 *
 * Manages JWT access & refresh tokens in localStorage.
 * Provides helpers to decode, check expiry, and extract user info.
 */

const TOKEN_KEY = 'arcx_access_token'
const REFRESH_KEY = 'arcx_refresh_token'

// ─── Token Storage ──────────────────────────────────────────────────────────

/**
 * Retrieve the stored access token.
 * @returns {string|null}
 */
export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * Retrieve the stored refresh token.
 * @returns {string|null}
 */
export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

/**
 * Persist both access and refresh tokens.
 * @param {string} access  — JWT access token
 * @param {string} refresh — JWT refresh token
 */
export function setTokens(access, refresh) {
  localStorage.setItem(TOKEN_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

/**
 * Remove both tokens from storage (logout).
 */
export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

// ─── JWT Decoding ───────────────────────────────────────────────────────────

/**
 * Decode the payload segment of a JWT.
 * Returns the parsed JSON object, or null on failure.
 *
 * @param {string} token — A valid JWT string (header.payload.signature)
 * @returns {object|null}
 */
function decodeJWTPayload(token) {
  try {
    if (!token || typeof token !== 'string') return null

    const parts = token.split('.')
    if (parts.length !== 3) return null

    // Base64url → Base64
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')

    // Pad to a multiple of 4
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      '='
    )

    const jsonStr = atob(padded)

    // Handle multi-byte UTF-8 characters
    const decoded = decodeURIComponent(
      Array.from(jsonStr)
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )

    return JSON.parse(decoded)
  } catch {
    return null
  }
}

// ─── Token Inspection ───────────────────────────────────────────────────────

/**
 * Check whether a JWT has expired.
 * Returns true if the token is expired, malformed, or missing.
 *
 * @param {string} token
 * @returns {boolean}
 */
export function isTokenExpired(token) {
  const payload = decodeJWTPayload(token)
  if (!payload || typeof payload.exp !== 'number') return true
  // exp is in seconds; compare against current time in seconds
  return payload.exp < Math.floor(Date.now() / 1000)
}

/**
 * Extract user information from a JWT.
 * The `sub` claim is mapped to `user_id` for convenience.
 *
 * @param {string} token
 * @returns {{ user_id: string, [key: string]: any } | null}
 */
export function getUserFromToken(token) {
  const payload = decodeJWTPayload(token)
  if (!payload) return null

  return {
    ...payload,
    user_id: payload.sub ?? null,
  }
}
