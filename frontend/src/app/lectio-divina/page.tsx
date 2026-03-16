"use client";

import { useState, useCallback } from "react";
import { ArrowLeft, ArrowRight, Heart } from "lucide-react";
import Link from "next/link";
import { StageIndicator } from "@/components/ui/stage-indicator";
import { BreathingTimer } from "@/components/ui/breathing-timer";
import { ScriptureDisplay } from "@/components/ui/scripture-display";
import type { LectioDivinaStage } from "@/types";

const STAGES: LectioDivinaStage[] = [
  "welcome",
  "lectio",
  "meditatio",
  "oratio",
  "contemplatio",
  "actio",
];

const STAGE_LABELS: Record<LectioDivinaStage, string> = {
  welcome: "Powitanie",
  lectio: "Lectio",
  meditatio: "Meditatio",
  oratio: "Oratio",
  contemplatio: "Contemplatio",
  actio: "Actio",
};

/* ── Mock data (to be replaced by API calls) ── */
const MOCK_SCRIPTURE = {
  book: "Ewangelia wg św. Jana",
  chapter: 15,
  startVerse: 4,
  endVerse: 5,
  text: "Trwajcie we Mnie, a Ja w was trwać będę. Podobnie jak latorośl nie może przynosić owocu sama z siebie — o ile nie trwa w winnym krzewie — tak samo i wy, jeżeli we Mnie trwać nie będziecie. Ja jestem krzewem winnym, wy — latoroślami. Kto trwa we Mnie, a Ja w nim, ten przynosi owoc obfity, ponieważ beze Mnie nic nie możecie uczynić.",
  translation: "Biblia Tysiąclecia",
};

const MOCK_CONTEXT =
  "Fragment ten pochodzi z Mowy Pożegnalnej Jezusa podczas Ostatniej Wieczerzy. Metafora winnego krzewu była dobrze znana w kulturze żydowskiej — Izrael był często porównywany do winnicy Pana (Iz 5:1-7). Jezus nadaje tej metaforze nowe, głębsze znaczenie, wskazując na osobistą relację z Nim jako źródło duchowego życia.";

const MOCK_QUESTIONS = [
  "Które słowo lub fraza najbardziej przyciąga Twoją uwagę?",
  "Co Jezus mówi Ci osobiście przez ten fragment?",
  "W jaki sposób 'trwasz' w Chrystusie w swoim codziennym życiu?",
  "Co przeszkadza Ci w przynoszeniu 'owocu obfitego'?",
];

const MOCK_PRAYER =
  "Panie Jezu, Ty jesteś prawdziwym Krzewem Winnym, a ja pragnę być Twoją latoroślą. Pomóż mi trwać w Tobie każdego dnia — w modlitwie, w sakramentach, w miłości do bliźnich. Wiem, że beze Ciebie nic nie mogę uczynić. Oczyść mnie ze wszystkiego, co przeszkadza mi w przynoszeniu owocu. Napełnij mnie Twoim Duchem, abym żył tak, jak Ty tego pragniesz. Amen.";

const MOCK_CHALLENGE =
  "Dzisiejsze wyzwanie: Przez cały dzień, w każdej chwili wyboru, zatrzymaj się na moment i zapytaj: 'Panie, co Ty byś wybrał?' Pozwól, aby świadomość Jego obecności kierowała Twoimi decyzjami.";

