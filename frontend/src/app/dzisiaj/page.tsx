"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth";
import { useProgressStore } from "@/stores/progress";
import { api } from "@/lib/api";

// ── Stałe sezonowe ────────────────────────────────────────────────────────────

const SEASON_COLORS: Record<string, string> = {
  advent:   "from-[#1a0a2e]/80 to-[#0d0b1a] border-purple-800/40",
  christmas:"from-[#1a1000]/80 to-[#0d0b1a] border-yellow-700/40",
  lent:     "from-[#1a0a00]/80 to-[#0d0b1a] border-purple-900/40",
  easter:   "from-[#001a08]/80 to-[#0d0b1a] border-yellow-600/40",
  ordinary: "from-[#001408]/80 to-[#0d0b1a] border-green-800/40",
};

const SEASON_BADGE: Record<string, string> = {
  advent:   "bg-purple-900/40 text-purple-300 border-purple-700/40",
  christmas:"bg-yellow-900/40 text-yellow-300 border-yellow-700/40",
  lent:     "bg-red-900/30 text-red-300 border-red-800/40",
  easter:   "bg-yellow-800/30 text-yellow-200 border-yellow-600/40",
  ordinary: "bg-green-900/30 text-green-300 border-green-700/40",
};

const COLOR_DOT: Record<string, string> = {
  white:  "bg-white",
  red:    "bg-red-500",
  green:  "bg-green-500",
  purple: "bg-purple-500",
  gold:   "bg-yellow-400",
  rose:   "bg-rose-400",
};

const DAY_PL: Record<string, string> = {
  Monday: "Poniedziałek", Tuesday: "Wtorek", Wednesday: "Środa",
  Thursday: "Czwartek", Friday: "Piątek", Saturday: "Sobota", Sunday: "Niedziela",
};

const GREETING_HOUR: Record<number, string> = {
  0:  "Dobranoc",
  1:  "Dobranoc",
  2:  "Dobranoc",
  3:  "Dobranoc",
  4:  "Dzień dobry",
  5:  "Dzień dobry",
  6:  "Dzień dobry",
  7:  "Dzień dobry",
  8:  "Dzień dobry",
  9:  "Dzień dobry",
  10: "Dzień dobry",
  11: "Dzień dobry",
  12: "Dobry dzień",
  13: "Dobry dzień",
  14: "Dobry dzień",
  15: "Dobry dzień",
  16: "Dobry wieczór",
  17: "Dobry wieczór",
  18: "Dobry wieczór",
  19: "Dobry wieczór",
  20: "Dobry wieczór",
  21: "Dobry wieczór",
  22: "Dobranoc",
  23: "Dobranoc",
};

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

// ── Komponent streak ──────────────────────────────────────────────────────────

