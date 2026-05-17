"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useBillingStore } from "@/stores/billing";

const MONTHLY_PRICE_ID = process.env.NEXT_PUBLIC_STRIPE_PRICE_MONTHLY ?? "";
const YEARLY_PRICE_ID = process.env.NEXT_PUBLIC_STRIPE_PRICE_YEARLY ?? "";

const FREE_FEATURES = [
  { text: "Różaniec — 20 tajemnic (bez AI)", icon: "📿" },
  { text: "Liturgia Godzin — Brewiarz", icon: "📖" },
  { text: "Dziennik duchowy — 3 wpisy / miesiąc", icon: "📓" },
  { text: "Intencje modlitewne — bez limitu", icon: "🕯" },
  { text: "Przeglądanie sesji wspólnotowych", icon: "👥" },
  { text: "Dostęp do Nowenn (bez śledzenia)", icon: "✦" },
];

const PREMIUM_FEATURES = [
  { text: "Lectio Divina — pełny pipeline AI", icon: "📖" },
  { text: "Medytacje AI do każdej tajemnicy różańca", icon: "📿" },
  { text: "Różaniec wspólnotowy na żywo", icon: "👥" },
  { text: "Nieograniczony dziennik duchowy", icon: "📓" },
  { text: "Ignacjański Rachunek Sumienia (Examen)", icon: "🔥" },
  { text: "Asystent refleksji duchowej (AI chat)", icon: "🙏" },
  { text: "Historia i wgląd w postęp duchowy", icon: "📊" },
  { text: "Śledzenie postępu Nowenn — 9 dni", icon: "✦" },
  { text: "Powiadomienia push (Jutrznia, Anioł Pański)", icon: "🔔" },
  { text: "Głosowe wprowadzanie modlitw (Whisper AI)", icon: "🎙" },
];

function CheckoutBanners() {
  const searchParams = useSearchParams();
  const checkoutSuccess = searchParams.get("checkout") === "success";
  const checkoutCanceled = searchParams.get("checkout") === "canceled";
  if (!checkoutSuccess && !checkoutCanceled) return null;
  return (
    <>
      {checkoutSuccess && (
        <div className="bg-emerald-950/50 border border-emerald-700/40 rounded-2xl p-5 mb-8 text-center">
          <div className="text-3xl mb-2">🙏</div>
          <p className="text-emerald-300 font-semibold">Dziękujemy! Twój plan Premium jest aktywny.</p>
          <p className="text-xs text-gray-500 mt-1">Wszystkie funkcje zostały odblokowane.</p>
        </div>
      )}
      {checkoutCanceled && (
        <div className="bg-yellow-950/30 border border-yellow-800/30 rounded-2xl p-4 mb-8 text-center">
          <p className="text-yellow-300 text-sm">Płatność anulowana — możesz spróbować ponownie.</p>
        </div>
      )}
    </>
  );
}

