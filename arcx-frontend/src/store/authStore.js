/**
 * ARCX Auth Store — src/store/authStore.js
 *
 * Zustand store for authentication state.
 * Tokens live in localStorage for persistence across refreshes.
 * User profile lives in store memory.
 */

import { create } from 'zustand'
import { authApi } from '../api/index'

export const useAuthStore = create((set, get) => ({
  user:          null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  loading:       false,
  error:         null,

  // ── Actions ──────────────────────────────────────────────────────────

  register: async (formData) => {
    set({ loading: true, error: null })
    try {
      const data = await authApi.register(formData)
      const { access_token, refresh_token, ...user } = data
      localStorage.setItem('access_token',  access_token)
      localStorage.setItem('refresh_token', refresh_token)
      set({ user, isAuthenticated: true, loading: false })
      return { success: true }
    } catch (err) {
      const msg = err.error || 'Registration failed.'
      set({ loading: false, error: msg })
      return { success: false, error: msg }
    }
  },

  login: async ({ email, password }) => {
    set({ loading: true, error: null })
    try {
      const data = await authApi.login(email, password)
      set({ isAuthenticated: true, loading: false })
      await get().fetchMe()
      return { success: true }
    } catch (err) {
      const msg = err.detail || 'Invalid email or password.'
      set({ loading: false, error: msg })
      return { success: false, error: msg }
    }
  },

  logout: async () => {
    try {
      authApi.logout()
    } catch (_) { }
    set({ user: null, isAuthenticated: false, error: null })
  },

  fetchMe: async () => {
    try {
      const data = await authApi.getMe()
      set({ user: data })
    } catch (_) {}
  },

  clearError: () => set({ error: null }),
}))