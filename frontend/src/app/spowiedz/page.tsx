"use client";

import { useState, useRef, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STATES = [
  { value: "single", label: "Osoba wolna" },
  { value: "married", label: "Małżonek/a" },
  { value: "parent", label: "Rodzic" },
  { value: "religious", label: "Zakonnik/Zakonnica" },
  { value: "priest", label: "Kapłan" },
  { value: "teenager", label: "Nastolatek" },
  { value: "child", label: "Dziecko" },
];

const COMMANDMENTS = [
  { number: 1, short: "Jeden Bóg", icon: "✝" },
  { number: 2, short: "Imię Boga", icon: "🗣" },
  { number: 3, short: "Dzień święty", icon: "⛪" },
  { number: 4, short: "Rodzice", icon: "👨‍👩‍👧" },
  { number: 5, short: "Życie", icon: "❤" },
  { number: 6, short: "Czystość", icon: "🌸" },
  { number: 7, short: "Własność", icon: "🤝" },
  { number: 8, short: "Prawda", icon: "📖" },
  { number: 9, short: "Czystość myśli", icon: "💭" },
  { number: 10, short: "Zawiść", icon: "⚖" },
];

type Stage =
  | "setup"
  | "overview"
  | "commandment"
  | "reflection"
  | "contrition"
  | "resolution";

export default function SpowiedzPage() {
  const [stage, setStage] = useState<Stage>("setup");
  const [stateOfLife, setStateOfLife] = useState("single");
  const [selectedCommandment, setSelectedCommandment] = useState<number>(1);
  const [commandments, setCommandments] = useState<any[]>([]);
  const [stateQuestions, setStateQuestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [streamedText, setStreamedText] = useState("");
  const [contritionText, setContritionText] = useState("");
  const [resolutionText, setResolutionText] = useState("");
  const [focusArea, setFocusArea] = useState("");
  const [userReflection, setUserReflection] = useState("");
  const streamRef = useRef<AbortController | null>(null);
  const textAreaRef = useRef<HTMLDivElement>(null);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    try {
      const [cmdRes, stateRes] = await Promise.all([
        fetch(`${API}/api/v1/sacraments/confession/commandments`),
        fetch(
          `${API}/api/v1/sacraments/confession/state-questions/${stateOfLife}`
        ),
      ]);
      const cmdData = await cmdRes.json();
      const stateData = await stateRes.json();
      setCommandments(cmdData.commandments || []);
      setStateQuestions(stateData.questions || []);
      setStage("overview");
    } catch {
      setCommandments(COMMANDMENTS.map((c) => ({ number: c.number, title: c.short, questions: [] })));
      setStage("overview");
    } finally {
      setLoading(false);
    }
  }, [stateOfLife]);

  const streamReflection = useCallback(
    async (commandmentNumber: number, userText?: string) => {
      if (streamRef.current) streamRef.current.abort();
      const controller = new AbortController();
      streamRef.current = controller;
      setStreamedText("");
      setStage("reflection");

      try {
        const res = await fetch(
          `${API}/api/v1/sacraments/confession/reflection/stream`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              commandment_number: commandmentNumber,
              state_of_life: stateOfLife,
              user_reflection: userText || null,
            }),
            signal: controller.signal,
          }
        );

        if (!res.ok || !res.body) {
          setStreamedText("Nie udało się załadować refleksji. Spróbuj ponownie.");
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let accumulated = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          accumulated += chunk;
          setStreamedText(accumulated);
          textAreaRef.current?.scrollTo(0, textAreaRef.current.scrollHeight);
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setStreamedText("Błąd połączenia z serwerem.");
        }
      }
    },
    [stateOfLife]
  );

  const generateContrition = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API}/api/v1/sacraments/confession/act-of-contrition`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ state_of_life: stateOfLife }),
        }
      );
      const data = await res.json();
      setContritionText(data.act_of_contrition || "");
      setStage("contrition");
    } catch {
      setContritionText("Nie udało się wygenerować aktu żalu. Spróbuj ponownie.");
      setStage("contrition");
    } finally {
      setLoading(false);
    }
  };

  const generateResolution = async () => {
    if (!focusArea.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API}/api/v1/sacraments/confession/resolution`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            focus_area: focusArea,
            state_of_life: stateOfLife,
          }),
        }
      );
      const data = await res.json();
      setResolutionText(data.resolution || "");
      setStage("resolution");
    } catch {
      setResolutionText("Nie udało się wygenerować postanowienia.");
      setStage("resolution");
    } finally {
      setLoading(false);
    }
  };

  // ── Render stages ──────────────────────────────────────────────────────────

  if (stage === "setup") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex items-center justify-center px-4">
        <div className="max-w-sm w-full">
          <div className="text-center mb-8">
            <div className="text-5xl mb-3">✝</div>
            <h1 className="text-2xl font-bold text-[#d4af37] mb-2">
              Rachunek sumienia
            </h1>
            <p className="text-gray-400 text-sm">
              «Podejdźmy z prawdziwym sercem» (Hbr 10,22)
            </p>
          </div>

          <div className="bg-white/5 rounded-2xl p-6 mb-6">
            <label className="block text-sm text-gray-300 mb-2">
              Stan życia
            </label>
            <select
              value={stateOfLife}
              onChange={(e) => setStateOfLife(e.target.value)}
              className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-[#d4af37]"
            >
              {STATES.map((s) => (
                <option key={s.value} value={s.value} className="bg-gray-900">
                  {s.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-2">
              Rachunek sumienia zostanie dostosowany do twojego stanu życia.
            </p>
          </div>

          <div className="bg-amber-900/20 border border-amber-700/30 rounded-xl p-4 mb-6 text-xs text-amber-300/80 leading-relaxed">
            🔒 Twoje odpowiedzi nie są przechowywane. Każda sesja jest
            całkowicie poufna.
          </div>

          <button
            onClick={loadOverview}
            disabled={loading}
            className="w-full bg-[#d4af37] text-black font-semibold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors disabled:opacity-50"
          >
            {loading ? "Przygotowuję..." : "Rozpocznij rachunek sumienia"}
          </button>
        </div>
      </main>
    );
  }

  if (stage === "overview") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-8">
            <button
              onClick={() => setStage("setup")}
              className="text-gray-400 hover:text-white"
            >
              ←
            </button>
            <h1 className="text-xl font-bold text-[#d4af37]">
              Dziesięć Przykazań
            </h1>
          </div>

          <p className="text-gray-400 text-sm mb-6 leading-relaxed">
            Wybierz przykazanie, przy którym chcesz się zatrzymać. AI-kierownik
            duchowy przeprowadzi cię przez refleksję.
          </p>

          <div className="grid grid-cols-2 gap-3 mb-8">
            {COMMANDMENTS.map((cmd) => (
              <button
                key={cmd.number}
                onClick={() => {
                  setSelectedCommandment(cmd.number);
                  setUserReflection("");
                  setStage("commandment");
                }}
                className="bg-white/5 hover:bg-white/10 border border-white/10 hover:border-[#d4af37]/50 rounded-xl p-4 text-left transition-all"
              >
                <div className="text-2xl mb-1">{cmd.icon}</div>
                <div className="text-xs text-gray-500 mb-0.5">
                  {cmd.number}. Przykazanie
                </div>
                <div className="text-sm font-medium text-white">
                  {cmd.short}
                </div>
              </button>
            ))}
          </div>

          {stateQuestions.length > 0 && (
            <div className="bg-white/5 rounded-2xl p-5 mb-6">
              <h3 className="text-sm font-semibold text-[#d4af37] mb-3">
                Pytania dla twojego stanu życia
              </h3>
              <ul className="space-y-2">
                {stateQuestions.map((q, i) => (
                  <li
                    key={i}
                    className="text-sm text-gray-300 flex items-start gap-2"
                  >
                    <span className="text-[#d4af37] mt-0.5">•</span>
                    {q}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-3">
            <button
              onClick={generateContrition}
              disabled={loading}
              className="w-full bg-purple-700/60 hover:bg-purple-700/80 border border-purple-600/50 text-white font-medium py-3 rounded-2xl transition-colors disabled:opacity-50"
            >
              {loading ? "Generuję..." : "📿 Akt Żalu"}
            </button>

            <div className="flex gap-3">
              <input
                type="text"
                value={focusArea}
                onChange={(e) => setFocusArea(e.target.value)}
                placeholder="Obszar postanowienia poprawy..."
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37]"
              />
              <button
                onClick={generateResolution}
                disabled={loading || !focusArea.trim()}
                className="bg-white/10 hover:bg-white/20 border border-white/20 text-white px-4 py-3 rounded-xl text-sm font-medium transition-colors disabled:opacity-40"
              >
                Postanowienie
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (stage === "commandment") {
    const cmd = commandments.find((c) => c.number === selectedCommandment);
    const simpleCmd = COMMANDMENTS.find((c) => c.number === selectedCommandment);

    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button
              onClick={() => setStage("overview")}
              className="text-gray-400 hover:text-white"
            >
              ←
            </button>
            <div>
              <div className="text-xs text-gray-500">
                {selectedCommandment}. Przykazanie
              </div>
              <h1 className="text-lg font-bold text-[#d4af37]">
                {cmd?.title || simpleCmd?.short}
              </h1>
            </div>
          </div>

          {cmd?.ccc_ref && (
            <div className="text-xs text-gray-500 mb-4">
              KKK {cmd.ccc_ref} · {cmd.scripture}
            </div>
          )}

          {cmd?.questions && cmd.questions.length > 0 && (
            <div className="bg-white/5 rounded-2xl p-5 mb-6">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">
                Pytania do refleksji
              </h3>
              <ul className="space-y-2">
                {cmd.questions.map((q: string, i: number) => (
                  <li
                    key={i}
                    className="text-sm text-gray-300 flex items-start gap-2"
                  >
                    <span className="text-[#d4af37] mt-0.5">•</span>
                    {q}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm text-gray-400 mb-2">
              Twoja refleksja (opcjonalnie — nie jest zapisywana)
            </label>
            <textarea
              value={userReflection}
              onChange={(e) => setUserReflection(e.target.value)}
              rows={3}
              placeholder="Możesz podzielić się swoimi myślami, a AI-kierownik pomoże ci pogłębić refleksję..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37] resize-none"
            />
          </div>

          <div className="space-y-3">
            <button
              onClick={() =>
                streamReflection(
                  selectedCommandment,
                  userReflection || undefined
                )
              }
              className="w-full bg-[#d4af37] text-black font-semibold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors"
            >
              Prowadź mnie przez refleksję ✨
            </button>
          </div>
        </div>
      </main>
    );
  }

  if (stage === "reflection") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button
              onClick={() => setStage("commandment")}
              className="text-gray-400 hover:text-white"
            >
              ←
            </button>
            <h1 className="text-lg font-bold text-[#d4af37]">
              Refleksja duchowa
            </h1>
          </div>

          <div
            ref={textAreaRef}
            className="bg-white/5 rounded-2xl p-6 min-h-[250px] max-h-[50vh] overflow-y-auto text-sm text-gray-200 leading-loose whitespace-pre-wrap mb-6"
          >
            {streamedText || (
              <span className="text-gray-500 animate-pulse">
                Kierownik duchowy pisze...
              </span>
            )}
          </div>

          {streamedText && (
            <div className="space-y-3">
              <button
                onClick={() => {
                  const next = selectedCommandment < 10 ? selectedCommandment + 1 : 1;
                  setSelectedCommandment(next);
                  setUserReflection("");
                  setStage("commandment");
                }}
                className="w-full bg-white/10 hover:bg-white/15 border border-white/20 text-white font-medium py-3 rounded-2xl transition-colors"
              >
                Następne przykazanie →
              </button>
              <button
                onClick={() => setStage("overview")}
                className="w-full bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors"
              >
                Wróć do przeglądu
              </button>
            </div>
          )}
        </div>
      </main>
    );
  }

  if (stage === "contrition") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button
              onClick={() => setStage("overview")}
              className="text-gray-400 hover:text-white"
            >
              ←
            </button>
            <h1 className="text-lg font-bold text-[#d4af37]">📿 Akt Żalu</h1>
          </div>

          <div className="bg-purple-900/20 border border-purple-700/30 rounded-2xl p-6 text-sm text-gray-200 leading-loose whitespace-pre-wrap mb-6">
            {contritionText || (
              <span className="text-gray-500 animate-pulse">
                Generuję akt żalu...
              </span>
            )}
          </div>

          {contritionText && (
            <div className="space-y-3">
              <p className="text-xs text-gray-500 text-center">
                Możesz odmówić ten akt żalu przed przystąpieniem do spowiedzi.
              </p>
              <button
                onClick={() => setStage("overview")}
                className="w-full bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors"
              >
                Zakończ przygotowanie
              </button>
            </div>
          )}
        </div>
      </main>
    );
  }

  if (stage === "resolution") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-8 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button
              onClick={() => setStage("overview")}
              className="text-gray-400 hover:text-white"
            >
              ←
            </button>
            <h1 className="text-lg font-bold text-[#d4af37]">
              Postanowienie poprawy
            </h1>
          </div>

          <div className="text-xs text-gray-500 mb-4">
            Obszar: <span className="text-[#d4af37]">{focusArea}</span>
          </div>

          <div className="bg-green-900/20 border border-green-700/30 rounded-2xl p-6 text-sm text-gray-200 leading-loose whitespace-pre-wrap mb-6">
            {resolutionText || (
              <span className="text-gray-500 animate-pulse">
                Generuję postanowienie...
              </span>
            )}
          </div>

          {resolutionText && (
            <button
              onClick={() => setStage("overview")}
              className="w-full bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors"
            >
              Wróć do przeglądu
            </button>
          )}
        </div>
      </main>
    );
  }

  return null;
}
