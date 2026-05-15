"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useBillingStore } from "@/stores/billing";

interface PremiumGateProps {
  children: React.ReactNode;
  feature?: string;
  fallback?: React.ReactNode;
}

/**
 * Opakowuje premium-only treści.
 * - Zalogowani użytkownicy premium → pokazuje children
 * - Free → pokazuje baner z linkiem do cennika (lub własny fallback)
 */
export function PremiumGate({ children, feature, fallback }: PremiumGateProps) {
  const { subscription, fetchStatus } = useBillingStore();

  useEffect(() => {
    if (!subscription) fetchStatus();
  }, [subscription, fetchStatus]);

  if (subscription?.is_premium) return <>{children}</>;

  if (fallback) return <>{fallback}</>;

  return (
    <div className="rounded-2xl border border-[#d4af37]/30 bg-[#d4af37]/5 p-6 text-center">
      <div className="text-3xl mb-3">✨</div>
      <h3 className="font-semibold text-[#d4af37] mb-1">
        {feature ? `${feature} — plan Premium` : "Funkcja Premium"}
      </h3>
      <p className="text-sm text-gray-400 mb-4">
        Odblokuj pełne doświadczenie duchowe — medytacje AI, nieograniczony dziennik,
        Różaniec wspólnotowy i wiele więcej.
      </p>
      <Link
        href="/cennik"
        className="inline-block bg-[#d4af37] text-black font-semibold px-6 py-2.5 rounded-xl hover:bg-[#c9a227] transition-colors text-sm"
      >
        Zobacz plany →
      </Link>
    </div>
  );
}
