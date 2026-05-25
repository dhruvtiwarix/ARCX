import client from './client';
import { setTokens, clearTokens } from '../utils/auth';

/**
 * Authenticate user and persist JWT pair.
 * @param {string} username
 * @param {string} password
 * @returns {Promise<{access: string, refresh: string}>}
 */
export async function login(username, password) {
  try {
    const { data } = await client.post('/api/auth/token/', { username, password });
    setTokens(data.access, data.refresh);
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

/**
 * Register a new user account.
 * @param {{email: string, full_name: string, phone: string, password: string}} payload
 * @returns {Promise<object>}
 */
export async function register(payload) {
  try {
    const { data } = await client.post('/api/v1/auth/register', {
      email: payload.email,
      full_name: payload.full_name,
      phone: payload.phone,
      password: payload.password,
    });
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

/**
 * Fetch the authenticated user's profile.
 * @returns {Promise<object>}
 */
export async function getMe() {
  try {
    const { data } = await client.get('/api/v1/auth/me');
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

/**
 * Log out by clearing persisted tokens.
 * The backend JWT logout endpoint is a no-op; token invalidation
 * is handled client-side by discarding the pair.
 */
export function logout() {
  clearTokens();
}
