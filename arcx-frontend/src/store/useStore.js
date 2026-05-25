import { create } from 'zustand';
import * as authAPI from '../api/auth';
import * as walletAPI from '../api/wallet';
import * as oracleAPI from '../api/oracle';
import * as kycAPI from '../api/kyc';
import { getAccessToken, setTokens, clearTokens, isTokenExpired, getUserFromToken } from '../utils/auth';

const useStore = create((set, get) => ({
  // ── Auth Slice ──
  user: null,
  isAuthenticated: !!getAccessToken() && !isTokenExpired(getAccessToken()),
  authLoading: false,
  authError: null,

  login: async (username, password) => {
    set({ authLoading: true, authError: null });
    try {
      const data = await authAPI.login(username, password);
      setTokens(data.access, data.refresh);
      const user = getUserFromToken(data.access);
      set({ isAuthenticated: true, user, authLoading: false });
      return data;
    } catch (error) {
      const msg = error.response?.data?.detail || error.response?.data?.error || 'Login failed';
      set({ authError: msg, authLoading: false });
      throw error;
    }
  },

  logout: () => {
    clearTokens();
    set({
      user: null,
      isAuthenticated: false,
      wallet: null,
      transactions: [],
      kycStatus: null,
    });
  },

  // ── Wallet Slice ──
  wallet: null,
  walletLoading: false,
  walletError: null,

  fetchWallet: async () => {
    set({ walletLoading: true, walletError: null });
    try {
      const data = await walletAPI.getBalance();
      set({ wallet: data, walletLoading: false });
    } catch (error) {
      set({ walletError: error.response?.data?.error || 'Failed to load wallet', walletLoading: false });
    }
  },

  deposit: async (amount_inr) => {
    try {
      const data = await walletAPI.deposit(amount_inr);
      // Refresh wallet balance after deposit
      get().fetchWallet();
      return data;
    } catch (error) {
      throw error;
    }
  },

  withdraw: async (amount_arcx) => {
    try {
      const data = await walletAPI.withdraw(amount_arcx);
      get().fetchWallet();
      return data;
    } catch (error) {
      throw error;
    }
  },

  // ── Transaction Slice ──
  transactions: [],
  txLoading: false,

  fetchTransactions: async (limit = 20) => {
    set({ txLoading: true });
    try {
      const data = await walletAPI.getHistory(limit);
      set({ transactions: data.transactions || [], txLoading: false });
    } catch (error) {
      set({ txLoading: false });
    }
  },

  // ── Oracle / NAV Slice ──
  livePrice: null,
  navHistory: [],
  todayNAV: null,
  priceLoading: false,

  fetchLivePrice: async () => {
    try {
      const data = await oracleAPI.getLivePrice();
      set({ livePrice: data });
    } catch (error) {
      console.error('Failed to fetch live price:', error);
    }
  },

  fetchNAVHistory: async (days = 30) => {
    set({ priceLoading: true });
    try {
      const data = await oracleAPI.getNAVHistory(days);
      set({ navHistory: data.history || [], priceLoading: false });
    } catch (error) {
      set({ priceLoading: false });
    }
  },

  fetchTodayNAV: async () => {
    try {
      const data = await oracleAPI.getTodayNAV();
      set({ todayNAV: data });
    } catch (error) {
      console.error('Failed to fetch today NAV:', error);
    }
  },

  // ── KYC Slice ──
  kycStatus: null,
  kycLoading: false,

  fetchKYCStatus: async () => {
    set({ kycLoading: true });
    try {
      const data = await kycAPI.getKYCStatus();
      set({ kycStatus: data, kycLoading: false });
    } catch (error) {
      set({ kycLoading: false });
    }
  },

  submitKYC: async (kycData) => {
    try {
      const data = await kycAPI.submitKYC(kycData);
      get().fetchKYCStatus();
      return data;
    } catch (error) {
      throw error;
    }
  },
}));

export default useStore;