export default function CennikPage() {
  const { subscription, loading, error, fetchStatus, startCheckout } = useBillingStore();
  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleSubscribe = (priceId: string) => {
    startCheckout(priceId);
  };

  const isPremium = subscription?.is_premium;

  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      {/* Hero */}
      <div className="relative bg-gradient-to-b from-[#1a1200]/80 to-[#0d0b1a] pt-10 pb-8 px-4 text-center border-b border-[#d4af37]/10">
        <div className="text-3xl text-[#d4af37]/60 mb-3">✝</div>
        <h1 className="text-2xl font-bold text-white mb-1">Wybierz swoją drogę formacji</h1>
        <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
          Darmowy plan pozostaje bezpłatny na zawsze.
          Premium odblokuje pełne towarzyszenie AI.
        </p>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8 pb-24">
        {/* Banery po checkout */}
        <Suspense>
          <CheckoutBanners />
        </Suspense>

        {error && (
          <div className="bg-red-950/40 border border-red-800/40 rounded-xl p-3 mb-6 text-sm text-red-300 text-center">
            {error}
          </div>
        )}

        {/* Konfigurator: miesięcznie / rocznie */}
        <div className="flex justify-center mb-8">
          <div className="bg-white/5 border border-white/8 rounded-xl p-1 flex gap-1">
            <button
              onClick={() => setBilling("monthly")}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${
                billing === "monthly"
                  ? "bg-[#d4af37] text-black"
                  : "text-gray-500 hover:text-white"
              }`}
            >
              Miesięcznie
            </button>
            <button
              onClick={() => setBilling("yearly")}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all relative ${
                billing === "yearly"
                  ? "bg-[#d4af37] text-black"
                  : "text-gray-500 hover:text-white"
              }`}
            >
              Rocznie
              <span className={`ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                billing === "yearly" ? "bg-black/20 text-black" : "bg-emerald-800 text-emerald-100"
              }`}>
                −37%
              </span>
            </button>
          </div>
        </div>

        {/* Karty planów */}
        <div className="grid md:grid-cols-2 gap-4">
          {/* FREE — Pielgrzym */}
          <div className="rounded-2xl border border-white/8 bg-white/3 p-6 flex flex-col">
            <div className="mb-5">
              <div className="text-[10px] text-gray-600 uppercase tracking-[0.2em] mb-2">Pielgrzym</div>
              <div className="text-4xl font-bold text-white">0 zł</div>
              <div className="text-xs text-gray-600 mt-1">bezpłatnie · na zawsze</div>
            </div>
            <ul className="space-y-2.5 flex-1 mb-6">
              {FREE_FEATURES.map((f) => (
                <li key={f.text} className="text-sm text-gray-400 flex items-start gap-2.5">
                  <span className="text-gray-600 mt-px flex-shrink-0 w-4 text-center">{f.icon}</span>
                  <span>{f.text}</span>
                </li>
              ))}
            </ul>
            {isPremium ? (
              <div className="w-full text-center text-xs text-gray-600 py-2.5 border border-white/8 rounded-xl">
                Twój plan: Premium
              </div>
            ) : (
              <div className="w-full text-center text-xs text-[#d4af37]/80 py-2.5 border border-[#d4af37]/20 rounded-xl font-medium">
                ✓ Plan aktywny
              </div>
            )}
          </div>

          {/* PREMIUM — Uczeń / Oblat */}
          <div className="rounded-2xl border border-[#d4af37]/40 bg-gradient-to-b from-[#d4af37]/8 to-[#d4af37]/3 p-6 flex flex-col relative overflow-hidden">
            <div className="absolute top-0 right-0 w-40 h-40 bg-[#d4af37]/5 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute top-4 right-4">
              <span className="text-[9px] tracking-[0.15em] bg-[#d4af37] text-black font-bold px-2 py-1 rounded-full uppercase">
                Polecany
              </span>
            </div>
            <div className="mb-5 relative">
              <div className="text-[10px] text-[#d4af37]/80 uppercase tracking-[0.2em] mb-2">
                {billing === "monthly" ? "Uczeń" : "Oblat"}
              </div>
              <div className="flex items-end gap-2">
                <div className="text-4xl font-bold text-white">
                  {billing === "monthly" ? "39" : "299"}
                </div>
                <div className="text-lg text-gray-400 mb-1">zł</div>
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {billing === "monthly" ? "miesięcznie" : "rocznie · (ok. 25 zł / mies.)"}
              </div>
            </div>
            <ul className="space-y-2.5 flex-1 mb-6 relative">
              {PREMIUM_FEATURES.map((f) => (
                <li key={f.text} className="text-sm text-gray-200 flex items-start gap-2.5">
                  <span className="text-[#d4af37]/70 mt-px flex-shrink-0 w-4 text-center">{f.icon}</span>
                  <span>{f.text}</span>
                </li>
              ))}
            </ul>

            <div className="relative">
              {isPremium ? (
                <div className="space-y-2">
                  <div className="w-full text-center text-sm text-[#d4af37] py-3 border border-[#d4af37]/30 rounded-xl font-medium">
                    ✓ Plan aktywny
                  </div>
                  <button
                    onClick={() => useBillingStore.getState().openPortal()}
                    disabled={loading}
                    className="w-full text-xs text-gray-500 hover:text-white py-2 transition-colors"
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
                  className="w-full bg-[#d4af37] text-black font-semibold py-3.5 rounded-xl hover:bg-[#c9a227] transition-colors disabled:opacity-60 text-sm"
                >
                  {loading ? "Ładowanie…" : "Rozpocznij Premium →"}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Wspólnota / Parafia — coming soon */}
        <div className="mt-6 rounded-2xl border border-[#d4af37]/25 bg-[#d4af37]/3 p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] uppercase tracking-[0.2em] text-[#d4af37]/60 font-semibold">
                Wspólnota / Parafia
              </span>
              <span className="text-[9px] font-bold bg-[#d4af37]/15 text-[#d4af37]/80 border border-[#d4af37]/30 px-2 py-0.5 rounded-full uppercase tracking-wider">
                Wkrótce
              </span>
            </div>
            <p className="text-sm text-gray-400 leading-relaxed">
              Plan grupowy dla wspólnot, parafii i grup modlitewnych — wspólna formacja, intencje grupy, admin parafii.
            </p>
          </div>
          <div className="shrink-0 text-2xl text-[#d4af37]/20 select-none">👥</div>
        </div>

        {/* Gwarancja i disclaimer */}
        <div className="mt-8 text-center space-y-2">
          <p className="text-xs text-gray-700">
            Płatność przez Stripe · Anuluj w dowolnym momencie · 14 dni na zwrot bez pytań
          </p>
          <p className="text-xs text-gray-700 italic">
            Sancta Nexus nie zastępuje kapłana, spowiednika ani kierownika duchowego.
          </p>
        </div>
      </div>
    </main>
  );
}
