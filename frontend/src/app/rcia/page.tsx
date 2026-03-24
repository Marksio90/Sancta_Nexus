"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STAGE_META: Record<
  string,
  { label: string; color: string; borderColor: string; icon: string; description: string }
> = {
  precatechumenate: {
    label: "Ewangelizacja wstępna",
    color: "from-sky-900/60 to-sky-800/40",
    borderColor: "border-sky-700/50",
    icon: "🌱",
    description: "Pierwsze pytania wiary i poznawanie Jezusa Chrystusa",
  },
  catechumenate: {
    label: "Katechumenat",
    color: "from-blue-900/60 to-blue-800/40",
    borderColor: "border-blue-700/50",
    icon: "📖",
    description: "Systematyczna formacja w wierze, modlitwie i życiu moralnym",
  },
  purification: {
    label: "Oczyszczenie i oświecenie",
    color: "from-violet-900/60 to-violet-800/40",
    borderColor: "border-violet-700/50",
    icon: "🕯",
    description: "Wielkopostne przygotowanie przez skrutinia i Symbole wiary",
  },
  mystagogia: {
    label: "Mistagogia",
    color: "from-amber-900/60 to-amber-800/40",
    borderColor: "border-amber-700/50",
    icon: "🌅",
    description: "Pogłębianie tajemnicy sakramentów po Wielkanocy",
  },
};

type AppState = "list" | "session" | "chat" | "reflection";

