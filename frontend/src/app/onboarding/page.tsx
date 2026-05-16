"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";
import { api } from "@/lib/api";

// Zapisywane w localStorage pod kluczem "onboarding_prefs"
interface OnboardingPrefs {
  prayerTime: "morning" | "evening" | "both";
  primaryPractice: string;
  reminderTime: string;
  completedAt: string;
}

// Mapa praktyki → tradycja duchowa (backend: ignatian, benedictine, franciscan...)
const PRACTICE_TO_TRADITION: Record<string, string> = {
  "/lectio-divina":     "benedictine",
  "/rozaniec":          "dominican",
  "/rachunek-sumienia": "ignatian",
  "/dziennik":          "ignatian",
  "/dzisiaj":           "ignatian",
};

const PRAYER_TIMES = [
  { value: "morning", label: "Rano", description: "Zaczynam dzień od modlitwy", icon: "🌅" },
  { value: "evening", label: "Wieczór", description: "Kończę dzień rachunkiem sumienia", icon: "🌙" },
  { value: "both",    label: "Rano i wieczór", description: "Regularność to moja siła", icon: "☀🌙" },
] as const;

const PRACTICES = [
  { value: "/dzisiaj",            label: "Liturgia dnia",       description: "Dzisiaj, święty patrona, brewiarz",   icon: "☀" },
  { value: "/lectio-divina",      label: "Lectio Divina",       description: "Modlitewne czytanie Pisma Świętego",  icon: "📖" },
  { value: "/rozaniec",           label: "Różaniec",            description: "20 tajemnic, medytacja AI",           icon: "📿" },
  { value: "/rachunek-sumienia",  label: "Rachunek Sumienia",   description: "Ignacjański Examen wieczorny",        icon: "🔥" },
  { value: "/dziennik",           label: "Dziennik duchowy",    description: "Pisemna rozmowa z Bogiem",            icon: "📓" },
];

const TOTAL_STEPS = 5;

