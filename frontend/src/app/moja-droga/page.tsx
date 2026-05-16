"use client";

/**
 * Moja Droga — longitudinal spiritual journey visualization.
 *
 * Renders:
 *  1. Three-stage Ignatian path (Purgativa → Illuminativa → Unitiva)
 *     with animated progress bars and milestone markers.
 *  2. Prayer streak calendar (GitHub-style heatmap, last 12 weeks).
 *  3. Session frequency bar chart (last 8 weeks, CSS-only).
 *  4. Top spiritual themes from session history.
 *
 * Data comes from useProgressStore (backend-synced, localStorage fallback).
 */

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useProgressStore, SessionRecord } from "@/stores/progress";
import { useAuthStore } from "@/stores/auth";

// ── Journey stages ──────────────────────────────────────────────────────────

const STAGES = [
  {
    key: "purgativa" as const,
    name: "Via Purgativa",
    namePl: "Oczyszczenie",
    description: "Odwracanie się od grzechu, oczyszczenie serca i woli.",
    scripture: '„Stwórz we mnie serce czyste, Boże." — Ps 51,12',
    milestones: [
      { sessions: 1, label: "Pierwsze spotkanie ze Słowem" },
      { sessions: 5, label: "Regularność modlitwy" },
      { sessions: 10, label: "Nawyk lectio" },
      { sessions: 20, label: "Wejście na drogę oświecenia" },
    ],
  },
  {
    key: "illuminativa" as const,
    name: "Via Illuminativa",
    namePl: "Oświecenie",
    description: "Wzrost w cnocie, kontemplacja prawd wiary, głębsza miłość.",
    scripture: '„Słowo Twoje jest lampą dla moich stóp." — Ps 119,105',
    milestones: [
      { sessions: 20, label: "Początek oświecenia" },
      { sessions: 30, label: "Modlitwa myślna" },
      { sessions: 35, label: "Rozpoznawanie natchnień" },
      { sessions: 40, label: "Gotowość do zjednoczenia" },
    ],
  },
  {
    key: "unitiva" as const,
    name: "Via Unitiva",
    namePl: "Zjednoczenie",
    description: "Zjednoczenie woli z Wolą Bożą, trwała kontemplacja.",
    scripture: '„Trwajcie we Mnie, a Ja w was trwać będę." — J 15,4',
    milestones: [
      { sessions: 40, label: "Pierwsze chwile zjednoczenia" },
      { sessions: 50, label: "Wytrwałość w kontemplacji" },
      { sessions: 60, label: "Owoc dzienny" },
      { sessions: 80, label: "Duchowa dojrzałość" },
    ],
  },
] as const;

// ── Heatmap helper ─────────────────────────────────────────────────────────

function buildHeatmap(sessions: SessionRecord[]): Map<string, number> {
  const map = new Map<string, number>();
  for (const s of sessions) {
    const d = s.date.slice(0, 10);
    map.set(d, (map.get(d) ?? 0) + 1);
  }
  return map;
}

function getLast12Weeks(): string[][] {
  const weeks: string[][] = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dayOfWeek = today.getDay(); // 0=Sun
  const sunday = new Date(today);
  sunday.setDate(today.getDate() - dayOfWeek);

  for (let w = 11; w >= 0; w--) {
    const week: string[] = [];
    for (let d = 0; d < 7; d++) {
      const date = new Date(sunday);
      date.setDate(sunday.getDate() - w * 7 + d);
      week.push(date.toISOString().slice(0, 10));
    }
    weeks.push(week);
  }
  return weeks;
}

function intensityClass(count: number): string {
  if (count === 0) return "bg-white/5";
  if (count === 1) return "bg-amber-500/30";
  if (count === 2) return "bg-amber-500/60";
  return "bg-amber-500";
}

// ── Weekly bar chart helper ────────────────────────────────────────────────

