"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRosarySocket } from "@/hooks/useRosarySocket";
import { PremiumAudioButton } from "@/components/AudioPlayer";
import { useBillingStore } from "@/stores/billing";
import { api } from "@/lib/api";

type MysteryType = "radosne" | "bolesne" | "chwalebne" | "swietlne";
type AppState = "menu" | "mysteries" | "decade" | "community" | "live";

interface RosaryMystery {
  number: number;
  title?: string;
  description?: string;
  scripture?: string;
  fruit?: string;
  meditation?: string;
}

interface CommunitySession {
  id: string;
  mystery_type: string;
  participant_count: number;
  intention?: string;
}

const MYSTERY_META: Record<MysteryType, { label: string; days: string; color: string; border: string; icon: string }> = {
  radosne:  { label: "Tajemnice radosne",  days: "Pon · Sob", color: "from-sky-900/60 to-sky-800/30",    border: "border-sky-700/40",    icon: "🌟" },
  bolesne:  { label: "Tajemnice bolesne",  days: "Wt · Pt",   color: "from-red-900/60 to-red-800/30",    border: "border-red-700/40",    icon: "✝" },
  chwalebne:{ label: "Tajemnice chwalebne",days: "Śr · Nd",   color: "from-amber-900/60 to-amber-800/30",border: "border-amber-700/40",  icon: "☀" },
  swietlne: { label: "Tajemnice światła",  days: "Czw",        color: "from-blue-900/60 to-blue-800/30",  border: "border-blue-700/40",   icon: "💡" },
};

