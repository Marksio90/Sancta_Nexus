"use client";

/**
 * NovenaDetailClient — interactive day tracker for individual novena pages.
 *
 * Fetches novena data from the backend and renders:
 *  - Daily intention and prayer text
 *  - Progress indicator (9 days)
 *  - Start/continue tracking CTA (requires auth)
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

interface NovenaFull {
  id: string;
  title: string;
  patron: string;
  patron_icon: string;
  description: string;
  days: number;
  scripture: string;
  ccc: string;
  origin: string;
  daily_intentions: string[];
  daily_prayer?: string;
}

interface DayContent {
  title: string;
  prayer: string;
}

export function NovenaDetailClient({ novenaId }: { novenaId: string }) {
  const [novena, setNovena] = useState<NovenaFull | null>(null);
  const [selectedDay, setSelectedDay] = useState(1);
  const [dayContent, setDayContent] = useState<DayContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    api
      .get<NovenaFull>(`/api/v1/community/novenas/${novenaId}`)
      .then(setNovena)
      .catch(() => null)
      .finally(() => setLoading(false));
  }, [novenaId]);

  useEffect(() => {
    if (!novena) return;
    api
      .get<DayContent>(`/api/v1/community/novenas/${novenaId}/day/${selectedDay}`)
      .then(setDayContent)
      .catch(() => null);
  }, [novena, novenaId, selectedDay]);

  const handleStart = async () => {
    if (!isAuthenticated) return;
    setStarting(true);
    try {
      await api.post(`/api/v1/community/novenas/${novenaId}/start`, {});
    } catch {
      // Already started or error — user can still track via /nowenna page
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#d4af37]/30 border-t-[#d4af37]" />
      </div>
    );
  }

  if (!novena) {
    return (
      <div className="text-center py-10">
        <p className="text-gray-500 text-sm">
          Nie można załadować treści nowenny.{" "}
          <Link href="/nowenna" className="text-[#d4af37] hover:underline">
            Wróć do biblioteki
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Day selector */}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-3 font-medium">
          Wybierz dzień nowenny
        </p>
        <div className="flex gap-2 flex-wrap">
          {Array.from({ length: novena.days }, (_, i) => i + 1).map((day) => (
            <button
              key={day}
              onClick={() => setSelectedDay(day)}
              className={`h-9 w-9 rounded-full text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-[#d4af37] ${
                selectedDay === day
                  ? "bg-[#d4af37] text-black"
                  : "border border-white/10 text-gray-400 hover:border-[#d4af37]/30 hover:text-[#d4af37]"
              }`}
            >
              {day}
            </button>
          ))}
        </div>
      </div>

      {/* Day intention */}
      {novena.daily_intentions[selectedDay - 1] && (
        <div className="rounded-2xl border border-[#d4af37]/20 bg-[#d4af37]/5 px-6 py-5">
          <p className="text-xs text-[#d4af37] uppercase tracking-wider mb-2 font-medium">
            Intencja dnia {selectedDay}
          </p>
          <p className="text-sacred-text font-medium leading-relaxed">
            {novena.daily_intentions[selectedDay - 1]}
          </p>
        </div>
      )}

      {/* Prayer text */}
      {dayContent?.prayer && (
        <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-5">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-3 font-medium">
            Modlitwa
          </p>
          <p className="text-gray-200 text-sm leading-relaxed italic">
            {dayContent.prayer}
          </p>
        </div>
      )}

      {/* Daily prayer from novena definition */}
      {!dayContent?.prayer && novena.daily_prayer && (
        <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-5">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-3 font-medium">
            Modlitwa nowennowa
          </p>
          <p className="text-gray-200 text-sm leading-relaxed italic">
            {novena.daily_prayer}
          </p>
        </div>
      )}

      {/* Metadata */}
      <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-4 flex flex-wrap gap-4 text-sm">
        {novena.origin && (
          <div>
            <p className="text-xs text-gray-600 mb-0.5">Pochodzenie</p>
            <p className="text-gray-400">{novena.origin}</p>
          </div>
        )}
        {novena.ccc && (
          <div>
            <p className="text-xs text-gray-600 mb-0.5">Katechizm</p>
            <p className="text-gray-400">{novena.ccc}</p>
          </div>
        )}
      </div>

      {/* CTA */}
      <div className="flex flex-col sm:flex-row gap-3">
        {isAuthenticated ? (
          <button
            onClick={handleStart}
            disabled={starting}
            className="flex-1 rounded-xl bg-[#d4af37] px-6 py-4 font-semibold text-black hover:bg-[#c9a227] disabled:opacity-40 transition-colors focus:outline-none focus:ring-2 focus:ring-[#d4af37]"
          >
            {starting ? "Zapisuję…" : "Zacznij śledzić nowennę"}
          </button>
        ) : (
          <Link
            href="/auth/login"
            className="flex-1 rounded-xl bg-[#d4af37] px-6 py-4 font-semibold text-black hover:bg-[#c9a227] transition-colors text-center"
          >
            Zaloguj się, by śledzić postęp
          </Link>
        )}
        <Link
          href="/nowenna"
          className="rounded-xl border border-white/10 px-6 py-4 text-sm text-gray-400 hover:border-white/20 hover:text-gray-200 transition-colors text-center"
        >
          Wszystkie nowenny
        </Link>
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-gray-600 italic text-center">
        Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy.
        Nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty.
      </p>
    </div>
  );
}
