"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth";
import { useProgressStore } from "@/stores/progress";
import { api } from "@/lib/api";

// ── Kolory liturgiczne ─────────────────────────────────────────────────────────

const SEASON_HERO: Record<string, { bg: string; glow: string; accent: string; badge: string }> = {
  advent:   { bg: "from-purple-950/70 via-[#0d0b1a] to-[#0d0b1a]",  glow: "via-purple-900/20",  accent: "text-purple-300",  badge: "bg-purple-900/50 text-purple-200 border-purple-700/50" },
  christmas:{ bg: "from-yellow-950/70 via-[#0d0b1a] to-[#0d0b1a]",  glow: "via-yellow-900/15",  accent: "text-yellow-200",  badge: "bg-yellow-900/50 text-yellow-200 border-yellow-700/50" },
  lent:     { bg: "from-[#1c0a00]/80 via-[#0d0b1a] to-[#0d0b1a]",   glow: "via-red-950/20",     accent: "text-red-300",     badge: "bg-red-950/50 text-red-200 border-red-900/50" },
  easter:   { bg: "from-[#001a06]/80 via-[#0d0b1a] to-[#0d0b1a]",   glow: "via-emerald-950/20", accent: "text-emerald-300", badge: "bg-emerald-950/50 text-emerald-200 border-emerald-800/50" },
  ordinary: { bg: "from-[#001208]/70 via-[#0d0b1a] to-[#0d0b1a]",   glow: "via-green-950/15",   accent: "text-green-300",   badge: "bg-green-950/50 text-green-200 border-green-800/50" },
};

const COLOR_DOT: Record<string, string> = {
  white:  "bg-white shadow-[0_0_6px_rgba(255,255,255,0.6)]",
  red:    "bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]",
  green:  "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]",
  purple: "bg-purple-500 shadow-[0_0_6px_rgba(168,85,247,0.6)]",
  gold:   "bg-yellow-400 shadow-[0_0_6px_rgba(250,204,21,0.6)]",
  rose:   "bg-rose-400 shadow-[0_0_6px_rgba(251,113,133,0.6)]",
};

const DAY_PL: Record<string, string> = {
  Monday: "Poniedziałek", Tuesday: "Wtorek", Wednesday: "Środa",
  Thursday: "Czwartek", Friday: "Piątek", Saturday: "Sobota", Sunday: "Niedziela",
};

const HOUR_GREETING: [number, string][] = [
  [5,  "Dobranoc"],
  [12, "Dzień dobry"],
  [17, "Dobry dzień"],
  [22, "Dobry wieczór"],
  [24, "Dobranoc"],
];

const HOUR_ICON: [number, string][] = [
  [5,  "✦"],
  [12, "☀"],
  [17, "🌤"],
  [22, "🌙"],
  [24, "✦"],
];

const STREAK_MILESTONES = [3, 7, 14, 30, 60, 100];

// ── Typy ──────────────────────────────────────────────────────────────────────

interface DailyData {
  date: string;
  day_of_week: string;
  liturgical: {
    season: string;
    season_label: string;
    color: string;
    feast: string | null;
    rank: string;
  };
  saint: {
    name: string;
    description: string;
    patronage: string;
    icon: string;
  };
  morning_prayer: string;
  suggested_practices: { label: string; href: string; icon: string }[];
}

const DAILY_TASKS_KEY = "sancta_daily_tasks";

function getTodayKey() {
  return new Date().toISOString().split("T")[0];
}

function loadCompletedToday(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(DAILY_TASKS_KEY);
    if (!raw) return new Set();
    const { date, completed } = JSON.parse(raw) as { date: string; completed: string[] };
    if (date !== getTodayKey()) return new Set();
    return new Set(completed);
  } catch {
    return new Set();
  }
}

function saveCompletedToday(completed: Set<string>) {
  if (typeof window === "undefined") return;
  localStorage.setItem(
    DAILY_TASKS_KEY,
    JSON.stringify({ date: getTodayKey(), completed: Array.from(completed) })
  );
}

function getGreeting(hour: number): string {
  for (const [h, g] of HOUR_GREETING) if (hour < h) return g;
  return "Dzień dobry";
}

