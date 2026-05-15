"use client";

import { create } from "zustand";
import { api } from "@/lib/api";

export interface SubscriptionStatus {
  tier: "free" | "pilgrim" | "disciple" | "mystic";
  status: string;
  cancel_at_period_end: boolean;
  current_period_end: string | null;
  is_premium: boolean;
}

interface BillingState {
  subscription: SubscriptionStatus | null;
  loading: boolean;
  error: string | null;
}

interface BillingActions {
  fetchStatus: () => Promise<void>;
  startCheckout: (priceId: string) => Promise<void>;
  openPortal: () => Promise<void>;
}

const DEFAULT_STATUS: SubscriptionStatus = {
  tier: "free",
  status: "free",
  cancel_at_period_end: false,
  current_period_end: null,
  is_premium: false,
};

export const useBillingStore = create<BillingState & BillingActions>((set) => ({
  subscription: null,
  loading: false,
  error: null,

  fetchStatus: async () => {
    set({ loading: true, error: null });
    try {
      const data = await api.get<SubscriptionStatus>("/api/v1/billing/status");
      set({ subscription: data, loading: false });
    } catch {
      set({ subscription: DEFAULT_STATUS, loading: false });
    }
  },

  startCheckout: async (priceId: string) => {
    set({ loading: true, error: null });
    try {
      const data = await api.post<{ checkout_url: string }>("/api/v1/billing/checkout", {
        price_id: priceId,
      });
      window.location.href = data.checkout_url;
    } catch (e: any) {
      set({ error: e?.message ?? "Błąd inicjowania płatności.", loading: false });
    }
  },

  openPortal: async () => {
    set({ loading: true, error: null });
    try {
      const data = await api.post<{ portal_url: string }>("/api/v1/billing/portal", {});
      window.location.href = data.portal_url;
    } catch (e: any) {
      set({ error: e?.message ?? "Błąd otwierania portalu.", loading: false });
    }
  },
}));