export default function RozaniecPage() {
  const [appState, setAppState] = useState<AppState>("menu");
  const [todayMystery, setTodayMystery] = useState<MysteryType>("radosne");
  const [selectedType, setSelectedType] = useState<MysteryType>("radosne");
  const [mysteries, setMysteries] = useState<RosaryMystery[]>([]);
  const [allData, setAllData] = useState<Record<string, { mysteries: RosaryMystery[] }> | null>(null);
  const [selectedMystery, setSelectedMystery] = useState<RosaryMystery | null>(null);
  const [selectedMysteryNum, setSelectedMysteryNum] = useState(1);
  const [meditation, setMeditation] = useState("");
  const [streamingMeditation, setStreamingMeditation] = useState(false);
  const [completedDecades, setCompletedDecades] = useState<Set<number>>(new Set());
  const [communitySessions, setCommunitySessions] = useState<CommunitySession[]>([]);
  const [newIntention, setNewIntention] = useState("");
  const [creatingSession, setCreatingSession] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeMysteryType, setActiveMysteryType] = useState<MysteryType>("radosne");
  const streamRef = useRef<AbortController | null>(null);
  const meditationRef = useRef<HTMLDivElement>(null);

  const ws = useRosarySocket(activeSessionId);
  const { subscription, fetchStatus: fetchBilling } = useBillingStore();

  useEffect(() => { fetchBilling(); }, [fetchBilling]);

  useEffect(() => {
    api.get<{ mystery_types: Record<string, { mysteries: RosaryMystery[] }>; today: string }>("/api/v1/community/rosary/mysteries")
      .then((d) => {
        setAllData(d.mystery_types);
        const today = d.today as MysteryType;
        setTodayMystery(today);
        setSelectedType(today);
        setMysteries(d.mystery_types?.[today]?.mysteries || []);
      })
      .catch(() => {});
  }, []);

  const loadCommunity = useCallback(async () => {
    try {
      const data = await api.get<{ sessions: CommunitySession[] }>("/api/v1/community/rosary/community");
      setCommunitySessions(data.sessions || []);
    } catch {}
  }, []);

  const selectMysteryType = (type: MysteryType) => {
    setSelectedType(type);
    setMysteries(allData?.[type]?.mysteries || []);
    setCompletedDecades(new Set());
    setMeditation("");
    setAppState("mysteries");
  };

  const streamMeditation = async (mysteryType: MysteryType, mysteryNum: number) => {
    if (streamRef.current) streamRef.current.abort();
    const ctrl = new AbortController();
    streamRef.current = ctrl;
    setMeditation("");
    setStreamingMeditation(true);

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const res = await fetch("/api/v1/community/rosary/meditate/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ mystery_type: mysteryType, mystery_number: mysteryNum }),
        signal: ctrl.signal,
      });
      if (!res.ok || !res.body) { setStreamingMeditation(false); return; }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let text = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        text += decoder.decode(value, { stream: true });
        setMeditation(text);
        meditationRef.current?.scrollTo(0, meditationRef.current.scrollHeight);
      }
    } catch (e: unknown) {
      if ((e as { name?: string }).name !== "AbortError") setMeditation("Błąd połączenia.");
    } finally {
      setStreamingMeditation(false);
    }
  };

  const openMystery = (mystery: RosaryMystery) => {
    setSelectedMystery(mystery);
    setSelectedMysteryNum(mystery.number);
    setMeditation("");
    setAppState("decade");
  };

  const completeDecade = (num: number) => {
    setCompletedDecades((prev) => new Set([...prev, num]));
  };

  const createSession = async () => {
    setCreatingSession(true);
    try {
      await api.post("/api/v1/community/rosary/community", {
        mystery_type: selectedType,
        intention: newIntention || null,
      });
      setNewIntention("");
      await loadCommunity();
    } catch {} finally {
      setCreatingSession(false);
    }
  };

  const joinSession = async (session: CommunitySession) => {
    try {
      await api.post(`/api/v1/community/rosary/community/${session.id}/join`, {});
    } catch {}
    setActiveMysteryType(session.mystery_type as MysteryType);
    setActiveSessionId(session.id);
    setAppState("live");
  };

  const leaveSession = () => {
    ws.disconnect();
    setActiveSessionId(null);
    setAppState("community");
    loadCommunity();
  };

  // ── Menu ──────────────────────────────────────────────────────────────────
  if (appState === "menu") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-10 pb-24">
          <div className="text-center mb-8">
            <div className="text-5xl mb-3">📿</div>
            <h1 className="text-2xl font-bold text-[#d4af37] mb-1">Różaniec</h1>
            <p className="text-gray-400 text-sm">20 tajemnic · Medytacja AI · Wspólnota</p>
          </div>

          {todayMystery && (
            <div className="bg-[#d4af37]/10 border border-[#d4af37]/30 rounded-2xl p-4 mb-6">
              <div className="text-xs text-[#d4af37] mb-1">Dzisiaj modlimy się nad:</div>
              <div className="font-semibold text-white">{MYSTERY_META[todayMystery].label}</div>
              <div className="text-xs text-gray-500">{MYSTERY_META[todayMystery].days}</div>
            </div>
          )}

          <div className="space-y-3 mb-6">
            {(Object.keys(MYSTERY_META) as MysteryType[]).map((type) => {
              const meta = MYSTERY_META[type];
              const isToday = type === todayMystery;
              return (
                <button
                  key={type}
                  onClick={() => selectMysteryType(type)}
                  className={`w-full rounded-xl border ${meta.border} bg-gradient-to-r ${meta.color} p-4 text-left hover:scale-[1.01] transition-all`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{meta.icon}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white">{meta.label}</span>
                        {isToday && (
                          <span className="text-xs bg-[#d4af37] text-black px-2 py-0.5 rounded-full font-medium">
                            Dziś
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-400">{meta.days}</div>
                    </div>
                    <span className="text-gray-500 text-sm">5 tajemnic →</span>
                  </div>
                </button>
              );
            })}
          </div>

          <button
            onClick={() => { loadCommunity(); setAppState("community"); }}
            className="w-full bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl p-4 text-left transition-all"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">👥</span>
              <div>
                <div className="font-medium text-white">Różaniec wspólnotowy</div>
                <div className="text-xs text-gray-500">Dołącz do sesji z innymi</div>
              </div>
            </div>
          </button>
        </div>
      </main>
    );
  }

  // ── Mysteries list ────────────────────────────────────────────────────────
  if (appState === "mysteries") {
    const meta = MYSTERY_META[selectedType];
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("menu")} className="text-gray-400 hover:text-white">←</button>
            <div>
              <div className="text-xs text-gray-500">{meta.days}</div>
              <h1 className="text-xl font-bold text-[#d4af37]">{meta.label}</h1>
            </div>
          </div>

          <div className="flex gap-2 mb-6">
            {[1, 2, 3, 4, 5].map((n) => (
              <div
                key={n}
                className={`flex-1 h-1.5 rounded-full ${
                  completedDecades.has(n) ? "bg-[#d4af37]" : "bg-white/10"
                }`}
              />
            ))}
          </div>

          <div className="space-y-3">
            {mysteries.map((mystery) => {
              const done = completedDecades.has(mystery.number);
              return (
                <button
                  key={mystery.number}
                  onClick={() => openMystery(mystery)}
                  className={`w-full rounded-xl border p-4 text-left transition-all ${
                    done
                      ? "bg-[#d4af37]/10 border-[#d4af37]/30"
                      : "bg-white/5 border-white/10 hover:border-white/30"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 ${
                        done
                          ? "bg-[#d4af37] text-black"
                          : "bg-white/10 text-gray-400"
                      }`}
                    >
                      {done ? "✓" : mystery.number}
                    </div>
                    <div>
                      <div className="font-medium text-sm text-white">{mystery.title}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{mystery.scripture} · Owoc: {mystery.fruit}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {completedDecades.size === 5 && (
            <div className="mt-6 bg-[#d4af37]/10 border border-[#d4af37]/30 rounded-2xl p-4 text-center">
              <div className="text-3xl mb-2">🙏</div>
              <p className="text-[#d4af37] font-semibold">Różaniec ukończony!</p>
              <p className="text-xs text-gray-400 mt-1">«Różaniec jest modlitwą i rozważaniem» — Jan Paweł II</p>
            </div>
          )}
        </div>
      </main>
    );
  }

  // ── Decade / mystery detail ────────────────────────────────────────────────
  if (appState === "decade" && selectedMystery) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("mysteries")} className="text-gray-400 hover:text-white">←</button>
            <div>
              <div className="text-xs text-gray-500">{selectedMysteryNum}. Tajemnica</div>
              <h1 className="text-lg font-bold text-[#d4af37]">{selectedMystery.title}</h1>
            </div>
          </div>

          <div className="bg-white/5 rounded-2xl p-5 mb-4">
            <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
              <div>
                <span className="text-gray-500">Pismo Święte</span>
                <div className="text-[#d4af37]">{selectedMystery.scripture}</div>
              </div>
              <div>
                <span className="text-gray-500">Owoc tajemnicy</span>
                <div className="text-[#d4af37]">{selectedMystery.fruit}</div>
              </div>
            </div>
            <p className="text-sm text-gray-300 leading-relaxed italic">
              {selectedMystery.meditation}
            </p>
          </div>

          {/* Audio meditation (premium) */}
          <div className="mb-4">
            <PremiumAudioButton
              mysteryType={selectedType}
              mysteryNumber={selectedMysteryNum}
              isPremium={subscription?.is_premium ?? false}
            />
          </div>

          {!meditation && !streamingMeditation && (
            <button
              onClick={() => streamMeditation(selectedType, selectedMysteryNum)}
              className="w-full bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl py-3 text-sm text-gray-300 transition-all mb-4"
            >
              ✨ Poprowadź mnie przez medytację (tekst)
            </button>
          )}

          {(meditation || streamingMeditation) && (
            <div
              ref={meditationRef}
              className="bg-white/5 rounded-2xl p-5 mb-4 max-h-48 overflow-y-auto text-sm text-gray-200 leading-loose whitespace-pre-wrap"
            >
              {streamingMeditation && !meditation ? (
                <span className="text-gray-500 animate-pulse">Piszę medytację...</span>
              ) : meditation}
            </div>
          )}

          <div className="bg-white/5 rounded-xl p-4 mb-4 text-xs text-gray-400">
            <p className="font-medium text-gray-300 mb-1">Modlitwa dziesiątki:</p>
            <p>1× Ojcze Nasz → 10× Zdrowaś Maryjo → 1× Chwała Ojcu → Fatimska (O mój Jezu…)</p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => {
                completeDecade(selectedMysteryNum);
                const next = selectedMysteryNum < 5
                  ? mysteries.find((m) => m.number === selectedMysteryNum + 1)
                  : null;
                if (next) { setSelectedMystery(next); setSelectedMysteryNum(next.number); setMeditation(""); }
                else setAppState("mysteries");
              }}
              className="flex-1 bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors"
            >
              {selectedMysteryNum < 5 ? "Odmówiono → Następna" : "Odmówiono ✓"}
            </button>
          </div>
        </div>
      </main>
    );
  }

  // ── Community sessions ─────────────────────────────────────────────────────
  if (appState === "community") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("menu")} className="text-gray-400 hover:text-white">←</button>
            <h1 className="text-xl font-bold text-[#d4af37]">Różaniec wspólnotowy</h1>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-2xl p-4 mb-6">
            <p className="text-sm font-medium text-gray-200 mb-3">Rozpocznij nową sesję</p>
            <div className="flex gap-2 mb-3">
              {(Object.keys(MYSTERY_META) as MysteryType[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setSelectedType(t)}
                  className={`flex-1 text-xs py-2 rounded-lg border transition-all ${
                    selectedType === t
                      ? "bg-[#d4af37]/20 border-[#d4af37]/50 text-[#d4af37]"
                      : "border-white/10 text-gray-500"
                  }`}
                >
                  {MYSTERY_META[t].icon}
                </button>
              ))}
            </div>
            <input
              type="text"
              value={newIntention}
              onChange={(e) => setNewIntention(e.target.value)}
              placeholder="Intencja sesji (opcjonalnie)"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37] mb-3"
            />
            <button
              onClick={createSession}
              disabled={creatingSession}
              className="w-full bg-[#d4af37] text-black font-semibold py-2.5 rounded-xl hover:bg-[#c9a227] transition-colors disabled:opacity-50"
            >
              {creatingSession ? "Tworzę..." : "📿 Zaproś do Różańca"}
            </button>
          </div>

          <h3 className="text-sm font-semibold text-gray-400 mb-3">
            Otwarte sesje ({communitySessions.length})
          </h3>
          {communitySessions.length === 0 ? (
            <p className="text-gray-600 text-sm text-center py-6">
              Brak otwartych sesji. Stwórz pierwszą!
            </p>
          ) : (
            <div className="space-y-3">
              {communitySessions.map((s) => {
                const meta = MYSTERY_META[s.mystery_type as MysteryType];
                return (
                  <div key={s.id} className={`rounded-xl border ${meta?.border || "border-white/10"} bg-gradient-to-r ${meta?.color || "from-gray-900/40 to-gray-800/20"} p-4`}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-medium text-sm">{meta?.label || s.mystery_type}</div>
                      <div className="text-xs text-gray-500">👥 {s.participant_count}</div>
                    </div>
                    {s.intention && <p className="text-xs text-gray-400 mb-2">{s.intention}</p>}
                    <button
                      onClick={() => joinSession(s)}
                      className="text-xs bg-white/10 hover:bg-white/20 text-white px-3 py-1.5 rounded-lg transition-colors"
                    >
                      Dołącz i módl się
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    );
  }

  // ── Live community session ─────────────────────────────────────────────────
  if (appState === "live") {
    const meta = MYSTERY_META[activeMysteryType] || MYSTERY_META.radosne;
    const wsDecades = new Set(ws.decadesCompleted);
    const allDone = ws.decadesCompleted.length === 5;

    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          {/* Header */}
          <div className="flex items-center gap-3 mb-6">
            <button onClick={leaveSession} className="text-gray-400 hover:text-white">←</button>
            <div className="flex-1">
              <h1 className="text-xl font-bold text-[#d4af37]">{meta.label}</h1>
              <div className="text-xs text-gray-500">Sesja wspólnotowa</div>
            </div>
            {/* Connection indicator */}
            <div className="flex items-center gap-1.5">
              <div
                className={`w-2 h-2 rounded-full ${
                  ws.connected ? "bg-green-400 animate-pulse" : "bg-gray-600"
                }`}
              />
              <span className="text-xs text-gray-500">
                {ws.connected ? "Online" : "Łączenie…"}
              </span>
            </div>
          </div>

          {/* Participants counter */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-4 mb-5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">👥</span>
              <div>
                <div className="text-sm font-semibold text-white">
                  {ws.participants} {ws.participants === 1 ? "uczestnik" : ws.participants < 5 ? "uczestników" : "uczestników"}
                </div>
                <div className="text-xs text-gray-500">modli się teraz</div>
              </div>
            </div>
            {ws.lastDecadeBy && (
              <div className="text-right">
                <div className="text-xs text-gray-500">Ostatnio odmówił</div>
                <div className="text-xs text-[#d4af37] font-mono truncate max-w-[100px]">
                  {ws.lastDecadeBy.slice(0, 8)}…
                </div>
              </div>
            )}
          </div>

          {/* Error banner */}
          {ws.error && (
            <div className="bg-red-900/30 border border-red-700/40 rounded-xl p-3 mb-4 text-xs text-red-300">
              {ws.error}
            </div>
          )}

          {/* Progress bar */}
          <div className="flex gap-2 mb-4">
            {[1, 2, 3, 4, 5].map((n) => (
              <div
                key={n}
                className={`flex-1 h-1.5 rounded-full transition-colors duration-500 ${
                  wsDecades.has(n) ? "bg-[#d4af37]" : "bg-white/10"
                }`}
              />
            ))}
          </div>

          {/* Decade buttons */}
          <div className="space-y-3 mb-6">
            {[1, 2, 3, 4, 5].map((n) => {
              const done = wsDecades.has(n);
              return (
                <button
                  key={n}
                  disabled={done || !ws.connected}
                  onClick={() => ws.sendDecade(n)}
                  className={`w-full rounded-xl border p-4 text-left transition-all ${
                    done
                      ? "bg-[#d4af37]/10 border-[#d4af37]/30 cursor-default"
                      : ws.connected
                        ? "bg-white/5 border-white/10 hover:border-[#d4af37]/40 hover:bg-white/10"
                        : "bg-white/5 border-white/5 opacity-50 cursor-not-allowed"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${
                        done ? "bg-[#d4af37] text-black" : "bg-white/10 text-gray-400"
                      }`}
                    >
                      {done ? "✓" : n}
                    </div>
                    <div className="flex-1">
                      <div className={`text-sm font-medium ${done ? "text-[#d4af37]" : "text-white"}`}>
                        {n}. dziesiątka
                      </div>
                      <div className="text-xs text-gray-500">
                        {done ? "Odmówiona przez wspólnotę" : "Dotknij, gdy odmówisz"}
                      </div>
                    </div>
                    {!done && ws.connected && (
                      <span className="text-xs text-gray-600">📿</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Completion message */}
          {allDone && (
            <div className="bg-[#d4af37]/10 border border-[#d4af37]/30 rounded-2xl p-5 text-center">
              <div className="text-4xl mb-2">🙏</div>
              <p className="text-[#d4af37] font-semibold text-lg">Wspólnotowy Różaniec ukończony!</p>
              <p className="text-xs text-gray-400 mt-2">
                «Gdziekolwiek dwaj albo trzej są zebrani w imię moje, tam jestem pośród nich.» — Mt 18,20
              </p>
            </div>
          )}

          {/* Prayer instructions */}
          {!allDone && (
            <div className="bg-white/5 rounded-xl p-4 text-xs text-gray-400">
              <p className="font-medium text-gray-300 mb-1">Modlitwa dziesiątki:</p>
              <p>1× Ojcze Nasz → 10× Zdrowaś Maryjo → 1× Chwała Ojcu → Fatimska</p>
            </div>
          )}
        </div>
      </main>
    );
  }

  return null;
}
