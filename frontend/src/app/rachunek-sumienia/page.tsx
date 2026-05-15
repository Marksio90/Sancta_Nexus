"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";

// ── Typy ─────────────────────────────────────────────────────────────────────

interface PhaseMeta {
  title: string;
  subtitle: string;
  icon: string;
  prompt_intro: string;
}

interface StartResponse {
  session_id: string;
  current_phase: string;
  phase_meta: PhaseMeta;
  disclaimer: string;
}

interface StepResponse {
  session_id: string;
  phase_completed: string;
  ai_response: string;
  next_phase: string | null;
  next_phase_meta: PhaseMeta | null;
  is_final: boolean;
  disclaimer: string;
}

interface CompleteResponse {
  session_id: string;
  summary: string;
  journal_entry_id: string | null;
  message: string;
  disclaimer: string;
}

type AppState = "intro" | "intention" | "phase" | "ai_response" | "complete";

const PHASE_ORDER = ["gratitude", "petition", "review", "response", "resolution"];
const PHASE_COLORS: Record<string, string> = {
  gratitude:  "from-amber-900/30 to-yellow-900/20 border-amber-700/40",
  petition:   "from-blue-900/30 to-indigo-900/20 border-blue-700/40",
  review:     "from-purple-900/30 to-violet-900/20 border-purple-700/40",
  response:   "from-rose-900/30 to-red-900/20 border-rose-700/40",
  resolution: "from-green-900/30 to-emerald-900/20 border-green-700/40",
};

const PHASE_STEP_LABELS: Record<string, string> = {
  gratitude:  "1 / 5",
  petition:   "2 / 5",
  review:     "3 / 5",
  response:   "4 / 5",
  resolution: "5 / 5",
};

// ── Komponent główny ──────────────────────────────────────────────────────────

