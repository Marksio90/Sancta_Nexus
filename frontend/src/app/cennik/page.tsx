"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useBillingStore } from "@/stores/billing";

const MONTHLY_PRICE_ID = process.env.NEXT_PUBLIC_STRIPE_PRICE_MONTHLY ?? "";
const YEARLY_PRICE_ID = process.env.NEXT_PUBLIC_STRIPE_PRICE_YEARLY ?? "";

const FREE_FEATURES = [
  "📿 Różaniec — 20 tajemnic (bez AI)",
  "📖 Liturgia Godzin (Brewiarz)",
  "📓 Dziennik duchowy — 3 wpisy / miesiąc",
  "🕯️ Intencje modlitewne",
  "👥 Przeglądanie sesji wspólnotowych",
];

const PREMIUM_FEATURES = [
  "✨ AI medytacje do każdej tajemnicy różańca",
  "📿 Różaniec wspólnotowy na żywo (WebSocket)",
  "📓 Nieograniczony dziennik duchowy",
  "🔥 Ignacjański Rachunek Sumienia bez limitu",
  "📖 Lectio Divina z pełnym pipeline'em AI",
  "🙏 Asystent refleksji (Examen AI)",
  "📊 Historia i wgląd w postęp duchowy",
  "🔔 Powiadomienia push (Jutrznia, Anioł Pański…)",
];

export default function CennikPage() {
  const { subscription, loading, error, fetchStatus, startCheckout } = useBillingStore();
  const searchParams = useSearchParams();
  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const checkoutSuccess = searchParams.get("checkout") === "success";
  const checkoutCanceled = searchParams.get("checkout") === "canceled";

  const handleSubscribe = (priceId: string) => {
    if (!priceId) {
      alert("Płatności są w trakcie konfiguracji — spróbuj za chwilę.");
      return;
    }
    startCheckout(priceId);
  };

  const isPremium = subscription?.is_premium;

  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      <div className="max-w-3xl mx-auto px-4 py-12 pb-24">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="text-5xl mb-4">✝</div>
          <h1 className="text-3xl font-bold text-[#d4af37] mb-2">Wybierz swój plan</h1>
          <p className="text-gray-400 max-w-md mx-auto">
            Sancta Nexus to platforma modlitwy i formacji duchowej dla katolików.
            Darmowy plan zawsze pozostanie bezpłatny.
          </p>
        </div>

        {/* Banery po checkout */}
        {checkoutSuccess && (
          <div className="bg-green-900/30 border border-green-700/40 rounded-2xl p-4 mb-8 text-center">
            <div className="text-2xl mb-1">🙏</div>
            <p className="text-green-300 font-semibold">Dziękujemy! Twój plan Premium jest aktywny.</p>
          </div>
        )}
        {checkoutCanceled && (
          <div className="bg-yellow-900/20 border border-yellow-700/30 rounded-2xl p-4 mb-8 text-center">
            <p className="text-yellow-300 text-sm">Płatność anulowana — możesz spróbować ponownie.</p>
          </div>
        )}
        {error && (
          <div className="bg-red-900/30 border border-red-700/40 rounded-xl p-3 mb-6 text-sm text-red-300 text-center">
            {error}
          </div>
        )}

        {/* Przełącznik miesięczny/roczny */}
        <div className="flex justify-center mb-8">
          <div className="bg-white/5 rounded-xl p-1 flex gap-1">
            <button
              onClick={() => setBilling("monthly")}
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
                billing === "monthly"
                  ? "bg-[#d4af37] text-black"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Miesięczny
            </button>
            <button
              onClick={() => setBilling("yearly")}
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
                billing === "yearly"
                  ? "bg-[#d4af37] text-black"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Roczny
              <span className="ml-2 text-xs bg-green-700 text-green-100 px-1.5 py-0.5 rounded-full">
                −37%
              </span>
            </button>
          </div>
        </div>

        {/* Karty planów */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* FREE */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 flex flex-col">
            <div className="mb-4">
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Bezpłatny</div>
              <div className="text-4xl font-bold text-white">0 zł</div>
              <div className="text-xs text-gray-500 mt-1">na zawsze</div>
            </div>
            <ul className="space-y-2 flex-1 mb-6">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-gray-500 mt-0.5">✓</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            {isPremium ? (
              <div className="w-full text-center text-sm text-gray-500 py-3 border border-white/10 rounded-xl">
                Twój aktualny plan: Premium
              </div>
            ) : (
              <div className="w-full text-center text-sm text-[#d4af37] py-3 border border-[#d4af37]/30 rounded-xl font-medium">
                ✓ Aktywny
              </div>
            )}
          </div>

          {/* PREMIUM */}
          <div className="rounded-2xl border border-[#d4af37]/50 bg-gradient-to-b from-[#d4af37]/10 to-[#d4af37]/5 p-6 flex flex-col relative overflow-hidden">
            <div className="absolute top-4 right-4">
              <span className="text-xs bg-[#d4af37] text-black font-bold px-2 py-1 rounded-full">
                POLECANY
              </span>
            </div>
            <div className="mb-4">
              <div className="text-xs text-[#d4af37] uppercase tracking-wider mb-1">
                {billing === "monthly" ? "Pielgrzym" : "Uczeń"}
              </div>
              <div className="text-4xl font-bold text-white">
                {billing === "monthly" ? "39 zł" : "299 zł"}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {billing === "monthly" ? "/ miesiąc" : "/ rok (25 zł/mies.)"}
              </div>
            </div>
            <ul className="space-y-2 flex-1 mb-6">
              {PREMIUM_FEATURES.map((f) => (
                <li key={f} className="text-sm text-gray-200 flex items-start gap-2">
                  <span className="text-[#d4af37] mt-0.5">✓</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>

            {isPremium ? (
              <div className="space-y-2">
                <div className="w-full text-center text-sm text-[#d4af37] py-3 border border-[#d4af37]/30 rounded-xl font-medium">
                  ✓ Plan aktywny — {subscription?.tier}
                </div>
                <button
                  onClick={() => useBillingStore.getState().openPortal()}
                  disabled={loading}
                  className="w-full text-sm text-gray-400 hover:text-white py-2 transition-colors"
                >
                  Zarządzaj subskrypcją →
                </button>
              </div>
            ) : (
              <button
                onClick={() =>
                  handleSubscribe(
                    billing === "monthly" ? MONTHLY_PRICE_ID : YEARLY_PRICE_ID
                  )
                }
                disabled={loading}
                className="w-full bg-[#d4af37] text-black font-semibold py-3 rounded-xl hover:bg-[#c9a227] transition-colors disabled:opacity-60"
              >
                {loading ? "Ładowanie…" : "Rozpocznij Premium →"}
              </button>
            )}
          </div>
        </div>

        {/* Gwarancja */}
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-600">
            Płatność przez Stripe · Anuluj w dowolnym momencie · 14-dniowy zwrot bez pytań
          </p>
          <p className="text-xs text-gray-700 mt-1">
            Sancta Nexus nie zastępuje kapłana, spowiednika ani kierownika duchowego.
          </p>
        </div>
      </div>
    </main>
  );
}