function StreakWidget({ streak }: { streak: number }) {
  const nextMilestone = STREAK_MILESTONES.find((m) => m > streak) ?? streak + 1;
  const progress = Math.min(100, (streak / nextMilestone) * 100);

  if (streak === 0) return null;

  return (
    <div className="bg-gradient-to-r from-orange-900/30 to-amber-900/20 border border-orange-700/30 rounded-2xl p-4 mb-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">🔥</span>
          <div>
            <div className="text-sm font-bold text-white">
              {streak} {streak === 1 ? "dzień" : streak < 5 ? "dni" : "dni"} z rzędu
            </div>
            <div className="text-xs text-orange-300/70">
              Do kolejnego milestone: {nextMilestone - streak} {nextMilestone - streak === 1 ? "dzień" : "dni"}
            </div>
          </div>
        </div>
        <div className="text-2xl font-bold text-[#d4af37]">{streak}</div>
      </div>
      <div className="w-full bg-white/10 rounded-full h-1.5">
        <div
          className="bg-gradient-to-r from-orange-500 to-[#d4af37] h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

// ── Komponent główny ──────────────────────────────────────────────────────────

export default function DzisiajPage() {
  const { user, isAuthenticated, loadFromStorage } = useAuthStore();
  const { prayerStreak, loadFromStorage: loadProgress } = useProgressStore();

  const [data, setData] = useState<DailyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [prayerExpanded, setPrayerExpanded] = useState(false);
  const [completedTasks, setCompletedTasks] = useState<Set<string>>(new Set());
  const [notifTime, setNotifTime] = useState("07:00");
  const [notifSet, setNotifSet] = useState(false);
  const [notifLoading, setNotifLoading] = useState(false);

  useEffect(() => {
    loadFromStorage();
    loadProgress();
    setCompletedTasks(loadCompletedToday());

    // Sprawdź czy notif już ustawione dziś
    const notifDone = localStorage.getItem("sancta_notif_set");
    if (notifDone) setNotifSet(true);

    // Pobierz dane liturgiczne — endpoint publiczny, api.ts dodaje JWT jeśli jest
    api.get<DailyData>("/api/v1/breviary/daily-engagement")
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => {
        setLoading(false);
      });
  }, [loadFromStorage, loadProgress]);

  const toggleTask = useCallback((href: string) => {
    setCompletedTasks((prev) => {
      const next = new Set(prev);
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

      // Pobierz VAPID public key z backendu
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
      // Powiadomienia niedostępne — nie blokujemy
    } finally {
      setNotifLoading(false);
    }
  }, [notifTime]);

  // ── Powitanie ─────────────────────────────────────────────────────────────

  const hour = new Date().getHours();
  const greeting = GREETING_HOUR[hour] ?? "Dzień dobry";
  const firstName = user?.displayName?.split(" ")[0] ?? user?.email?.split("@")[0] ?? null;
  const completedCount = completedTasks.size;
  const allDone = data && completedCount >= data.suggested_practices.length;

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[#d4af37]/30 border-t-[#d4af37] rounded-full animate-spin" />
          <p className="text-xs text-gray-500">Ładowanie liturgii dnia…</p>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex items-center justify-center px-4">
        <div className="text-center space-y-3">
          <p className="text-gray-400">Nie można załadować danych liturgicznych.</p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm text-[#d4af37] underline"
          >
            Spróbuj ponownie
          </button>
        </div>
      </main>
    );
  }

  const seasonKey = data.liturgical.season;
  const gradientClass = SEASON_COLORS[seasonKey] || SEASON_COLORS.ordinary;
  const badgeClass = SEASON_BADGE[seasonKey] || SEASON_BADGE.ordinary;
  const dotClass = COLOR_DOT[data.liturgical.color] || "bg-gray-400";
  const dayPl = DAY_PL[data.day_of_week] || data.day_of_week;

  const dateObj = new Date(data.date + "T12:00:00");
  const dateFormatted = dateObj.toLocaleDateString("pl-PL", {
    day: "numeric", month: "long", year: "numeric",
  });

  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      <div className="max-w-2xl mx-auto px-4 py-8 pb-28 space-y-4">

        {/* ── Nagłówek z pozdrowieniem ────────────────────────────────────── */}
        <div className="text-center mb-2">
          <div className="text-xs text-gray-500 mb-1">{dayPl}</div>
          <h1 className="text-2xl font-bold text-[#d4af37]">{dateFormatted}</h1>
          {isAuthenticated && firstName && (
            <p className="text-sm text-gray-400 mt-1">
              {greeting}, <span className="text-white font-medium">{firstName}</span> 🙏
            </p>
          )}
        </div>

        {/* ── Streak modlitewny ────────────────────────────────────────────── */}
        <StreakWidget streak={prayerStreak} />

        {/* ── Postęp dnia ─────────────────────────────────────────────────── */}
        {data.suggested_practices.length > 0 && (
          <div className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3">
            <div className="flex gap-1.5">
              {data.suggested_practices.map((p) => (
                <div
                  key={p.href}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    completedTasks.has(p.href) ? "bg-[#d4af37]" : "bg-white/20"
                  }`}
                />
              ))}
            </div>
            <span className="text-xs text-gray-400">
              {allDone ? (
                <span className="text-[#d4af37]">✓ Wszystkie praktyki dnia ukończone!</span>
              ) : (
                `${completedCount}/${data.suggested_practices.length} praktyk ukończono`
              )}
            </span>
          </div>
        )}

        {/* ── Karta liturgiczna ────────────────────────────────────────────── */}
        <div className={`rounded-2xl border bg-gradient-to-b ${gradientClass} p-5`}>
          <div className="flex items-center gap-3 mb-3">
            <div className={`w-3 h-3 rounded-full flex-shrink-0 ${dotClass}`} />
            <span className={`text-xs px-2 py-0.5 rounded-full border ${badgeClass}`}>
              {data.liturgical.season_label}
            </span>
            <span className="text-xs text-gray-500 capitalize">{data.liturgical.rank}</span>
          </div>
          {data.liturgical.feast ? (
            <>
              <h2 className="text-lg font-bold text-white mb-1">{data.liturgical.feast}</h2>
              <p className="text-xs text-gray-400">Uroczystość / Święto liturgiczne</p>
            </>
          ) : (
            <h2 className="text-lg font-bold text-white">Feria zwykła</h2>
          )}
        </div>

        {/* ── Patron dnia ─────────────────────────────────────────────────── */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
          <div className="flex items-start gap-3">
            <div className="text-3xl flex-shrink-0">{data.saint.icon}</div>
            <div className="min-w-0">
              <div className="text-xs text-[#d4af37] mb-1">Patron dnia</div>
              <h3 className="font-semibold text-white mb-2">{data.saint.name}</h3>
              <p className="text-sm text-gray-300 leading-relaxed">{data.saint.description}</p>
              {data.saint.patronage && (
                <p className="text-xs text-gray-500 mt-2">
                  <span className="text-gray-600">Patron: </span>
                  {data.saint.patronage}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* ── Modlitwa poranna ─────────────────────────────────────────────── */}
        <div className="bg-[#d4af37]/5 border border-[#d4af37]/20 rounded-2xl overflow-hidden">
          <button
            onClick={() => setPrayerExpanded(!prayerExpanded)}
            className="w-full px-5 py-4 text-left flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">🙏</span>
              <span className="text-sm font-medium text-[#d4af37]">Modlitwa poranna</span>
            </div>
            <span className="text-gray-500 text-xs transition-transform duration-200" style={{
              transform: prayerExpanded ? "rotate(180deg)" : "rotate(0deg)"
            }}>▼</span>
          </button>
          {prayerExpanded && (
            <div className="px-5 pb-5 border-t border-[#d4af37]/10">
              <p className="text-sm text-gray-200 leading-relaxed pt-3 italic">
                {data.morning_prayer}
              </p>
            </div>
          )}
        </div>

        {/* ── Praktyki dnia ────────────────────────────────────────────────── */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Praktyki na dziś
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {data.suggested_practices.map((p) => {
              const done = completedTasks.has(p.href);
              return (
                <div key={p.href} className="relative group">
                  <Link
                    href={p.href}
                    className={`flex flex-col p-4 rounded-xl border transition-all ${
                      done
                        ? "bg-[#d4af37]/10 border-[#d4af37]/40"
                        : "bg-white/5 border-white/10 hover:bg-white/10 hover:border-[#d4af37]/30"
                    }`}
                  >
                    <div className="text-2xl mb-2">{p.icon}</div>
                    <div className={`text-sm font-medium transition-colors ${
                      done ? "text-[#d4af37]" : "text-white group-hover:text-[#d4af37]"
                    }`}>
                      {p.label}
                    </div>
                    {done && (
                      <div className="absolute top-2 right-2 w-5 h-5 bg-[#d4af37] rounded-full flex items-center justify-center">
                        <span className="text-black text-xs font-bold">✓</span>
                      </div>
                    )}
                  </Link>
                  {/* Przycisk oznacz jako wykonane */}
                  <button
                    onClick={() => toggleTask(p.href)}
                    className={`mt-1.5 w-full text-xs py-1 rounded-lg border transition-colors ${
                      done
                        ? "border-[#d4af37]/30 text-[#d4af37]/60 hover:text-red-400 hover:border-red-400/30"
                        : "border-white/10 text-gray-600 hover:text-[#d4af37] hover:border-[#d4af37]/30"
                    }`}
                  >
                    {done ? "✓ Wykonano" : "Oznacz jako wykonane"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Przypomnienie poranne ─────────────────────────────────────────── */}
        {!notifSet ? (
          <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🔔</span>
              <span className="text-sm font-medium text-white">Przypomnienie poranne</span>
            </div>
            <p className="text-xs text-gray-400 mb-3">
              Imię świętego patrona i liturgia dnia — codziennie o wybranej godzinie.
            </p>
            <div className="flex gap-2">
              <input
                type="time"
                value={notifTime}
                onChange={(e) => setNotifTime(e.target.value)}
                className="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#d4af37]"
              />
              <button
                onClick={setupDailyNotification}
                disabled={notifLoading}
                className="flex-1 bg-[#d4af37]/20 hover:bg-[#d4af37]/30 border border-[#d4af37]/40 text-[#d4af37] text-sm font-medium rounded-lg py-2 transition-colors disabled:opacity-50"
              >
                {notifLoading ? "…" : "Ustaw"}
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-green-900/20 border border-green-700/30 rounded-2xl p-4 flex items-center justify-between">
            <span className="text-green-300 text-sm">✓ Przypomnienie ustawione na {notifTime}</span>
            <button
              onClick={() => {
                localStorage.removeItem("sancta_notif_set");
                setNotifSet(false);
              }}
              className="text-xs text-gray-500 hover:text-white"
            >
              Zmień
            </button>
          </div>
        )}

        {/* ── Szybkie linki ─────────────────────────────────────────────────── */}
        {isAuthenticated && (
          <div className="pt-2 border-t border-white/5 flex justify-center gap-6">
            <Link href="/dziennik" className="text-xs text-gray-600 hover:text-[#d4af37] transition-colors">
              Dziennik
            </Link>
            <Link href="/konto" className="text-xs text-gray-600 hover:text-[#d4af37] transition-colors">
              Moje konto
            </Link>
            <Link href="/dashboard" className="text-xs text-gray-600 hover:text-[#d4af37] transition-colors">
              Postęp duchowy
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