function buildWeeklyBars(sessions: SessionRecord[]): number[] {
  const counts = Array(8).fill(0) as number[];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (const s of sessions) {
    const d = new Date(s.date);
    d.setHours(0, 0, 0, 0);
    const diffDays = Math.floor((today.getTime() - d.getTime()) / 86400000);
    const weekIdx = Math.floor(diffDays / 7);
    if (weekIdx < 8) {
      counts[7 - weekIdx]++;
    }
  }
  return counts;
}

// ── Component ──────────────────────────────────────────────────────────────

export default function MojaDrogaPage() {
  const {
    loadFromBackend,
    loadFromStorage,
    totalSessions,
    sessions,
    themes,
    journeyProgress,
    isBackendSynced,
  } = useProgressStore();

  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      loadFromBackend();
    } else {
      loadFromStorage();
    }
  }, [isAuthenticated, loadFromBackend, loadFromStorage]);

  const heatmap = useMemo(() => buildHeatmap(sessions), [sessions]);
  const weeks = useMemo(() => getLast12Weeks(), []);
  const weeklyBars = useMemo(() => buildWeeklyBars(sessions), [sessions]);
  const maxBar = Math.max(...weeklyBars, 1);

  // Determine active stage
  const activeStageKey =
    journeyProgress.unitiva > 0
      ? "unitiva"
      : journeyProgress.illuminativa > 0
      ? "illuminativa"
      : "purgativa";

  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto max-w-3xl">
        {/* Back link */}
        <Link
          href="/dashboard"
          className="mb-8 inline-flex items-center gap-2 text-sm text-gray-400 hover:text-amber-400 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Panel duchowy
        </Link>

        {/* Header */}
        <div className="mb-10">
          <h1 className="font-cinzel text-4xl font-bold text-sacred-text mb-2">
            Moja Droga
          </h1>
          <p className="text-gray-400 text-sm">
            Twoja duchowa podróż według tradycji ignacjańskiej
          </p>
          {!isBackendSynced && isAuthenticated && (
            <p className="mt-2 text-xs text-amber-600/70">
              Dane z pamięci lokalnej — synchronizacja w toku…
            </p>
          )}
        </div>

        {/* ── Three-stage path ── */}
        <div className="mb-10 space-y-4">
          {STAGES.map((stage, idx) => {
            const progress = journeyProgress[stage.key];
            const isActive = stage.key === activeStageKey;
            const isUnlocked =
              stage.key === "purgativa" ||
              (stage.key === "illuminativa" && totalSessions >= 20) ||
              (stage.key === "unitiva" && totalSessions >= 40);

            return (
              <div
                key={stage.key}
                className={`rounded-2xl border p-6 transition-all ${
                  isActive
                    ? "border-amber-500/30 bg-amber-500/5"
                    : isUnlocked
                    ? "border-white/10 bg-white/5"
                    : "border-white/5 bg-white/[0.02] opacity-50"
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-amber-400 text-xs font-mono">
                        {String(idx + 1).padStart(2, "0")}
                      </span>
                      <h2 className="font-cinzel text-lg font-semibold text-sacred-text">
                        {stage.namePl}
                      </h2>
                      <span className="text-gray-500 text-sm">
                        · {stage.name}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 leading-relaxed max-w-md">
                      {stage.description}
                    </p>
                  </div>
                  <span className="text-2xl font-bold text-amber-400 ml-4 shrink-0">
                    {progress}%
                  </span>
                </div>

                {/* Progress bar */}
                <div className="h-2 rounded-full bg-white/10 mb-4">
                  <div
                    className="h-2 rounded-full bg-gradient-to-r from-amber-600 to-amber-400 transition-all duration-700"
                    style={{ width: `${progress}%` }}
                  />
                </div>

                {/* Scripture */}
                <p className="text-xs italic text-gray-500 mb-4">
                  {stage.scripture}
                </p>

                {/* Milestones */}
                <div className="flex flex-wrap gap-2">
                  {stage.milestones.map((m) => {
                    const achieved = totalSessions >= m.sessions;
                    return (
                      <span
                        key={m.sessions}
                        className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs transition-colors ${
                          achieved
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : "bg-white/5 text-gray-600 border border-white/5"
                        }`}
                      >
                        {achieved ? "✓" : "○"} {m.label}
                      </span>
                    );
                  })}
                </div>

                {!isUnlocked && (
                  <p className="mt-3 text-xs text-gray-600">
                    Odblokuj po{" "}
                    {stage.key === "illuminativa" ? 20 : 40} sesjach
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {/* ── Session heatmap ── */}
        <div className="mb-10 rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="font-cinzel text-base font-semibold text-amber-400 mb-5">
            Kalendarze modlitwy — ostatnie 12 tygodni
          </h2>

          <div className="flex gap-1 overflow-x-auto pb-1">
            {weeks.map((week, wi) => (
              <div key={wi} className="flex flex-col gap-1">
                {week.map((day) => (
                  <div
                    key={day}
                    title={day}
                    className={`h-3 w-3 rounded-sm ${intensityClass(heatmap.get(day) ?? 0)}`}
                  />
                ))}
              </div>
            ))}
          </div>

          <div className="mt-3 flex items-center gap-2 text-xs text-gray-600">
            <span>Mniej</span>
            {[0, 1, 2, 3].map((v) => (
              <div
                key={v}
                className={`h-3 w-3 rounded-sm ${intensityClass(v)}`}
              />
            ))}
            <span>Więcej</span>
          </div>

          {sessions.length === 0 && (
            <p className="mt-4 text-center text-sm text-gray-600">
              Zacznij pierwszą sesję Lectio Divina, by zobaczyć kalendarz.
            </p>
          )}
        </div>

        {/* ── Weekly bar chart ── */}
        <div className="mb-10 rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="font-cinzel text-base font-semibold text-amber-400 mb-5">
            Sesje ostatnich 8 tygodni
          </h2>

          <div className="flex items-end gap-2 h-24">
            {weeklyBars.map((count, i) => {
              const heightPct = Math.round((count / maxBar) * 100);
              const isCurrentWeek = i === 7;
              return (
                <div
                  key={i}
                  className="flex-1 flex flex-col items-center gap-1"
                >
                  <div className="w-full flex items-end justify-center" style={{ height: "80px" }}>
                    <div
                      className={`w-full rounded-t-md transition-all duration-500 ${
                        isCurrentWeek ? "bg-amber-500" : "bg-amber-500/40"
                      }`}
                      style={{ height: count > 0 ? `${heightPct}%` : "4px" }}
                    />
                  </div>
                  <span className="text-xs text-gray-600 tabular-nums">
                    {count}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="flex justify-between text-xs text-gray-600 mt-1 px-1">
            <span>8 tygodni temu</span>
            <span>Ten tydzień</span>
          </div>
        </div>

        {/* ── Top themes ── */}
        {themes.length > 0 && (
          <div className="mb-10 rounded-2xl border border-white/10 bg-white/5 p-6">
            <h2 className="font-cinzel text-base font-semibold text-amber-400 mb-5">
              Powracające tematy duchowe
            </h2>
            <div className="flex flex-wrap gap-2">
              {themes.slice(0, 10).map((t, i) => {
                const maxCount = themes[0]?.count ?? 1;
                const sizePct = Math.round((t.count / maxCount) * 100);
                const textSize =
                  sizePct > 80
                    ? "text-lg"
                    : sizePct > 50
                    ? "text-base"
                    : "text-sm";
                return (
                  <span
                    key={i}
                    className={`rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-amber-300/80 ${textSize}`}
                  >
                    {t.name}
                    <span className="ml-1 text-xs text-gray-600">
                      ×{t.count}
                    </span>
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* CTA */}
        <div className="text-center">
          <Link
            href="/lectio-divina"
            className="inline-block rounded-xl bg-amber-600 px-8 py-4 font-cinzel font-semibold text-white hover:bg-amber-700 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            Rozpocznij dzisiejszą Lectio Divina
          </Link>
        </div>
      </div>
    </div>
  );
}
