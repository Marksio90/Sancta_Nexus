"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AppState = "list" | "session" | "gifts" | "patron" | "chat";

const GIFT_ICONS: Record<string, string> = {
  Mądrość: "✨",
  Rozum: "💡",
  Rada: "🧭",
  Męstwo: "⚔",
  Umiejętność: "🔧",
  Pobożność: "🙏",
  "Bojaźń Boża": "👁",
};

export default function BierzmowaniePage() {
  const [appState, setAppState] = useState<AppState>("list");
  const [program, setProgram] = useState<any[]>([]);
  const [gifts, setGifts] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<any>(null);
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  // Patron finder
  const [interests, setInterests] = useState("");
  const [traits, setTraits] = useState("");
  const [patronSuggestions, setPatronSuggestions] = useState("");
  const [loadingPatron, setLoadingPatron] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/v1/sacraments/confirmation/program`)
      .then((r) => r.json())
      .then((d) => {
        setProgram(d.sessions || []);
        setGifts(d.gifts_of_spirit || []);
      })
      .catch(() => {});
  }, []);

  const openSession = (session: any) => {
    setSelectedSession(session);
    setMessages([
      {
        role: "assistant",
        content: `Witaj w sesji ${session.number}: **${session.title}**\n\n*${session.subtitle}*\n\n${session.key_question}`,
      },
    ]);
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
      const res = await fetch(`${API}/api/v1/sacraments/confirmation/ask`, {
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
      setMessages([...newMessages, { role: "assistant", content: "Błąd połączenia." }]);
    } finally {
      setSending(false);
    }
  };

  const findPatron = async () => {
    setLoadingPatron(true);
    try {
      const res = await fetch(`${API}/api/v1/sacraments/confirmation/patron`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interests: interests
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          personal_traits: traits
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        }),
      });
      const data = await res.json();
      setPatronSuggestions(data.suggestions || "");
    } catch {
      setPatronSuggestions("Nie udało się załadować propozycji.");
    } finally {
      setLoadingPatron(false);
    }
  };

  // ── List ──────────────────────────────────────────────────────────────────
  if (appState === "list") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-10 pb-24">
          <div className="text-center mb-8">
            <div className="text-5xl mb-3">🔥</div>
            <h1 className="text-2xl font-bold text-[#d4af37] mb-1">
              Przygotowanie do Bierzmowania
            </h1>
            <p className="text-gray-400 text-sm">
              6 kroków do przyjęcia Ducha Świętego · KKK §§ 1285–1321
            </p>
          </div>

          {/* Quick links */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            <button
              onClick={() => setAppState("gifts")}
              className="bg-amber-900/30 hover:bg-amber-900/50 border border-amber-700/40 rounded-xl p-4 text-left transition-all"
            >
              <div className="text-2xl mb-1">🌟</div>
              <div className="text-sm font-semibold">7 darów Ducha</div>
              <div className="text-xs text-gray-500">Iz 11,2-3</div>
            </button>
            <button
              onClick={() => setAppState("patron")}
              className="bg-purple-900/30 hover:bg-purple-900/50 border border-purple-700/40 rounded-xl p-4 text-left transition-all"
            >
              <div className="text-2xl mb-1">👤</div>
              <div className="text-sm font-semibold">Znajdź patrona</div>
              <div className="text-xs text-gray-500">AI-pomoc w wyborze</div>
            </button>
          </div>

          {/* Sessions */}
          {program.length === 0 ? (
            <div className="text-center text-gray-500 py-8 animate-pulse">Ładuję program...</div>
          ) : (
            <div className="space-y-3">
              {program.map((session) => (
                <button
                  key={session.session_id}
                  onClick={() => openSession(session)}
                  className="w-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-amber-600/40 rounded-xl p-4 text-left transition-all"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-9 h-9 rounded-full bg-amber-600/20 border border-amber-600/40 flex items-center justify-center text-sm font-bold text-amber-400">
                      {session.number}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold text-white">{session.title}</div>
                      <div className="text-xs text-amber-400/70">{session.subtitle}</div>
                    </div>
                    {session.holy_spirit_gift && (
                      <div className="text-xs text-gray-600 text-right hidden sm:block">
                        {session.holy_spirit_gift}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </main>
    );
  }

  // ── 7 Gifts ────────────────────────────────────────────────────────────────
  if (appState === "gifts") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("list")} className="text-gray-400 hover:text-white">←</button>
            <h1 className="text-lg font-bold text-[#d4af37]">7 darów Ducha Świętego</h1>
          </div>

          <p className="text-xs text-gray-500 mb-6">Iz 11,2-3 · KKK §§ 1830-1832</p>

          <div className="space-y-3">
            {gifts.map((gift: any) => (
              <div
                key={gift.gift}
                className="bg-white/5 border border-white/10 rounded-xl p-4"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">
                    {GIFT_ICONS[gift.gift] || "✨"}
                  </span>
                  <div>
                    <div className="font-semibold text-[#d4af37]">{gift.gift}</div>
                    <div className="text-xs text-gray-500 italic">{gift.latin}</div>
                  </div>
                </div>
                <p className="text-sm text-gray-300 mb-2">{gift.description}</p>
                <div className="flex gap-4 text-xs text-gray-600">
                  <span>{gift.scripture}</span>
                  <span>KKK {gift.ccc}</span>
                  <span>Owoc: <span className="text-amber-400">{gift.fruit}</span></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    );
  }

  // ── Patron finder ──────────────────────────────────────────────────────────
  if (appState === "patron") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("list")} className="text-gray-400 hover:text-white">←</button>
            <h1 className="text-lg font-bold text-[#d4af37]">Znajdź patrona bierzmowania</h1>
          </div>

          <p className="text-sm text-gray-400 mb-6 leading-relaxed">
            AI dobierze dla ciebie świętego, który będzie twoim patronem i wzorem.
            Podaj swoje zainteresowania i cechy charakteru.
          </p>

          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm text-gray-300 mb-1">
                Zainteresowania (oddziel przecinkami)
              </label>
              <input
                type="text"
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                placeholder="np. muzyka, nauka, sport, literatura, przyroda"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-600/50"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-1">
                Cechy charakteru (oddziel przecinkami)
              </label>
              <input
                type="text"
                value={traits}
                onChange={(e) => setTraits(e.target.value)}
                placeholder="np. odważny, refleksyjny, towarzyski, poszukujący"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-600/50"
              />
            </div>
          </div>

          <button
            onClick={findPatron}
            disabled={loadingPatron || (!interests.trim() && !traits.trim())}
            className="w-full bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors disabled:opacity-50 mb-6"
          >
            {loadingPatron ? "Szukam patrona..." : "Znajdź mojego patrona ✨"}
          </button>

          {patronSuggestions && (
            <div className="bg-purple-900/20 border border-purple-700/30 rounded-2xl p-6 text-sm text-gray-200 leading-loose whitespace-pre-wrap">
              {patronSuggestions}
            </div>
          )}
        </div>
      </main>
    );
  }

  // ── Session ────────────────────────────────────────────────────────────────
  if (appState === "session" && selectedSession) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("list")} className="text-gray-400 hover:text-white">←</button>
            <div>
              <div className="text-xs text-gray-500">Sesja {selectedSession.number}</div>
              <h1 className="text-xl font-bold text-[#d4af37]">{selectedSession.title}</h1>
            </div>
          </div>

          {/* Info row */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-white/5 rounded-xl p-3">
              <div className="text-xs text-gray-500 mb-1">Pismo Święte</div>
              {selectedSession.scripture?.map((s: string) => (
                <div key={s} className="text-xs text-[#d4af37]">{s}</div>
              ))}
            </div>
            <div className="bg-white/5 rounded-xl p-3">
              <div className="text-xs text-gray-500 mb-1">KKK</div>
              {selectedSession.ccc_refs?.map((r: string) => (
                <div key={r} className="text-xs text-[#d4af37]">{r}</div>
              ))}
            </div>
          </div>

          {/* Challenge */}
          <div className="bg-amber-900/20 border border-amber-700/30 rounded-xl p-4 mb-4">
            <div className="text-xs font-semibold text-[#d4af37] mb-1">🎯 Wyzwanie tygodnia</div>
            <p className="text-sm text-gray-300">{selectedSession.personal_challenge}</p>
          </div>

          {/* Prayer */}
          <div className="bg-white/5 rounded-xl p-4 mb-4 italic text-sm text-gray-400">
            🙏 {selectedSession.prayer}
          </div>

          {/* Chat */}
          <div className="bg-white/5 rounded-2xl p-4 mb-4 max-h-64 overflow-y-auto space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={`text-sm ${m.role === "user" ? "text-right" : "text-left"}`}>
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
              <div className="text-xs text-gray-500 animate-pulse">Katechista odpowiada...</div>
            )}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Masz pytanie?"
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-600/50"
            />
            <button
              onClick={sendMessage}
              disabled={sending || !input.trim()}
              className="bg-amber-700/60 hover:bg-amber-700/80 text-white px-4 py-3 rounded-xl text-sm transition-colors disabled:opacity-40"
            >
              →
            </button>
          </div>
        </div>
      </main>
    );
  }

  return null;
}
