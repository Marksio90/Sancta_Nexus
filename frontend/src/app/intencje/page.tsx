"use client";

import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CATEGORIES = [
  { id: "all", label: "Wszystkie" },
  { id: "general", label: "Ogólne" },
  { id: "zdrowie", label: "Zdrowie" },
  { id: "rodzina", label: "Rodzina" },
  { id: "praca", label: "Praca" },
  { id: "pokój", label: "Pokój" },
  { id: "nawrócenie", label: "Nawrócenie" },
  { id: "żałoba", label: "Żałoba" },
  { id: "wdzięczność", label: "Wdzięczność" },
  { id: "powołanie", label: "Powołanie" },
];

const CATEGORY_ICONS: Record<string, string> = {
  general: "🙏",
  zdrowie: "❤",
  rodzina: "👨‍👩‍👧",
  praca: "💼",
  pokój: "🕊",
  nawrócenie: "✝",
  żałoba: "🕯",
  wdzięczność: "✨",
  egzaminy: "📚",
  powołanie: "⛪",
};

type AppState = "list" | "new";

export default function IntencjePage() {
  const [appState, setAppState] = useState<AppState>("list");
  const [intentions, setIntentions] = useState<any[]>([]);
  const [category, setCategory] = useState("all");
  const [loading, setLoading] = useState(true);
  const [prayedIds, setPrayedIds] = useState<Set<string>>(new Set());

  // New intention form
  const [content, setContent] = useState("");
  const [newCategory, setNewCategory] = useState("general");
  const [authorDisplay, setAuthorDisplay] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const loadIntentions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API}/api/v1/community/intentions?category=${category}&limit=40`
      );
      const data = await res.json();
      setIntentions(data.intentions || []);
    } catch {
      setIntentions([]);
    } finally {
      setLoading(false);
    }
  }, [category]);

  useEffect(() => {
    loadIntentions();
  }, [loadIntentions]);

  const pray = async (id: string) => {
    if (prayedIds.has(id)) return;
    setPrayedIds((prev) => new Set([...prev, id]));
    try {
      await fetch(`${API}/api/v1/community/intentions/${id}/pray`, {
        method: "POST",
      });
      setIntentions((prev) =>
        prev.map((i) =>
          i.id === id ? { ...i, prayer_count: i.prayer_count + 1 } : i
        )
      );
    } catch {
      setPrayedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const submitIntention = async () => {
    if (!content.trim() || submitting) return;
    setSubmitting(true);
    try {
      await fetch(`${API}/api/v1/community/intentions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: content.trim(),
          is_public: isPublic,
          category: newCategory,
          author_display: authorDisplay.trim() || "Anonim",
        }),
      });
      setSubmitted(true);
      setContent("");
      setAuthorDisplay("");
      setTimeout(() => {
        setSubmitted(false);
        setAppState("list");
        loadIntentions();
      }, 2000);
    } catch {
      setSubmitting(false);
    }
  };

  // ── New intention form ─────────────────────────────────────────────────────
  if (appState === "new") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-lg mx-auto px-4 py-10 pb-24">
          <div className="flex items-center gap-3 mb-8">
            <button
              onClick={() => setAppState("list")}
              className="text-gray-400 hover:text-white"
            >
              ←
            </button>
            <h1 className="text-xl font-bold text-[#d4af37]">
              Nowa intencja modlitewna
            </h1>
          </div>

          {submitted ? (
            <div className="text-center py-16">
              <div className="text-5xl mb-4">🙏</div>
              <p className="text-[#d4af37] font-semibold text-lg">
                Intencja dodana!
              </p>
              <p className="text-gray-400 text-sm mt-1">
                Wspólnota będzie się modlić razem z Tobą.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              <div>
                <label className="block text-sm text-gray-300 mb-2">
                  Intencja modlitewna *
                </label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={4}
                  maxLength={500}
                  placeholder="O co chcesz prosić Boga i proszę wspólnotę o modlitwę?"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37] resize-none"
                />
                <div className="text-xs text-gray-600 text-right mt-1">
                  {content.length}/500
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-300 mb-2">
                  Kategoria
                </label>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.filter((c) => c.id !== "all").map((c) => (
                    <button
                      key={c.id}
                      onClick={() => setNewCategory(c.id)}
                      className={`text-xs px-3 py-1.5 rounded-full border transition-all ${
                        newCategory === c.id
                          ? "bg-[#d4af37] border-[#d4af37] text-black font-semibold"
                          : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
                      }`}
                    >
                      {CATEGORY_ICONS[c.id] || "🙏"} {c.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-300 mb-2">
                  Podpisać jako (opcjonalnie)
                </label>
                <input
                  type="text"
                  value={authorDisplay}
                  onChange={(e) => setAuthorDisplay(e.target.value)}
                  maxLength={100}
                  placeholder="np. Marysia, Rodzina Kowalskich — lub zostaw puste dla Anonim"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37]"
                />
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsPublic((v) => !v)}
                  className={`relative w-11 h-6 rounded-full transition-colors ${
                    isPublic ? "bg-[#d4af37]" : "bg-gray-700"
                  }`}
                >
                  <span
                    className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${
                      isPublic ? "left-5" : "left-0.5"
                    }`}
                  />
                </button>
                <span className="text-sm text-gray-300">
                  {isPublic
                    ? "Publiczna — widoczna dla wspólnoty"
                    : "Prywatna — tylko Ty i Bóg"}
                </span>
              </div>

              <button
                onClick={submitIntention}
                disabled={!content.trim() || submitting}
                className="w-full bg-[#d4af37] text-black font-semibold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors disabled:opacity-50"
              >
                {submitting ? "Dodaję..." : "Dodaj intencję 🙏"}
              </button>
            </div>
          )}
        </div>
      </main>
    );
  }

  // ── Intentions list ────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      <div className="max-w-2xl mx-auto px-4 py-10 pb-24">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[#d4af37]">
              🙏 Intencje modlitewne
            </h1>
            <p className="text-gray-500 text-xs mt-0.5">
              Módl się razem ze wspólnotą
            </p>
          </div>
          <button
            onClick={() => setAppState("new")}
            className="bg-[#d4af37] text-black text-sm font-semibold px-4 py-2 rounded-xl hover:bg-[#c9a227] transition-colors"
          >
            + Dodaj
          </button>
        </div>

        {/* Category filter */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-6 scrollbar-hide">
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              onClick={() => setCategory(c.id)}
              className={`whitespace-nowrap text-xs px-3 py-1.5 rounded-full border transition-all flex-shrink-0 ${
                category === c.id
                  ? "bg-[#d4af37] border-[#d4af37] text-black font-semibold"
                  : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Intentions */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((n) => (
              <div
                key={n}
                className="bg-white/5 rounded-xl p-4 h-20 animate-pulse"
              />
            ))}
          </div>
        ) : intentions.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <div className="text-4xl mb-3">🕯</div>
            <p>Brak intencji w tej kategorii.</p>
            <button
              onClick={() => setAppState("new")}
              className="mt-4 text-[#d4af37] text-sm underline"
            >
              Dodaj pierwszą intencję
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {intentions.map((intention) => {
              const prayed = prayedIds.has(intention.id);
              return (
                <div
                  key={intention.id}
                  className="bg-white/5 border border-white/10 rounded-xl p-4"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-xl mt-0.5">
                      {CATEGORY_ICONS[intention.category] || "🙏"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-200 leading-relaxed mb-2">
                        {intention.content}
                      </p>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                          <span>{intention.author_display || "Anonim"}</span>
                          {intention.status === "answered" && (
                            <span className="text-green-500">✓ Wysłuchana</span>
                          )}
                        </div>
                        <button
                          onClick={() => pray(intention.id)}
                          disabled={prayed}
                          className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-all ${
                            prayed
                              ? "bg-violet-700/40 border-violet-600/50 text-violet-300"
                              : "bg-white/5 border-white/10 text-gray-400 hover:border-violet-600/50 hover:text-violet-300"
                          }`}
                        >
                          <span>🙏</span>
                          <span>
                            {prayed ? "Modlę się" : "Modlę się"}
                          </span>
                          <span className="font-semibold">
                            {intention.prayer_count}
                          </span>
                        </button>
                      </div>
                    </div>
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