export default function LectioDivinaPage() {
  const [currentStage, setCurrentStage] = useState<number>(0);
  const [emotion, setEmotion] = useState("");
  const [meditationResponse, setMeditationResponse] = useState("");
  const [isTransitioning, setIsTransitioning] = useState(false);

  const stage = STAGES[currentStage];

  const goToStage = useCallback(
    (direction: 1 | -1) => {
      const next = currentStage + direction;
      if (next < 0 || next >= STAGES.length) return;
      setIsTransitioning(true);
      setTimeout(() => {
        setCurrentStage(next);
        setIsTransitioning(false);
      }, 300);
    },
    [currentStage],
  );

  const canGoNext = () => {
    if (stage === "welcome") return emotion.trim().length > 0;
    return true;
  };

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-3xl">
        {/* Back link */}
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-2 text-sm text-sacred-text-muted transition-colors hover:text-gold"
        >
          <ArrowLeft className="h-4 w-4" />
          Powrót
        </Link>

        {/* Stage indicator */}
        <StageIndicator
          stages={STAGES.map((s) => STAGE_LABELS[s])}
          currentStage={currentStage}
        />

        {/* Stage content */}
        <div
          className={`mt-10 transition-all duration-300 ${
            isTransitioning
              ? "translate-y-2 opacity-0"
              : "translate-y-0 opacity-100"
          }`}
        >
          {/* ── Welcome / Emotion ── */}
          {stage === "welcome" && (
            <div className="animate-fade-in text-center">
              <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-gold/30 bg-sacred-surface">
                <Heart className="h-8 w-8 text-gold" />
              </div>
              <h1 className="font-heading mb-4 text-3xl text-gold">
                Jak się dziś czujesz?
              </h1>
              <p className="mx-auto mb-8 max-w-md text-sacred-text-muted">
                Podziel się swoim stanem ducha. Pomoże to dobrać odpowiedni
                fragment Pisma Świętego i poprowadzić Twoją modlitwę.
              </p>
              <textarea
                value={emotion}
                onChange={(e) => setEmotion(e.target.value)}
                placeholder="Np. Czuję spokój, ale też lekki niepokój o przyszłość..."
                className="mx-auto block w-full max-w-lg resize-none rounded-xl border border-sacred-border bg-sacred-surface p-4 text-sacred-text placeholder-sacred-text-muted/50 transition-colors focus:border-gold/50 focus:outline-none"
                rows={4}
              />
            </div>
          )}

          {/* ── Lectio ── */}
          {stage === "lectio" && (
            <div className="animate-fade-in">
              <h2 className="font-heading mb-2 text-center text-2xl text-gold">
                Lectio
              </h2>
              <p className="mb-8 text-center text-sacred-text-muted">
                Czytaj uważnie. Pozwól, aby słowa dotarły do Twojego serca.
              </p>

              <ScriptureDisplay
                book={MOCK_SCRIPTURE.book}
                chapter={MOCK_SCRIPTURE.chapter}
                startVerse={MOCK_SCRIPTURE.startVerse}
                endVerse={MOCK_SCRIPTURE.endVerse}
                text={MOCK_SCRIPTURE.text}
                translation={MOCK_SCRIPTURE.translation}
              />

              <div className="mt-8 rounded-xl border border-sacred-border bg-sacred-surface p-6">
                <h3 className="font-heading mb-3 text-lg text-parchment">
                  Kontekst historyczny
                </h3>
                <p className="leading-relaxed text-sacred-text-muted">
                  {MOCK_CONTEXT}
                </p>
              </div>
            </div>
          )}

          {/* ── Meditatio ── */}
          {stage === "meditatio" && (
            <div className="animate-fade-in">
              <h2 className="font-heading mb-2 text-center text-2xl text-gold">
                Meditatio
              </h2>
              <p className="mb-8 text-center text-sacred-text-muted">
                Rozważaj Słowo. Co Bóg mówi do Ciebie przez ten fragment?
              </p>

              <div className="mb-8 space-y-4">
                {MOCK_QUESTIONS.map((question, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-sacred-border bg-sacred-surface p-4"
                  >
                    <p className="font-scripture text-gold-light">{question}</p>
                  </div>
                ))}
              </div>

              <div>
                <label className="mb-2 block text-sm text-sacred-text-muted">
                  Twoja refleksja
                </label>
                <textarea
                  value={meditationResponse}
                  onChange={(e) => setMeditationResponse(e.target.value)}
                  placeholder="Zapisz swoje przemyślenia..."
                  className="w-full resize-none rounded-xl border border-sacred-border bg-sacred-surface p-4 text-sacred-text placeholder-sacred-text-muted/50 transition-colors focus:border-gold/50 focus:outline-none"
                  rows={6}
                />
              </div>
            </div>
          )}

          {/* ── Oratio ── */}
          {stage === "oratio" && (
            <div className="animate-fade-in">
              <h2 className="font-heading mb-2 text-center text-2xl text-gold">
                Oratio
              </h2>
              <p className="mb-8 text-center text-sacred-text-muted">
                Odpowiedz Bogu modlitwą. Oto modlitwa zainspirowana Twoją
                refleksją.
              </p>

              <div className="glow-candle rounded-xl border border-gold/20 bg-sacred-surface p-8">
                <p className="font-scripture text-center text-lg leading-loose text-parchment">
                  {MOCK_PRAYER}
                </p>
              </div>

              <p className="mt-6 text-center text-sm text-sacred-text-muted">
                Możesz odmówić tę modlitwę własnymi słowami lub w ciszy serca.
              </p>
            </div>
          )}

          {/* ── Contemplatio ── */}
          {stage === "contemplatio" && (
            <div className="animate-fade-in">
              <h2 className="font-heading mb-2 text-center text-2xl text-gold">
                Contemplatio
              </h2>
              <p className="mb-12 text-center text-sacred-text-muted">
                Bądź w ciszy przed Bogiem. Pozwól Mu działać.
              </p>

              <BreathingTimer durationMinutes={3} />
            </div>
          )}

          {/* ── Actio ── */}
          {stage === "actio" && (
            <div className="animate-fade-in text-center">
              <h2 className="font-heading mb-2 text-3xl text-gold">Actio</h2>
              <p className="mb-8 text-sacred-text-muted">
                Idź i żyj tym, co otrzymałeś.
              </p>

              <div className="mx-auto max-w-lg rounded-xl border border-gold/20 bg-sacred-surface p-8">
                <h3 className="font-heading mb-4 text-lg text-candlelight">
                  Twoje dzisiejsze wyzwanie
                </h3>
                <p className="font-scripture leading-relaxed text-parchment">
                  {MOCK_CHALLENGE}
                </p>
              </div>

              <div className="sacred-divider mx-auto my-10 w-48" />

              <p className="font-scripture text-sacred-text-muted">
                &ldquo;Bądźcie wykonawcami słowa, a nie tylko
                słuchaczami&rdquo;
                <br />
                <span className="text-sm not-italic">— Jk 1:22</span>
              </p>

              <Link
                href="/dashboard"
                className="mt-8 inline-flex items-center gap-2 rounded-lg border border-gold/30 bg-gold/10 px-6 py-3 text-gold transition-all hover:bg-gold/20"
              >
                Zobacz swój Panel Duchowy
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        <div className="mt-12 flex items-center justify-between">
          <button
            onClick={() => goToStage(-1)}
            disabled={currentStage === 0}
            className="flex items-center gap-2 rounded-lg border border-sacred-border px-5 py-2.5 text-sacred-text-muted transition-all hover:border-gold/30 hover:text-gold disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:border-sacred-border disabled:hover:text-sacred-text-muted"
          >
            <ArrowLeft className="h-4 w-4" />
            Wstecz
          </button>

          {currentStage < STAGES.length - 1 && (
            <button
              onClick={() => goToStage(1)}
              disabled={!canGoNext()}
              className="flex items-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-5 py-2.5 text-gold transition-all hover:bg-gold/20 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-gold/10"
            >
              Dalej
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