export default function OnboardingPage() {
  const router = useRouter();
  const { user, loadFromStorage } = useAuthStore();
  const [step, setStep] = useState(1);
  const [prayerTime, setPrayerTime] = useState<"morning" | "evening" | "both">("morning");
  const [primaryPractice, setPrimaryPractice] = useState("/dzisiaj");
  const [reminderTime, setReminderTime] = useState("07:00");
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    loadFromStorage();
    // Jeśli onboarding już ukończony → pomiń
    if (typeof window !== "undefined") {
      const prefs = localStorage.getItem("onboarding_prefs");
      if (prefs) { router.replace("/dzisiaj"); }
    }
  }, [loadFromStorage, router]);

  const name = user?.displayName?.split(" ")[0] ?? "Witaj";

  const finish = async (practice = primaryPractice) => {
    const prefs: OnboardingPrefs = {
      prayerTime,
      primaryPractice: practice,
      reminderTime,
      completedAt: new Date().toISOString(),
    };
    localStorage.setItem("onboarding_prefs", JSON.stringify(prefs));

    // Sync preferences to backend (fire-and-forget — don't block navigation)
    const tradition = PRACTICE_TO_TRADITION[practice] ?? "ignatian";
    const effectiveTime =
      prayerTime === "evening" ? "20:00" : reminderTime;

    Promise.allSettled([
      // Save spiritual tradition to privacy settings
      api.put("/api/v1/users/me/privacy", { spiritual_tradition: tradition }),
      // Register notification time preference (requires existing push subscription)
      (async () => {
        const endpoint = localStorage.getItem("push_endpoint");
        if (endpoint) {
          await api.post("/api/v1/notifications/daily-reminder", {
            endpoint,
            time: effectiveTime,
          });
        }
      })(),
    ]).catch(() => {});

    setLeaving(true);
    setTimeout(() => router.push(practice), 400);
  };

  const next = () => setStep((s) => Math.min(s + 1, TOTAL_STEPS));
  const back = () => setStep((s) => Math.max(s - 1, 1));

  const progress = (step / TOTAL_STEPS) * 100;

  return (
    <main className={`min-h-screen bg-[#0d0b1a] text-white flex flex-col transition-opacity duration-400 ${leaving ? "opacity-0" : "opacity-100"}`}>
      {/* Progress bar */}
      <div className="h-0.5 bg-white/5 fixed top-0 left-0 right-0 z-10">
        <div
          className="h-full bg-[#d4af37] transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex-1 flex flex-col max-w-lg mx-auto w-full px-6 py-12">
        {/* Step indicator */}
        <div className="text-xs text-gray-600 mb-8">{step} / {TOTAL_STEPS}</div>

        {/* ── Step 1: Witaj ──────────────────────────────────────────── */}
        {step === 1 && (
          <div className="flex-1 flex flex-col justify-center animate-in fade-in duration-300">
            <div className="text-6xl text-center mb-6">✝</div>
            <h1 className="text-3xl font-bold text-center text-white mb-3">
              Witaj, {name}!
            </h1>
            <p className="text-gray-400 text-center leading-relaxed mb-2">
              Sancta Nexus to Twój towarzysz duchowy — nieustępliwie obecny,
              zawsze gotowy na rozmowę z Bogiem.
            </p>
            <p className="text-xs text-gray-600 text-center mb-10">
              Asystent refleksji pomaga porządkować myśli i wracać do modlitwy.
              Nie zastępuje kapłana, spowiednika ani kierownika duchowego.
            </p>
            <button
              onClick={next}
              className="w-full bg-[#d4af37] text-black font-semibold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors text-lg"
            >
              Zacznijmy →
            </button>
            <button
              onClick={() => finish("/dzisiaj")}
              className="w-full text-xs text-gray-600 hover:text-gray-400 mt-4 py-2 transition-colors"
            >
              Pomiń konfigurację, wejdź od razu
            </button>
          </div>
        )}

        {/* ── Step 2: Kiedy modlisz się najchętniej? ─────────────────── */}
        {step === 2 && (
          <div className="flex-1 flex flex-col animate-in fade-in duration-300">
            <h2 className="text-2xl font-bold text-white mb-2">
              Kiedy modlisz się najchętniej?
            </h2>
            <p className="text-gray-500 text-sm mb-8">
              Dostosujemy powiadomienia i sugestie do Twojego rytmu.
            </p>
            <div className="space-y-3 mb-auto">
              {PRAYER_TIMES.map((pt) => (
                <button
                  key={pt.value}
                  onClick={() => setPrayerTime(pt.value)}
                  className={`w-full rounded-2xl border p-4 text-left transition-all ${
                    prayerTime === pt.value
                      ? "bg-[#d4af37]/15 border-[#d4af37]/60"
                      : "bg-white/5 border-white/10 hover:border-white/30"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{pt.icon}</span>
                    <div>
                      <div className="font-medium text-white">{pt.label}</div>
                      <div className="text-xs text-gray-500">{pt.description}</div>
                    </div>
                    {prayerTime === pt.value && (
                      <span className="ml-auto text-[#d4af37]">✓</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
            <div className="flex gap-3 mt-8">
              <button onClick={back} className="px-5 py-3 text-gray-500 hover:text-white transition-colors text-sm">← Wstecz</button>
              <button onClick={next} className="flex-1 bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors">Dalej →</button>
            </div>
          </div>
        )}

        {/* ── Step 3: Od czego chcesz zacząć? ───────────────────────── */}
        {step === 3 && (
          <div className="flex-1 flex flex-col animate-in fade-in duration-300">
            <h2 className="text-2xl font-bold text-white mb-2">
              Od czego chcesz zacząć?
            </h2>
            <p className="text-gray-500 text-sm mb-6">
              Wybierz pierwszą praktykę — resztę odkryjesz stopniowo.
            </p>
            <div className="space-y-2 mb-auto">
              {PRACTICES.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPrimaryPractice(p.value)}
                  className={`w-full rounded-xl border p-4 text-left transition-all ${
                    primaryPractice === p.value
                      ? "bg-[#d4af37]/15 border-[#d4af37]/60"
                      : "bg-white/5 border-white/10 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{p.icon}</span>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-white">{p.label}</div>
                      <div className="text-xs text-gray-500">{p.description}</div>
                    </div>
                    {primaryPractice === p.value && (
                      <span className="text-[#d4af37] text-sm">✓</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={back} className="px-5 py-3 text-gray-500 hover:text-white transition-colors text-sm">← Wstecz</button>
              <button onClick={next} className="flex-1 bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors">Dalej →</button>
            </div>
          </div>
        )}

        {/* ── Step 4: Powiadomienie poranne ─────────────────────────── */}
        {step === 4 && (
          <div className="flex-1 flex flex-col animate-in fade-in duration-300">
            <div className="text-4xl text-center mb-6">🔔</div>
            <h2 className="text-2xl font-bold text-white mb-2 text-center">
              Codzienne przypomnienie
            </h2>
            <p className="text-gray-500 text-sm mb-8 text-center">
              Każdego ranka imię patrona dnia i liturgia — Twój punkt wyjścia.
            </p>
            <div className="bg-white/5 border border-white/10 rounded-2xl p-5 mb-6">
              <label className="text-xs text-gray-500 block mb-2">Godzina przypomnienia</label>
              <input
                type="time"
                value={reminderTime}
                onChange={(e) => setReminderTime(e.target.value)}
                className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-xl text-white text-center font-mono focus:outline-none focus:border-[#d4af37]"
              />
            </div>
            <div className="flex gap-3 mt-auto">
              <button onClick={back} className="px-5 py-3 text-gray-500 hover:text-white transition-colors text-sm">← Wstecz</button>
              <button
                onClick={next}
                className="flex-1 bg-[#d4af37] text-black font-semibold py-3 rounded-2xl hover:bg-[#c9a227] transition-colors"
              >
                Dalej →
              </button>
            </div>
            <button onClick={next} className="text-xs text-gray-600 hover:text-gray-400 mt-3 py-1 text-center transition-colors">
              Pomiń na razie
            </button>
          </div>
        )}

        {/* ── Step 5: Gotowy! ──────────────────────────────────────── */}
        {step === 5 && (
          <div className="flex-1 flex flex-col justify-center animate-in fade-in duration-300">
            <div className="text-center mb-8">
              <div className="text-6xl mb-4">🙏</div>
              <h2 className="text-3xl font-bold text-white mb-3">
                Gotowy do drogi!
              </h2>
              <p className="text-gray-400 leading-relaxed">
                Twoja platforma jest skonfigurowana.
                Pamiętaj — to nie aplikacja Cię zmieni,
                ale Bóg działający przez codzienną wierność małym krokom.
              </p>
            </div>

            <div className="bg-[#d4af37]/5 border border-[#d4af37]/20 rounded-2xl p-4 mb-8 text-sm text-gray-400 italic text-center leading-relaxed">
              „Będziesz miłował Pana Boga swego z całego serca swego,
              z całej duszy swojej i ze wszystkich sił swoich.”
              <div className="text-xs text-gray-600 mt-1 not-italic">Pwt 6,5</div>
            </div>

            <div className="space-y-3">
              <button
                onClick={() => finish(primaryPractice)}
                className="w-full bg-[#d4af37] text-black font-semibold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors text-base"
              >
                Zacznij pierwszą modlitwę →
              </button>
              <button
                onClick={() => finish("/dzisiaj")}
                className="w-full bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl py-3 text-sm text-gray-300 transition-all"
              >
                Wejdź na stronę Dzisiaj
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
