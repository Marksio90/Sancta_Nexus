"use client";

import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Lightweight local user ID (guest session — replace with real auth)
function getGuestId(): string {
  if (typeof window === "undefined") return "guest";
  let id = localStorage.getItem("sn_guest_id");
  if (!id) {
    id = "guest-" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("sn_guest_id", id);
  }
  return id;
}

type AppState = "library" | "detail" | "day" | "tracking";

export default function NowennaPage() {
  const [appState, setAppState] = useState<AppState>("library");
  const [novenas, setNovenas] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [selectedFull, setSelectedFull] = useState<any>(null);
  const [selectedDay, setSelectedDay] = useState<number>(1);
  const [dayContent, setDayContent] = useState<any>(null);
  const [meditation, setMeditation] = useState("");
  const [loadingMeditation, setLoadingMeditation] = useState(false);
  const [myNovenas, setMyNovenas] = useState<any[]>([]);
  const [loadingMy, setLoadingMy] = useState(false);
  const [intention, setIntention] = useState("");
  const [starting, setStarting] = useState(false);
  const [userId, setUserId] = useState<string>("guest");

  useEffect(() => {
    setUserId(getGuestId());
    fetch(`${API}/api/v1/community/novenas`)
      .then((r) => r.json())
      .then((d) => setNovenas(d.novenas || []))
      .catch(() => {});
  }, []);

  const loadMyNovenas = useCallback(async () => {
    setLoadingMy(true);
    try {
      const res = await fetch(
        `${API}/api/v1/community/novenas/my?user_id=${userId}`
      );
      const data = await res.json();
      setMyNovenas(data.novenas || []);
    } catch {
      setMyNovenas([]);
    } finally {
      setLoadingMy(false);
    }
  }, [userId]);

  const openNovena = async (novena: any) => {
    setSelected(novena);
    setSelectedFull(null);
    setMeditation("");
    setAppState("detail");
    try {
      const res = await fetch(`${API}/api/v1/community/novenas/${novena.id}`);
      const data = await res.json();
      setSelectedFull(data);
    } catch {}
  };

  const openDay = async (novenaId: string, day: number) => {
    setSelectedDay(day);
    setDayContent(null);
    setMeditation("");
    setAppState("day");
    try {
      const res = await fetch(
        `${API}/api/v1/community/novenas/${novenaId}/day/${day}`
      );
      const data = await res.json();
      setDayContent(data);
    } catch {}
  };

  const loadMeditation = async (novenaId: string, day: number) => {
    setLoadingMeditation(true);
    try {
      const res = await fetch(
        `${API}/api/v1/community/novenas/${novenaId}/meditation/${day}`
      );
      const data = await res.json();
      setMeditation(data.meditation || "");
    } catch {
      setMeditation("Nie udało się załadować medytacji.");
    } finally {
      setLoadingMeditation(false);
    }
  };

  const startNovena = async () => {
    if (!selected || starting) return;
    setStarting(true);
    try {
      await fetch(
        `${API}/api/v1/community/novenas/${selected.id}/start?user_id=${userId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ intention: intention.trim() || null }),
        }
      );
      await loadMyNovenas();
      setIntention("");
      setAppState("tracking");
    } catch {} finally {
      setStarting(false);
    }
  };

  const completeDay = async (trackingId: string, day: number) => {
    try {
      await fetch(
        `${API}/api/v1/community/novenas/tracking/${trackingId}/complete-day?user_id=${userId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ day }),
        }
      );
      await loadMyNovenas();
    } catch {}
  };

  // ── Library ────────────────────────────────────────────────────────────────
  if (appState === "library") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-10 pb-24">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-[#d4af37]">🕯 Nowenny</h1>
              <p className="text-gray-500 text-xs">8 nowenn · 9 dni · tracking postępu</p>
            </div>
            <button
              onClick={() => { loadMyNovenas(); setAppState("tracking"); }}
              className="text-xs bg-white/5 border border-white/10 px-3 py-2 rounded-xl text-gray-300 hover:border-white/30 transition-all"
            >
              Moje nowenny
            </button>
          </div>

          <div className="space-y-3">
            {novenas.map((novena) => (
              <button
                key={novena.id}
                onClick={() => openNovena(novena)}
                className={`w-full rounded-2xl border ${novena.border || "border-white/10"} bg-gradient-to-br ${novena.color || "from-gray-900/40 to-gray-800/20"} p-4 text-left hover:scale-[1.01] transition-all`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-3xl">{novena.patron_icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-white text-sm mb-0.5">{novena.title}</div>
                    <div className="text-xs text-[#d4af37] mb-1">{novena.patron}</div>
                    <p className="text-xs text-gray-400 line-clamp-2">{novena.description}</p>
                    <div className="flex gap-3 mt-2 text-xs text-gray-600">
                      <span>{novena.days} dni</span>
                      <span>{novena.scripture}</span>
                      <span>KKK {novena.ccc}</span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </main>
    );
  }

  // ── Novena detail ──────────────────────────────────────────────────────────
  if (appState === "detail" && selected) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("library")} className="text-gray-400 hover:text-white">←</button>
            <div>
              <h1 className="text-xl font-bold text-[#d4af37]">{selected.title}</h1>
              <div className="text-xs text-gray-500">{selected.patron}</div>
            </div>
          </div>

          {/* Days grid */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">9 dni nowenny</h3>
            <div className="grid grid-cols-3 gap-2">
              {Array.from({ length: 9 }, (_, i) => i + 1).map((day) => (
                <button
                  key={day}
                  onClick={() => openDay(selected.id, day)}
                  className="bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl p-3 text-center transition-all"
                >
                  <div className="text-sm font-bold text-[#d4af37]">Dzień {day}</div>
                  {selectedFull?.daily_intentions?.[day - 1] && (
                    <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                      {selectedFull.daily_intentions[day - 1].replace(/^Dzień \d+ — /, "")}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Start novena */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-4 mb-4">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">Rozpocznij noweną z trackingiem</h3>
            <input
              type="text"
              value={intention}
              onChange={(e) => setIntention(e.target.value)}
              maxLength={500}
              placeholder="W jakiej intencji odmawiasz tę noweną? (opcjonalnie)"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37] mb-3"
            />
            <button
              onClick={startNovena}
              disabled={starting}
              className="w-full bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors disabled:opacity-50"
            >
              {starting ? "Startuję..." : `🕯 Rozpocznij noweną do ${selected.patron}`}
            </button>
          </div>

          {selectedFull?.origin && (
            <div className="text-xs text-gray-600 text-center">
              Źródło: {selectedFull.origin}
            </div>
          )}
        </div>
      </main>
    );
  }

  // ── Day content ────────────────────────────────────────────────────────────
  if (appState === "day" && selected) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("detail")} className="text-gray-400 hover:text-white">←</button>
            <div>
              <div className="text-xs text-gray-500">{selected.title}</div>
              <h1 className="text-lg font-bold text-[#d4af37]">Dzień {selectedDay}</h1>
            </div>
          </div>

          {dayContent ? (
            <>
              <div className="bg-white/5 rounded-2xl p-5 mb-4">
                <h3 className="text-sm font-semibold text-[#d4af37] mb-3">
                  {dayContent.title}
                </h3>
                <div className="text-sm text-gray-200 leading-loose whitespace-pre-wrap">
                  {dayContent.prayer}
                </div>
              </div>

              {!meditation && !loadingMeditation && (
                <button
                  onClick={() => loadMeditation(selected.id, selectedDay)}
                  className="w-full bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl py-3 text-sm text-gray-300 transition-all mb-4"
                >
                  ✨ Medytacja AI na ten dzień
                </button>
              )}

              {(meditation || loadingMeditation) && (
                <div className="bg-amber-900/20 border border-amber-700/30 rounded-2xl p-5 mb-4 text-sm text-gray-200 leading-loose whitespace-pre-wrap">
                  {loadingMeditation ? (
                    <span className="text-gray-500 animate-pulse">Generuję medytację...</span>
                  ) : meditation}
                </div>
              )}

              <div className="flex gap-2">
                {selectedDay > 1 && (
                  <button
                    onClick={() => openDay(selected.id, selectedDay - 1)}
                    className="flex-1 bg-white/5 border border-white/10 text-gray-300 py-3 rounded-xl text-sm transition-all hover:bg-white/10"
                  >
                    ← Dzień {selectedDay - 1}
                  </button>
                )}
                {selectedDay < 9 && (
                  <button
                    onClick={() => openDay(selected.id, selectedDay + 1)}
                    className="flex-1 bg-[#d4af37] text-black font-semibold py-3 rounded-xl text-sm hover:bg-[#c9a227] transition-colors"
                  >
                    Dzień {selectedDay + 1} →
                  </button>
                )}
              </div>
            </>
          ) : (
            <div className="text-center text-gray-500 py-10 animate-pulse">Ładuję...</div>
          )}
        </div>
      </main>
    );
  }

  // ── My novenas (tracking) ──────────────────────────────────────────────────
  if (appState === "tracking") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("library")} className="text-gray-400 hover:text-white">←</button>
            <h1 className="text-xl font-bold text-[#d4af37]">Moje nowenny</h1>
          </div>

          {loadingMy ? (
            <div className="text-center text-gray-500 animate-pulse py-10">Ładuję...</div>
          ) : myNovenas.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <div className="text-4xl mb-3">🕯</div>
              <p className="mb-4">Nie rozpocząłeś jeszcze żadnej nowenny.</p>
              <button
                onClick={() => setAppState("library")}
                className="text-[#d4af37] text-sm underline"
              >
                Przeglądaj bibliotekę nowenn
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {myNovenas.map((n) => (
                <div
                  key={n.id}
                  className="bg-white/5 border border-white/10 rounded-2xl p-5"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-2xl">{n.patron_icon}</span>
                    <div className="flex-1">
                      <div className="font-semibold text-sm text-white">{n.novena_title}</div>
                      {n.intention && (
                        <div className="text-xs text-gray-500 mt-0.5 italic">
                          «{n.intention}»
                        </div>
                      )}
                    </div>
                    {n.is_complete && (
                      <span className="text-xs bg-green-700/50 text-green-300 px-2 py-1 rounded-full">
                        ✓ Ukończona
                      </span>
                    )}
                  </div>

                  {/* Progress bar */}
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Postęp</span>
                      <span>{n.completed_days.length}/{n.total_days} dni</span>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-1.5">
                      <div
                        className="bg-[#d4af37] h-1.5 rounded-full transition-all"
                        style={{ width: `${n.progress_percent}%` }}
                      />
                    </div>
                  </div>

                  {/* Day buttons */}
                  <div className="grid grid-cols-9 gap-1">
                    {Array.from({ length: n.total_days }, (_, i) => i + 1).map((day) => {
                      const done = n.completed_days.includes(day);
                      return (
                        <button
                          key={day}
                          onClick={() => !done && completeDay(n.id, day)}
                          disabled={done}
                          className={`aspect-square rounded-lg text-xs font-bold transition-all ${
                            done
                              ? "bg-[#d4af37] text-black"
                              : "bg-white/10 text-gray-500 hover:bg-white/20 hover:text-white"
                          }`}
                        >
                          {done ? "✓" : day}
                        </button>
                      );
                    })}
                  </div>

                  {!n.is_complete && (
                    <p className="text-xs text-gray-600 mt-2 text-center">
                      Dotknij dnia, aby oznaczyć jako odmówiony
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    );
  }

  return null;
}
