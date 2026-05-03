import { create } from "zustand";
import { api } from "../lib/api";

export const useAuthStore = create((set, get) => ({
  user: null,
  companies: [],
  activeCompanyId: null,
  activeRole: null,
  loading: true,

  setSession: (data) =>
    set({
      user: data.user || null,
      companies: data.companies || [],
      activeCompanyId: data.active_company_id || null,
      activeRole: data.active_role || null,
      loading: false,
    }),

  refreshMe: async () => {
    try {
      const { data } = await api.get("/auth/me");
      set({
        user: data.user,
        companies: data.companies,
        activeCompanyId: data.active_company_id,
        activeRole: data.active_role,
        loading: false,
      });
      return data;
    } catch (e) {
      set({ user: null, companies: [], activeCompanyId: null, activeRole: null, loading: false });
      return null;
    }
  },

  login: async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    set({
      user: data.user,
      companies: data.companies,
      activeCompanyId: data.active_company_id,
      activeRole: data.active_role,
      loading: false,
    });
    return data;
  },

  logout: async () => {
    try {
      await api.post("/auth/logout");
    } catch (e) {
      console.error("Logout request failed:", e?.message || e);
    }
    set({ user: null, companies: [], activeCompanyId: null, activeRole: null });
  },

  switchCompany: async (companyId) => {
    const { data } = await api.post("/auth/switch-company", { company_id: companyId });
    set({ activeCompanyId: data.active_company_id, activeRole: data.active_role });
    return data;
  },

  activeCompany: () => {
    const s = get();
    return s.companies.find((c) => c.id === s.activeCompanyId);
  },
}));