function getHourIcon(hour: number): string {
  for (const [h, icon] of HOUR_ICON) if (hour < h) return icon;
  return "✦";
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse bg-white/5 rounded-xl ${className}`} />;
}

// ── Komponent główny ──────────────────────────────────────────────────────────

export default function DzisiajPage() {
  const { user, isAuthenticated, loadFromStorage } = useAuthStore();
  const { prayerStreak, loadFromStorage: loadProgress } = useProgressStore();

  const [data, setData] = useState<DailyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [prayerExpanded, setPrayerExpanded] = useState(false);
  const [completedTasks, setCompletedTasks] = useState<Set<string>>(() => loadCompletedToday());
  const [notifTime, setNotifTime] = useState(() =>
    typeof window !== "undefined" ? (localStorage.getItem("sancta_notif_set") ?? "07:00") : "07:00"
  );
  const [notifSet, setNotifSet] = useState(() =>
    typeof window !== "undefined" ? !!localStorage.getItem("sancta_notif_set") : false
  );
  const [notifLoading, setNotifLoading] = useState(false);

  useEffect(() => {
    loadFromStorage();
    loadProgress();

    api.get<DailyData>("/api/v1/breviary/daily-engagement")
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [loadFromStorage, loadProgress]);

  const toggleTask = useCallback((href: string) => {
    setCompletedTasks((prev: Set<string>) => {
      const next = new Set<string>(prev);
      if (next.has(href)) next.delete(href);
      else next.add(href);
      saveCompletedToday(next);
      return next;
    });
  }, []);

  const setupDailyNotification = useCallback(async () => {
    if (!("serviceWorker" in navigator) || !("Notification" in window)) {
      alert("Twoja przeglądarka nie obsługuje powiadomień push.");
      return;
    }
    setNotifLoading(true);
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") { setNotifLoading(false); return; }

      const reg = await navigator.serviceWorker.ready;
      const vapidData = await api.get<{ publicKey: string }>("/api/v1/notifications/vapid-public-key");
      const vapidKey = vapidData.publicKey;

      if (vapidKey) {
        const sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: vapidKey,
        });
        const subJson = sub.toJSON() as { endpoint: string; keys: Record<string, string> };
        await api.post("/api/v1/notifications/subscribe", {
          endpoint: subJson.endpoint,
          keys: subJson.keys,
        });
      }

      await api.post("/api/v1/notifications/daily-reminder", { time: notifTime });
      localStorage.setItem("sancta_notif_set", notifTime);
      setNotifSet(true);
    } catch {
      // Powiadomienia niedostępne
    } finally {
      setNotifLoading(false);
    }
  }, [notifTime]);

  const hour = new Date().getHours();
  const greeting = getGreeting(hour);
  const hourIcon = getHourIcon(hour);
  const firstName = user?.displayName?.split(" ")[0] ?? user?.email?.split("@")[0] ?? null;
  const completedCount = completedTasks.size;
  const totalCount = data?.suggested_practices.length ?? 0;
  const allDone = totalCount > 0 && completedCount >= totalCount;

  const seasonKey = data?.liturgical.season ?? "ordinary";
  const season = SEASON_HERO[seasonKey] ?? SEASON_HERO.ordinary;
  const dotClass = COLOR_DOT[data?.liturgical.color ?? ""] ?? "bg-gray-400";

  const dateObj = data ? new Date(data.date + "T12:00:00") : new Date();
  const dateFormatted = dateObj.toLocaleDateString("pl-PL", {
    day: "numeric", month: "long", year: "numeric",
  });
  const dayPl = data ? (DAY_PL[data.day_of_week] ?? data.day_of_week) : DAY_PL[["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"][new Date().getDay()]];

  const nextMilestone = STREAK_MILESTONES.find((m) => m > prayerStreak) ?? prayerStreak + 1;
  const streakProgress = Math.min(100, (prayerStreak / nextMilestone) * 100);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">

      {/* ── HERO ──────────────────────────────────────────────────────────── */}
      <div className={`relative bg-gradient-to-b ${season.bg} pt-10 pb-8 px-4 overflow-hidden`}>
        {/* glow blob */}
        <div className={`absolute inset-0 bg-gradient-to-b from-transparent ${season.glow} to-transparent opacity-60 pointer-events-none`} />

        <div className="relative max-w-2xl mx-auto text-center">
          {/* Krzyż / ikona pory dnia */}
          <div className="text-4xl mb-3 opacity-70">{hourIcon}</div>

          {/* Data */}
          <div className="text-xs tracking-[0.2em] text-gray-500 uppercase mb-1">{dayPl}</div>
          <h1 className="text-2xl font-bold text-[#d4af37] mb-1">{dateFormatted}</h1>

          {/* Powitanie */}
          {isAuthenticated && firstName ? (
            <p className="text-sm text-gray-400">
              {greeting},{" "}
              <span className="text-white font-medium">{firstName}</span>
            </p>
          ) : (
            <p className="text-sm text-gray-500">{greeting}</p>
          )}

          {/* Odznaka liturgiczna */}
          {loading ? (
            <div className="mt-4 flex justify-center">
              <Skeleton className="h-6 w-32" />
            </div>
          ) : data && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${dotClass}`} />
              <span className={`text-xs px-3 py-1 rounded-full border ${season.badge}`}>
                {data.liturgical.season_label}
              </span>
              {data.liturgical.feast && (
                <span className={`text-xs ${season.accent} font-medium`}>{data.liturgical.feast}</span>
              )}
            </div>
          )}

          {/* Postęp dnia */}
          {totalCount > 0 && (
            <div className="mt-5 max-w-xs mx-auto">
              <div className="flex justify-between text-xs text-gray-600 mb-1.5">
                <span>Postęp dnia</span>
                <span className={allDone ? "text-[#d4af37]" : "text-gray-500"}>
                  {allDone ? "✓ Ukończono" : `${completedCount} / ${totalCount}`}
                </span>
              </div>
              <div className="flex gap-1.5">
                {data?.suggested_practices.map((p) => (
                  <div
                    key={p.href}
                    className={`flex-1 h-1 rounded-full transition-all duration-500 ${
                      completedTasks.has(p.href) ? "bg-[#d4af37]" : "bg-white/15"
                    }`}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── CONTENT ───────────────────────────────────────────────────────── */}
      <div className="max-w-2xl mx-auto px-4 py-6 pb-28 space-y-4">

        {/* Streak */}
        {prayerStreak > 0 && (
          <div className="bg-gradient-to-r from-orange-950/60 to-amber-950/40 border border-orange-800/30 rounded-2xl px-4 py-3 flex items-center gap-4">
            <span className="text-2xl">🔥</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-white">
                {prayerStreak} {prayerStreak === 1 ? "dzień" : "dni"} z rzędu
              </div>
              <div className="w-full bg-white/10 rounded-full h-1 mt-1.5">
                <div
                  className="bg-gradient-to-r from-orange-500 to-[#d4af37] h-1 rounded-full transition-all duration-500"
                  style={{ width: `${streakProgress}%` }}
                />
              </div>
            </div>
            <div className="text-xl font-bold text-[#d4af37] flex-shrink-0">{prayerStreak}</div>
          </div>
        )}

        {/* ── Patron dnia ─────────────────────────────────────────────────── */}
        {loading ? (
          <Skeleton className="h-36" />
        ) : data && (
          <div className="relative rounded-2xl border border-[#d4af37]/20 bg-gradient-to-br from-[#d4af37]/8 via-[#0d0b1a] to-[#0d0b1a] p-5 overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#d4af37]/5 rounded-full blur-2xl pointer-events-none" />
            <div className="relative flex items-start gap-4">
              <div className="text-4xl flex-shrink-0 leading-none mt-0.5">{data.saint.icon}</div>
              <div className="min-w-0 flex-1">
                <div className="text-[10px] tracking-[0.15em] text-[#d4af37]/70 uppercase mb-1">
                  Patron dnia
                </div>
                <h2 className="text-lg font-bold text-white mb-1.5 leading-tight">
                  {data.saint.name}
                </h2>
                <p className="text-sm text-gray-300 leading-relaxed">
                  {data.saint.description}
                </p>
                {data.saint.patronage && (
                  <p className="text-xs text-gray-600 mt-2">
                    Patron: <span className="text-gray-500">{data.saint.patronage}</span>
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Modlitwa poranna ─────────────────────────────────────────────── */}
        {loading ? (
          <Skeleton className="h-14" />
        ) : data && (
          <div className="rounded-2xl border border-white/8 bg-white/3 overflow-hidden">
            <button
              onClick={() => setPrayerExpanded(!prayerExpanded)}
              className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-white/3 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <span className="text-base">🙏</span>
                <span className="text-sm font-medium text-gray-300">Modlitwa poranna</span>
              </div>
              <span
                className="text-gray-600 text-xs transition-transform duration-200"
                style={{ transform: prayerExpanded ? "rotate(180deg)" : "rotate(0deg)" }}
              >
                ▼
              </span>
            </button>
            {prayerExpanded && (
              <div className="px-5 pb-5 pt-1 border-t border-white/5">
                <p className="text-sm text-gray-300 leading-loose italic">
                  {data.morning_prayer}
                </p>
              </div>
            )}
          </div>
        )}

        {/* ── Praktyki dnia ─────────────────────────────────────────────────── */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="h-px flex-1 bg-white/8" />
            <span className="text-[10px] tracking-[0.2em] text-gray-600 uppercase">Praktyki na dziś</span>
            <div className="h-px flex-1 bg-white/8" />
          </div>

          {loading ? (
            <div className="grid grid-cols-2 gap-3">
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
            </div>
          ) : data && data.suggested_practices.length > 0 ? (
            <div className="grid grid-cols-2 gap-3">
              {data.suggested_practices.map((p) => {
                const done = completedTasks.has(p.href);
                return (
                  <div key={p.href} className="flex flex-col gap-1.5">
                    <Link
                      href={p.href}
                      className={`group flex flex-col p-4 rounded-xl border transition-all duration-200 ${
                        done
                          ? "bg-[#d4af37]/10 border-[#d4af37]/30"
                          : "bg-white/4 border-white/8 hover:bg-white/8 hover:border-[#d4af37]/25"
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-2xl leading-none">{p.icon}</span>
                        {done && (
                          <span className="w-4 h-4 bg-[#d4af37] rounded-full flex items-center justify-center">
                            <span className="text-black text-[9px] font-black">✓</span>
                          </span>
                        )}
                      </div>
                      <span className={`text-sm font-medium leading-tight transition-colors ${
                        done
                          ? "text-[#d4af37]"
                          : "text-white group-hover:text-[#d4af37]"
                      }`}>
                        {p.label}
                      </span>
                    </Link>
                    <button
                      onClick={() => toggleTask(p.href)}
                      className={`text-[11px] py-1.5 rounded-lg border transition-all ${
                        done
                          ? "border-[#d4af37]/20 text-[#d4af37]/50 hover:text-red-400/70 hover:border-red-400/20"
                          : "border-white/8 text-gray-600 hover:text-[#d4af37]/80 hover:border-[#d4af37]/20"
                      }`}
                    >
                      {done ? "✓ Wykonano" : "Oznacz"}
                    </button>
                  </div>
                );
              })}
            </div>
          ) : !loading && (
            <p className="text-sm text-gray-600 text-center py-6">
              Brak praktyk na dziś — spoczywaj w Panu.
            </p>
          )}
        </div>

        {/* ── Powiadomienie ─────────────────────────────────────────────────── */}
        {!notifSet ? (
          <div className="rounded-2xl border border-white/8 bg-white/3 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span>🔔</span>
              <span className="text-sm font-medium text-white">Jutrznia na każdy dzień</span>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              Patron dnia i liturgia — codziennie o wybranej godzinie.
            </p>
            <div className="flex gap-2">
              <input
                type="time"
                value={notifTime}
                onChange={(e) => setNotifTime(e.target.value)}
                className="bg-white/8 border border-white/15 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#d4af37]"
              />
              <button
                onClick={setupDailyNotification}
                disabled={notifLoading}
                className="flex-1 bg-[#d4af37]/15 hover:bg-[#d4af37]/25 border border-[#d4af37]/30 text-[#d4af37] text-sm font-medium rounded-lg py-2 transition-colors disabled:opacity-50"
              >
                {notifLoading ? "…" : "Ustaw"}
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-emerald-950/40 border border-emerald-800/30 rounded-2xl p-3.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-green-400 text-sm">✓</span>
              <span className="text-green-300 text-sm">Przypomnienie: {notifSet ? notifTime : ""}</span>
            </div>
            <button
              onClick={() => { localStorage.removeItem("sancta_notif_set"); setNotifSet(false); }}
              className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
            >
              Zmień
            </button>
          </div>
        )}

        {/* ── Szybkie linki ─────────────────────────────────────────────────── */}
        {isAuthenticated && (
          <div className="pt-3 border-t border-white/5 flex justify-center gap-8">
            <Link href="/dziennik" className="text-xs text-gray-600 hover:text-[#d4af37] transition-colors">
              Dziennik
            </Link>
            <Link href="/dashboard" className="text-xs text-gray-600 hover:text-[#d4af37] transition-colors">
              Mój postęp
            </Link>
            <Link href="/konto" className="text-xs text-gray-600 hover:text-[#d4af37] transition-colors">
              Konto
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
