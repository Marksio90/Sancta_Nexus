"use client";

import { useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SESSION_ICONS = ["⛪", "❤", "🗣", "🌸", "👶", "🙏", "📱", "🗺"];

type AppState = "loading" | "list" | "session" | "chat" | "reflection";

export default function MalzenstwoPage() {
  const [appState, setAppState] = useState<AppState>("list");
  const [program, setProgram] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<any>(null);
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [reflection, setReflection] = useState("");
  const [loadingReflection, setLoadingReflection] = useState(false);
  const [programLoaded, setProgramLoaded] = useState(false);

  const loadProgram = useCallback(async () => {
    if (programLoaded) return;
    setAppState("loading");
    try {
      const res = await fetch(`${API}/api/v1/sacraments/marriage/program`);
      const data = await res.json();
      setProgram(data.sessions || []);
      setProgramLoaded(true);
    } catch {
      setProgram([]);
    } finally {
      setAppState("list");
    }
  }, [programLoaded]);

  const openSession = useCallback(
    async (session: any) => {
      setSelectedSession(session);
      setMessages([
        {
          role: "assistant",
          content: `Witam w sesji **${session.title}** — *${session.subtitle}*.\n\n${session.key_questions[0]}`,
        },
      ]);
      setReflection("");
      setAppState("session");
    },
    []
  );

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    const userMsg = input.trim();
    setInput("");
    setSending(true);

    const newMessages = [...messages, { role: "user" as const, content: userMsg }];
    setMessages(newMessages);

    try {
      const res = await fetch(`${API}/api/v1/sacraments/marriage/discuss`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg,
          session_id: selectedSession?.session_id,
          conversation_history: newMessages.slice(-6).map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });
      const data = await res.json();
      setMessages([
        ...newMessages,
        { role: "assistant", content: data.response || "..." },
      ]);
    } catch {
      setMessages([
        ...newMessages,
        {
          role: "assistant",
          content: "Przepraszam, wystąpił problem z połączeniem.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const loadReflection = async () => {
    if (!selectedSession) return;
    setLoadingReflection(true);
    setAppState("reflection");
    try {
      const res = await fetch(
        `${API}/api/v1/sacraments/marriage/reflection/${selectedSession.session_id}`
      );
      const data = await res.json();
      setReflection(data.reflection || "");
    } catch {
      setReflection("Nie udało się załadować refleksji.");
    } finally {
      setLoadingReflection(false);
    }
  };

  // Load program on mount
  if (!programLoaded && appState === "list") {
    loadProgram();
  }

  // ── List ──────────────────────────────────────────────────────────────────
  if (appState === "list" || appState === "loading") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-10 pb-24">
          <div className="text-center mb-8">
            <div className="text-5xl mb-3">💍</div>
            <h1 className="text-2xl font-bold text-[#d4af37] mb-1">
              Przygotowanie do małżeństwa
            </h1>
            <p className="text-gray-400 text-sm">
              8 spotkań dla narzeczonych · Teologia Ciała · Amoris Laetitia
            </p>
          </div>

          {appState === "loading" ? (
            <div className="text-center text-gray-500 py-10 animate-pulse">
              Ładuję program...
            </div>
          ) : program.length === 0 ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                <div
                  key={n}
                  className="bg-white/5 border border-white/10 rounded-xl p-4 animate-pulse h-20"
                />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {program.map((session, idx) => (
                <button
                  key={session.session_id}
                  onClick={() => openSession(session)}
                  className="w-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-rose-600/50 rounded-xl p-4 text-left transition-all"
                >
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">
                      {SESSION_ICONS[idx] || "🙏"}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-xs text-gray-500">
                          Sesja {session.number}
                        </span>
                        <span className="text-xs text-gray-600">
                          {session.duration_hours}h
                        </span>
                      </div>
                      <div className="text-sm font-semibold text-white">
                        {session.title}
                      </div>
                      <div className="text-xs text-rose-400">
                        {session.subtitle}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </main>
    );
  }

  // ── Session detail ─────────────────────────────────────────────────────────
  if (appState === "session" && selectedSession) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button
              onClick={() => setAppState("list")}
              className="text-gray-400 hover:text-white"
            >
              ←
            </button>
            <div>
              <div className="text-xs text-gray-500">
                Sesja {selectedSession.number}
              </div>
              <h1 className="text-xl font-bold text-[#d4af37]">
                {selectedSession.title}
              </h1>
            </div>
          </div>

          {/* Info cards */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="bg-white/5 rounded-xl p-3">
              <div className="text-xs text-gray-500 mb-1">Pismo Święte</div>
              {selectedSession.scripture?.map((s: string) => (
                <div key={s} className="text-xs text-[#d4af37]">
                  {s}
                </div>
              ))}
            </div>
            <div className="bg-white/5 rounded-xl p-3">
              <div className="text-xs text-gray-500 mb-1">Katechizm</div>
              {selectedSession.ccc_refs?.map((r: string) => (
                <div key={r} className="text-xs text-[#d4af37]">
                  KKK {r}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-rose-900/20 border border-rose-700/30 rounded-xl p-4 mb-6">
            <div className="text-xs text-gray-400 mb-1">Kluczowy dokument</div>
            <div className="text-sm text-rose-300">
              {selectedSession.key_document}
            </div>
          </div>

          {/* Couple exercise */}
          <div className="bg-white/5 rounded-xl p-4 mb-6">
            <div className="text-xs font-semibold text-[#d4af37] mb-2">
              ✍ Ćwiczenie dla pary
            </div>
            <p className="text-sm text-gray-300">
              {selectedSession.couple_exercise}
            </p>
          </div>

          {/* Prayer */}
          <div className="bg-purple-900/20 border border-purple-700/30 rounded-xl p-4 mb-6 italic text-sm text-gray-300">
            🙏 {selectedSession.prayer}
          </div>

          {/* Key questions */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">
              Pytania do omówienia
            </h3>
            {selectedSession.key_questions?.map((q: string, i: number) => (
              <div
                key={i}
                className="flex items-start gap-2 mb-2 text-sm text-gray-400"
              >
                <span className="text-[#d4af37] mt-0.5">{i + 1}.</span>
                {q}
              </div>
            ))}
          </div>

          {/* Conversation */}
          <div className="bg-white/5 rounded-2xl p-4 mb-4 max-h-64 overflow-y-auto space-y-3">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`text-sm leading-relaxed ${
                  m.role === "user"
                    ? "text-right text-white/90"
                    : "text-left text-gray-300"
                }`}
              >
                <span
                  className={`inline-block rounded-xl px-3 py-2 text-xs ${
                    m.role === "user"
                      ? "bg-[#d4af37]/20 text-[#d4af37]"
                      : "bg-white/5"
                  }`}
                >
                  {m.content}
                </span>
              </div>
            ))}
            {sending && (
              <div className="text-xs text-gray-500 animate-pulse">
                Doradca pisze...
              </div>
            )}
          </div>

          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Zapytaj lub podziel się refleksją..."
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-rose-600/50"
            />
            <button
              onClick={sendMessage}
              disabled={sending || !input.trim()}
              className="bg-rose-700/60 hover:bg-rose-700/80 text-white px-4 py-3 rounded-xl text-sm font-medium transition-colors disabled:opacity-40"
            >
              Wyślij
            </button>
          </div>

          <button
            onClick={loadReflection}
            className="w-full bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors"
          >
            ✨ Medytacja do tej sesji
          </button>
        </div>
      </main>
    );
  }

  // ── Reflection ─────────────────────────────────────────────────────────────
  if (appState === "reflection") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button
              onClick={() => setAppState("session")}
              className="text-gray-400 hover:text-white"
            >
              ←
            </button>
            <h1 className="text-lg font-bold text-[#d4af37]">
              Medytacja — {selectedSession?.title}
            </h1>
          </div>

          <div className="bg-rose-900/10 border border-rose-700/20 rounded-2xl p-6 text-sm text-gray-200 leading-loose whitespace-pre-wrap min-h-[200px]">
            {loadingReflection ? (
              <span className="text-gray-500 animate-pulse">
                Generuję medytację...
              </span>
            ) : (
              reflection
            )}
          </div>

          {!loadingReflection && (
            <button
              onClick={() => setAppState("session")}
              className="w-full mt-6 bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors"
            >
              Wróć do sesji
            </button>
          )}
        </div>
      </main>
    );
  }

  return null;
}