export default function RCIAPage() {
  const [appState, setAppState] = useState<AppState>("list");
  const [curriculum, setCurriculum] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<any>(null);
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [reflection, setReflection] = useState("");
  const [loadingReflection, setLoadingReflection] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/v1/sacraments/rcia/curriculum`)
      .then((r) => r.json())
      .then((d) => setCurriculum(d.stages || []))
      .catch(() => setCurriculum([]));
  }, []);

  const openSession = (session: any) => {
    setSelectedSession(session);
    setMessages([
      {
        role: "assistant",
        content: `Witaj w sesji **${session.title_pl}**.\n\n${session.summary}\n\nKluczowe pytanie: *${session.key_question}*`,
      },
    ]);
    setReflection("");
    setAppState("session");
  };

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    const userMsg = input.trim();
    setInput("");
    setSending(true);

    const newMessages = [...messages, { role: "user" as const, content: userMsg }];
    setMessages(newMessages);

    try {
      const res = await fetch(`${API}/api/v1/sacraments/rcia/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMsg,
          session_id: selectedSession?.session_id,
          conversation_history: newMessages.slice(-6).map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });
      const data = await res.json();
      setMessages([...newMessages, { role: "assistant", content: data.answer || "..." }]);
    } catch {
      setMessages([...newMessages, { role: "assistant", content: "Przepraszam, błąd połączenia." }]);
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
        `${API}/api/v1/sacraments/rcia/reflection/${selectedSession.session_id}`
      );
      const data = await res.json();
      setReflection(data.reflection || "");
    } catch {
      setReflection("Nie udało się załadować refleksji.");
    } finally {
      setLoadingReflection(false);
    }
  };

  if (appState === "list") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-10 pb-24">
          <div className="text-center mb-8">
            <div className="text-5xl mb-3">🕊</div>
            <h1 className="text-2xl font-bold text-[#d4af37] mb-1">
              RCIA — Droga do wiary
            </h1>
            <p className="text-gray-400 text-sm">
              Rite of Christian Initiation of Adults · 14 sesji · 4 etapy
            </p>
          </div>

          {curriculum.length === 0 ? (
            <div className="text-center text-gray-500 py-10 animate-pulse">
              Ładuję program...
            </div>
          ) : (
            <div className="space-y-6">
              {curriculum.map((stage: any) => {
                const meta = STAGE_META[stage.stage] || {
                  label: stage.stage,
                  color: "from-gray-900/60 to-gray-800/40",
                  borderColor: "border-gray-700/50",
                  icon: "📚",
                  description: "",
                };
                return (
                  <div key={stage.stage}>
                    {/* Stage header */}
                    <div
                      className={`rounded-2xl border ${meta.borderColor} bg-gradient-to-r ${meta.color} p-4 mb-3`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{meta.icon}</span>
                        <div>
                          <h2 className="font-semibold text-white">
                            {meta.label}
                          </h2>
                          <p className="text-xs text-gray-400">
                            {meta.description}
                          </p>
                        </div>
                        <span className="ml-auto text-xs text-gray-500">
                          {stage.session_count} sesji
                        </span>
                      </div>
                    </div>

                    {/* Sessions */}
                    <div className="space-y-2 pl-2">
                      {stage.sessions?.map((session: any) => (
                        <button
                          key={session.session_id}
                          onClick={() => openSession(session)}
                          className="w-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-blue-600/40 rounded-xl p-3 text-left transition-all"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-medium text-white">
                                {session.title_pl}
                              </div>
                              <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                                {session.summary}
                              </div>
                            </div>
                            <span className="text-xs text-gray-600 whitespace-nowrap">
                              #{session.session_number}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    );
  }

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
              <div className="text-xs text-gray-500">RCIA · Sesja {selectedSession.session_number}</div>
              <h1 className="text-xl font-bold text-[#d4af37]">
                {selectedSession.title_pl}
              </h1>
            </div>
          </div>

          {/* Scripture & CCC */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-white/5 rounded-xl p-3">
              <div className="text-xs text-gray-500 mb-1">Pismo Święte</div>
              {selectedSession.scripture?.map((s: string) => (
                <div key={s} className="text-xs text-[#d4af37]">{s}</div>
              ))}
            </div>
            <div className="bg-white/5 rounded-xl p-3">
              <div className="text-xs text-gray-500 mb-1">Katechizm</div>
              {selectedSession.ccc_refs?.map((r: string) => (
                <div key={r} className="text-xs text-[#d4af37]">KKK {r}</div>
              ))}
            </div>
          </div>

          {/* Prayer suggestion */}
          <div className="bg-blue-900/20 border border-blue-700/30 rounded-xl p-4 mb-4 italic text-sm text-gray-300">
            🙏 {selectedSession.prayer_suggestion}
          </div>

          {/* Chat */}
          <div className="bg-white/5 rounded-2xl p-4 mb-4 max-h-72 overflow-y-auto space-y-3">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`text-sm ${m.role === "user" ? "text-right" : "text-left"}`}
              >
                <span
                  className={`inline-block rounded-xl px-3 py-2 text-xs leading-relaxed ${
                    m.role === "user"
                      ? "bg-[#d4af37]/20 text-[#d4af37]"
                      : "bg-white/5 text-gray-300"
                  }`}
                >
                  {m.content}
                </span>
              </div>
            ))}
            {sending && (
              <div className="text-xs text-gray-500 animate-pulse">
                Katechista odpowiada...
              </div>
            )}
          </div>

          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Zadaj pytanie katechisty..."
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-600/50"
            />
            <button
              onClick={sendMessage}
              disabled={sending || !input.trim()}
              className="bg-blue-700/60 hover:bg-blue-700/80 text-white px-4 py-3 rounded-xl text-sm transition-colors disabled:opacity-40"
            >
              →
            </button>
          </div>

          <button
            onClick={loadReflection}
            className="w-full bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors"
          >
            ✨ Prowadzona refleksja
          </button>
        </div>
      </main>
    );
  }

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
              Refleksja — {selectedSession?.title_pl}
            </h1>
          </div>

          <div className="bg-blue-900/10 border border-blue-700/20 rounded-2xl p-6 text-sm text-gray-200 leading-loose whitespace-pre-wrap min-h-[200px]">
            {loadingReflection ? (
              <span className="text-gray-500 animate-pulse">Generuję refleksję...</span>
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