export default function RachunekSumieniaPage() {
  const [appState, setAppState] = useState<AppState>("intro");
  const [intention, setIntention] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string>("gratitude");
  const [currentMeta, setCurrentMeta] = useState<PhaseMeta | null>(null);
  const [reflection, setReflection] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [nextPhaseMeta, setNextPhaseMeta] = useState<PhaseMeta | null>(null);
  const [nextPhase, setNextPhase] = useState<string | null>(null);
  const [isFinal, setIsFinal] = useState(false);
  const [disclaimer, setDisclaimer] = useState("");
  const [completeData, setCompleteData] = useState<CompleteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveToJournal, setSaveToJournal] = useState(false);
  const [phasesCompleted, setPhasesCompleted] = useState<string[]>([]);

  const startExamen = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.post<StartResponse>("/api/v1/examen/start", {
        intention: intention.trim() || null,
      });
      setSessionId(data.session_id);
      setCurrentPhase(data.current_phase);
      setCurrentMeta(data.phase_meta);
      setDisclaimer(data.disclaimer);
      setReflection("");
      setAppState("phase");
    } catch {
      setError("Nie udało się rozpocząć sesji. Spróbuj ponownie.");
    } finally {
      setLoading(false);
    }
  }, [intention]);

  const submitStep = useCallback(async () => {
    if (!sessionId || !reflection.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.post<StepResponse>("/api/v1/examen/step", {
        session_id: sessionId,
        reflection: reflection.trim(),
      });
      setAiResponse(data.ai_response);
      setNextPhaseMeta(data.next_phase_meta);
      setNextPhase(data.next_phase);
      setIsFinal(data.is_final);
      setPhasesCompleted((prev) => [...prev, data.phase_completed]);
      setAppState("ai_response");
    } catch {
      setError("Nie udało się zapisać refleksji. Spróbuj ponownie.");
    } finally {
      setLoading(false);
    }
  }, [sessionId, reflection]);

  const goToNextPhase = useCallback(() => {
    if (isFinal) {
      setAppState("complete");
      return;
    }
    if (nextPhase && nextPhaseMeta) {
      setCurrentPhase(nextPhase);
      setCurrentMeta(nextPhaseMeta);
      setReflection("");
      setAiResponse("");
      setAppState("phase");
    }
  }, [isFinal, nextPhase, nextPhaseMeta]);

  const completeExamen = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.post<CompleteResponse>("/api/v1/examen/complete", {
        session_id: sessionId,
        save_to_journal: saveToJournal,
      });
      setCompleteData(data);
    } catch {
      setError("Nie udało się zakończyć sesji.");
    } finally {
      setLoading(false);
    }
  }, [sessionId, saveToJournal]);

  // ── Ekran wstępny ───────────────────────────────────────────────────────────
  if (appState === "intro") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex flex-col items-center justify-center px-4 py-12">
        <div className="max-w-lg w-full text-center space-y-6">
          <div className="text-6xl mb-2">🕯</div>
          <h1 className="text-3xl font-bold text-[#d4af37] tracking-wide">
            Rachunek Sumienia
          </h1>
          <p className="text-gray-400 text-sm leading-relaxed">
            Ignacjański Examen — 5 kroków refleksji nad Bożą obecnością w Twoim dniu.
            Wieczorna modlitwa, która porządkuje serce.
          </p>

          {/* Kroki */}
          <div className="grid grid-cols-5 gap-2 mt-4">
            {[
              { icon: "🙏", label: "Wdzięczność" },
              { icon: "✨", label: "Prośba" },
              { icon: "🔍", label: "Przegląd" },
              { icon: "❤️", label: "Odpowiedź" },
              { icon: "🌅", label: "Postanowienie" },
            ].map((step, i) => (
              <div key={i} className="flex flex-col items-center gap-1">
                <div className="w-10 h-10 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-lg">
                  {step.icon}
                </div>
                <span className="text-xs text-gray-500 text-center leading-tight">{step.label}</span>
              </div>
            ))}
          </div>

          <div className="text-xs text-gray-600 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-left leading-relaxed mt-2">
            ℹ️ Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy.
            Nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty.
          </div>

          <button
            onClick={() => setAppState("intention")}
            className="w-full bg-[#d4af37] text-black font-bold py-4 rounded-2xl text-lg hover:bg-[#c9a227] transition-colors mt-2"
          >
            Rozpocznij Rachunek Sumienia
          </button>
        </div>
      </main>
    );
  }

  // ── Intencja ────────────────────────────────────────────────────────────────
  if (appState === "intention") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex flex-col items-center justify-center px-4 py-12">
        <div className="max-w-lg w-full space-y-6">
          <button
            onClick={() => setAppState("intro")}
            className="text-gray-500 hover:text-white text-sm"
          >
            ← Powrót
          </button>
          <div className="text-center">
            <div className="text-4xl mb-3">🙏</div>
            <h2 className="text-xl font-bold text-[#d4af37]">Intencja (opcjonalnie)</h2>
            <p className="text-gray-400 text-sm mt-2">
              W jakiej intencji odmawiasz dziś Rachunek Sumienia?
            </p>
          </div>

          <textarea
            value={intention}
            onChange={(e) => setIntention(e.target.value)}
            maxLength={300}
            rows={3}
            placeholder="Np. W intencji mojej rodziny. Za łaskę rozeznania. Dziękując za dziś..."
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37] resize-none"
          />

          <button
            onClick={startExamen}
            disabled={loading}
            className="w-full bg-[#d4af37] text-black font-bold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors disabled:opacity-60"
          >
            {loading ? "Przygotowuję sesję..." : "Rozpocznij →"}
          </button>

          {error && <p className="text-red-400 text-sm text-center">{error}</p>}
        </div>
      </main>
    );
  }

  // ── Krok Rachunku Sumienia ─────────────────────────────────────────────────
  if (appState === "phase" && currentMeta) {
    const colorClass = PHASE_COLORS[currentPhase] || "from-gray-900/40 to-gray-800/20 border-white/10";
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white px-4 py-8">
        <div className="max-w-lg mx-auto space-y-5">
          {/* Nagłówek z postępem */}
          <div className="flex items-center justify-between">
            <div className="flex gap-1">
              {PHASE_ORDER.map((p) => (
                <div
                  key={p}
                  className={`h-1.5 rounded-full transition-all ${
                    phasesCompleted.includes(p)
                      ? "bg-[#d4af37] w-8"
                      : p === currentPhase
                      ? "bg-[#d4af37]/60 w-8"
                      : "bg-white/10 w-5"
                  }`}
                />
              ))}
            </div>
            <span className="text-xs text-gray-500">{PHASE_STEP_LABELS[currentPhase]}</span>
          </div>

          {/* Karta kroku */}
          <div className={`bg-gradient-to-br ${colorClass} border rounded-2xl p-6`}>
            <div className="text-4xl mb-3">{currentMeta.icon}</div>
            <h2 className="text-xl font-bold text-[#d4af37] mb-1">{currentMeta.title}</h2>
            <p className="text-xs text-gray-400 mb-4">{currentMeta.subtitle}</p>
            <p className="text-sm text-gray-200 leading-relaxed">{currentMeta.prompt_intro}</p>
          </div>

          {/* Pole refleksji */}
          <div>
            <label className="text-xs text-gray-400 mb-2 block">Twoja refleksja</label>
            <textarea
              value={reflection}
              onChange={(e) => setReflection(e.target.value)}
              maxLength={2000}
              rows={6}
              autoFocus
              placeholder="Pisz swobodnie — nikt tego nie ocenia. To rozmowa z Bogiem."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37] resize-none leading-relaxed"
            />
            <div className="text-right text-xs text-gray-600 mt-1">{reflection.length}/2000</div>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            onClick={submitStep}
            disabled={loading || !reflection.trim()}
            className="w-full bg-[#d4af37] text-black font-bold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors disabled:opacity-50"
          >
            {loading ? "Przetwarzam..." : "Dalej →"}
          </button>

          {/* Disclaimer */}
          <p className="text-xs text-gray-600 text-center leading-relaxed">{disclaimer}</p>
        </div>
      </main>
    );
  }

  // ── Odpowiedź AI ───────────────────────────────────────────────────────────
  if (appState === "ai_response") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white px-4 py-8">
        <div className="max-w-lg mx-auto space-y-5">
          {/* Postęp */}
          <div className="flex gap-1">
            {PHASE_ORDER.map((p) => (
              <div
                key={p}
                className={`h-1.5 rounded-full transition-all ${
                  phasesCompleted.includes(p) ? "bg-[#d4af37] w-8" : "bg-white/10 w-5"
                }`}
              />
            ))}
          </div>

          <div className="text-center">
            <div className="text-sm text-gray-500 mb-1">Odpowiedź asystenta refleksji</div>
          </div>

          {/* Odpowiedź AI */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
            <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">{aiResponse}</p>
          </div>

          {/* Disclaimer */}
          <div className="text-xs text-gray-600 bg-white/5 border border-white/10 rounded-xl px-4 py-3 leading-relaxed">
            ℹ️ {disclaimer}
          </div>

          {/* Następny krok lub zakończenie */}
          {isFinal ? (
            <button
              onClick={goToNextPhase}
              className="w-full bg-[#d4af37] text-black font-bold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors"
            >
              🌅 Zakończ Rachunek Sumienia
            </button>
          ) : (
            <div className="space-y-3">
              {nextPhaseMeta && (
                <div className="text-center text-xs text-gray-500">
                  Następny krok: <span className="text-[#d4af37]">{nextPhaseMeta.icon} {nextPhaseMeta.title}</span>
                </div>
              )}
              <button
                onClick={goToNextPhase}
                className="w-full bg-[#d4af37] text-black font-bold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors"
              >
                Następny krok →
              </button>
            </div>
          )}
        </div>
      </main>
    );
  }

  // ── Zakończenie ────────────────────────────────────────────────────────────
  if (appState === "complete") {
    if (completeData) {
      return (
        <main className="min-h-screen bg-[#0d0b1a] text-white flex flex-col items-center justify-center px-4 py-12">
          <div className="max-w-lg w-full text-center space-y-5">
            <div className="text-6xl">✝️</div>
            <h2 className="text-2xl font-bold text-[#d4af37]">Rachunek zakończony</h2>
            <p className="text-gray-400 text-sm">{completeData.message}</p>

            {completeData.journal_entry_id && (
              <div className="bg-green-900/20 border border-green-700/30 rounded-xl px-4 py-3 text-sm text-green-300">
                ✓ Zapisano do dziennika duchowego
              </div>
            )}

            <div className="text-xs text-gray-600 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-left leading-relaxed">
              ℹ️ {completeData.disclaimer}
            </div>

            <div className="flex flex-col gap-3 pt-2">
              <a
                href="/dziennik"
                className="w-full bg-white/5 border border-white/10 text-gray-300 py-3 rounded-xl text-sm text-center hover:bg-white/10 transition-all"
              >
                Przejdź do Dziennika
              </a>
              <button
                onClick={() => {
                  setAppState("intro");
                  setSessionId(null);
                  setCurrentPhase("gratitude");
                  setCurrentMeta(null);
                  setReflection("");
                  setAiResponse("");
                  setPhasesCompleted([]);
                  setCompleteData(null);
                  setIntention("");
                  setSaveToJournal(false);
                }}
                className="w-full bg-[#d4af37] text-black font-bold py-3 rounded-xl text-sm hover:bg-[#c9a227] transition-colors"
              >
                Nowy Rachunek Sumienia
              </button>
            </div>
          </div>
        </main>
      );
    }

    // Pytanie o zapis do dziennika (przed wywołaniem API complete)
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex flex-col items-center justify-center px-4 py-12">
        <div className="max-w-lg w-full space-y-6">
          <div className="text-center">
            <div className="text-5xl mb-3">🌅</div>
            <h2 className="text-xl font-bold text-[#d4af37]">Zakończ Rachunek Sumienia</h2>
            <p className="text-gray-400 text-sm mt-2">
              Ukończyłeś wszystkie 5 kroków ignacjańskiego Examen. Chwała Bogu!
            </p>
          </div>

          <div className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-xl p-4">
            <input
              type="checkbox"
              id="saveJournal"
              checked={saveToJournal}
              onChange={(e) => setSaveToJournal(e.target.checked)}
              className="w-4 h-4 accent-[#d4af37]"
            />
            <label htmlFor="saveJournal" className="text-sm text-gray-300 cursor-pointer">
              Zapisz ten Rachunek do mojego Dziennika duchowego
            </label>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            onClick={completeExamen}
            disabled={loading}
            className="w-full bg-[#d4af37] text-black font-bold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors disabled:opacity-60"
          >
            {loading ? "Zapisuję..." : "Zakończ ✓"}
          </button>
        </div>
      </main>
    );
  }

  return null;
}
