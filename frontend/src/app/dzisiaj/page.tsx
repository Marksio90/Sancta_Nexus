"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

export default function DzisiajPage() {
  const [data, setData] = useState<DailyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [prayerExpanded, setPrayerExpanded] = useState(false);
  const [notifTime, setNotifTime] = useState("07:00");
  const [notifSet, setNotifSet] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/v1/breviary/daily-engagement`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const setupDailyNotification = async () => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      alert("Twoja przeglądarka nie obsługuje powiadomień push.");
      return;
    }
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") return;

      const reg = await navigator.serviceWorker.ready;
      const vapidRes = await fetch(`${API}/api/v1/notifications/vapid-public-key`);
      const { public_key } = await vapidRes.json();

      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: public_key,
      });

      // Rejestruj subskrypcję
      const subJson = sub.toJSON() as { endpoint: string; keys: Record<string, string> };
      await fetch(`${API}/api/v1/notifications/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint: subJson.endpoint, keys: subJson.keys }),
      });

      // Ustaw czas powiadomienia
      await fetch(`${API}/api/v1/notifications/daily-reminder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint: subJson.endpoint, time: notifTime }),
      });

      setNotifSet(true);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex items-center justify-center">
        <div className="animate-pulse text-[#d4af37]">📖</div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex items-center justify-center">
        <p className="text-gray-500">Nie można załadować danych liturgicznych.</p>
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
      <div className="max-w-2xl mx-auto px-4 py-8 pb-28">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="text-xs text-gray-500 mb-1">{dayPl}</div>
          <h1 className="text-2xl font-bold text-[#d4af37]">{dateFormatted}</h1>
        </div>

        {/* Liturgical day card */}
        <div className={`rounded-2xl border bg-gradient-to-b ${gradientClass} p-5 mb-4`}>
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

        {/* Saint of the day */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 mb-4">
          <div className="flex items-start gap-3">
            <div className="text-3xl flex-shrink-0">{data.saint.icon}</div>
            <div>
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

        {/* Morning prayer */}
        <div className="bg-[#d4af37]/5 border border-[#d4af37]/20 rounded-2xl p-5 mb-4">
          <button
            onClick={() => setPrayerExpanded(!prayerExpanded)}
            className="w-full text-left"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">🙏</span>
                <span className="text-sm font-medium text-[#d4af37]">Modlitwa poranna</span>
              </div>
              <span className="text-gray-500 text-xs">{prayerExpanded ? "▲" : "▼"}</span>
            </div>
          </button>
          {prayerExpanded && (
            <p className="text-sm text-gray-200 leading-relaxed mt-3 italic border-t border-[#d4af37]/10 pt-3">
              {data.morning_prayer}
            </p>
          )}
        </div>

        {/* Suggested practices */}
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Na dziś
        </h3>
        <div className="grid grid-cols-2 gap-3 mb-6">
          {data.suggested_practices.map((p) => (
            <Link
              key={p.href}
              href={p.href}
              className="bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl p-4 transition-all hover:border-[#d4af37]/30 group"
            >
              <div className="text-2xl mb-2">{p.icon}</div>
              <div className="text-sm font-medium text-white group-hover:text-[#d4af37] transition-colors">
                {p.label}
              </div>
            </Link>
          ))}
        </div>

        {/* Daily notification setup */}
        {!notifSet ? (
          <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">🔔</span>
              <span className="text-sm font-medium text-white">Przypomnienie poranne</span>
            </div>
            <p className="text-xs text-gray-400 mb-3">
              Otrzymuj codziennie imię świętego patrona i liturgię dnia.
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
                className="flex-1 bg-[#d4af37]/20 hover:bg-[#d4af37]/30 border border-[#d4af37]/40 text-[#d4af37] text-sm font-medium rounded-lg py-2 transition-colors"
              >
                Ustaw przypomnienie
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-green-900/20 border border-green-700/30 rounded-2xl p-4 text-center">
            <span className="text-green-300 text-sm">✓ Przypomnienie ustawione na {notifTime}</span>
          </div>
        )}
      </div>
    </main>
  );
}
