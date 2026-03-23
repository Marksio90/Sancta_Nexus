"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { ArrowLeft, ArrowRight, Heart, BookOpen, Flame, Eye, Footprints, Sparkles } from "lucide-react";
import Link from "next/link";
import { StageIndicator } from "@/components/ui/stage-indicator";
import { BreathingTimer } from "@/components/ui/breathing-timer";
import { ScriptureDisplay } from "@/components/ui/scripture-display";
import { useLectioStore } from "@/stores/lectio";
import { useProgressStore } from "@/stores/progress";
import { getLiturgicalInfo } from "@/lib/liturgical-season";
import type { LectioDivinaStage } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface LiturgicalContext {
  season: string;
  feast: string | null;
  readings: { label: string; reference: string; book: string; chapter: number }[];
}

async function fetchLiturgicalContext(): Promise<LiturgicalContext | null> {
  try {
    const today = new Date().toISOString().split("T")[0];
    const res = await fetch(`${API_BASE}/api/v1/lectio-divina/scripture/${today}`);
    if (res.ok) return res.json();
  } catch { /* backend offline */ }
  return null;
}

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

const STAGE_ICONS: Record<LectioDivinaStage, typeof Heart> = {
  welcome: Heart,
  lectio: BookOpen,
  meditatio: Eye,
  oratio: Flame,
  contemplatio: Heart,
  actio: Footprints,
};

/* ── Mock data (used when API is unavailable) ── */
const MOCK_SCRIPTURE = {
  book: "Ewangelia wg sw. Jana",
  chapter: 15,
  startVerse: 4,
  endVerse: 5,
  text: "Trwajcie we Mnie, a Ja w was trwac bede. Podobnie jak latorosl nie moze przynosic owocu sama z siebie — o ile nie trwa w winnym krzewie — tak samo i wy, jezeli we Mnie trwac nie bedziecie. Ja jestem krzewem winnym, wy — latoroslami. Kto trwa we Mnie, a Ja w nim, ten przynosi owoc obfity, poniewaz beze Mnie nic nie mozecie uczynic.",
  translation: "Biblia Tysiaclecia V",
  historicalContext: "Fragment ten pochodzi z Mowy Pozegnalnej Jezusa podczas Ostatniej Wieczerzy. Metafora winnego krzewu (gr. ampelos) byla dobrze znana w kulturze zydowskiej — Izrael byl czesto porownywany do winnicy Pana (Iz 5:1-7). Jezus nadaje tej metaforze nowe, glebsze znaczenie, wskazujac na osobista relacje z Nim jako zrodlo duchowego zycia.",
  patristicNote: "Sw. Augustyn: 'Latorosl nie daje zycia korzeniowi, lecz korzen latorosli. Tak i uczniowie nie daja Chrystusowi tego, czego potrzebuja, lecz od Chrystusa otrzymuja to, co jest im potrzebne do zycia.'",
  originalLanguageKey: "meno (gr.) — trwac, pozostawac, zamieszkiwac. Wskazuje na gleboka, osobista, trwala relacje.",
  catechismRef: "CCC 787 — 'Od poczatku Jezus wlaczyl swoich uczniow do swego zycia.'",
};

const MOCK_QUESTIONS = [
  { text: "Ktore slowo z tego fragmentu najbardziej przyciaga Twoja uwage i dlaczego?", layer: "literalis", scripture_echo: "trwajcie we Mnie" },
  { text: "W jaki sposob Jezus jest 'krzewem winnym' w Twoim codziennym zyciu?", layer: "allegoricus", scripture_echo: "Ja jestem krzewem winnym" },
  { text: "Co konkretnie przeszkadza Ci w 'przynoszeniu owocu obfitego'?", layer: "moralis", scripture_echo: "przynosi owoc obfity" },
  { text: "Gdybys mogl/a usiasc w ciszy z jednym slowem z tego fragmentu, ktore by to bylo?", layer: "anagogicus", scripture_echo: "" },
];

const MOCK_REFLECTION_LAYERS = {
  literalis: "Greckie 'meno' (trwac) pojawia sie w Ewangelii Jana az 40 razy. Dla sw. Jana 'trwanie' to nie statyczne 'bycie', lecz dynamiczna, zywa relacja z Chrystusem. Sw. Jan Chryzostom pisal: 'Trwac w Chrystusie to nie kwestia miejsca, lecz woli i milosci.'",
  allegoricus: "Krzew winny jest typem Chrystusa — tak jak Izrael byl winna latorosla Boga (Iz 5), tak Jezus jest prawdziwym krzewem, z ktorego czerpiemy zycie. Kazdy owoc — milosc, radosc, pokoj — jest owocem Ducha (Ga 5,22), nie naszej ludzkiej sily.",
  moralis: "Pytanie 'beze Mnie nic nie mozecie uczynic' jest zaproszeniem do pokory. Nie chodzi o ludzka bezradnosc, lecz o prawde, ze najglebsze dobro rodzi sie z relacji z Bogiem. Jakie 'owoce' w Twoim zyciu sa owocem wlasnego wysilku, a jakie sa darem Bozej laski?",
  anagogicus: "Obraz krzewu winnego otwiera przestrzen mistyczna: zjednoczenie z Chrystusem jest juz tutaj, na ziemi, zapowiedzia pelnego zjednoczenia w wiecznosci. Sw. Jan od Krzyza pisal: 'Dusza, ktora trwa w Bogu, jest jak latorosl w ogniu — plonie, ale nie spala sie, bo jej ogniem jest Milosc.'",
};

const MOCK_PRAYER = "Panie Jezu, Ty jestes prawdziwym Krzewem Winnym, a ja pragne byc Twoja latorosla. Pomoz mi trwac w Tobie kazdego dnia — w modlitwie, w sakramentach, w milosci do bliznich. Wiem, ze beze Ciebie nic nie moge uczynic. Oczysz mnie ze wszystkiego, co przeszkadza mi w przynoszeniu owocu. Napelnij mnie Twoim Duchem, abym zyl tak, jak Ty tego pragniesz. Przez Chrystusa, Pana naszego. Amen.";

const MOCK_CONTEMPLATION = {
  sacredWord: "Trwaj",
  sacredWordMeaning: "meno (gr.) — pozostawac w zywa, osobistej relacji z Bogiem",
  jesusPrayerRhythm: "Wdech: 'Panie Jezu Chryste...' Wydech: '...pozwol mi trwac w Tobie.'",
  closingPrayer: "Dziekuje Ci, Panie, za te chwile ciszy w Twoim winnym ogrodzie. Amen.",
};

const MOCK_CHALLENGE = {
  text: "Dzis poswiec 5 minut na cicha modlitwe ze slowem 'trwaj'. W kazdej chwili wyboru zatrzymaj sie i zapytaj: 'Panie, jak moge teraz trwac w Tobie?' Wieczorem zapisz jeden moment, w ktorym poczules/as Jego obecnosc.",
  category: "prayer",
  difficulty: "easy",
  virteFocus: "stalość",
  scriptureAnchor: "Kto trwa we Mnie, a Ja w nim, ten przynosi owoc obfity",
  eveningExamen: {
    retrospection: "Czy udalo ci sie dzis zatrzymac ze slowem 'trwaj'? W jakim momencie?",
    divinePresence: "Gdzie w tym dniu poczules/as najbardziej Boza obecnosc?",
    resolution: "Jaka mala praktyke 'trwania' chcesz kontynuowac jutro?",
  },
};

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: "łatwe",
  medium: "średnie",
  hard: "trudne",
  divine: "✦ Boski",
};

function DifficultBadge({ difficulty }: { difficulty: string }) {
  if (difficulty === "divine") {
    return (
      <span className="rounded-full border border-[--color-gold] bg-[--color-gold]/20 px-3 py-1 text-xs font-semibold text-[--color-gold] shadow-[0_0_8px_var(--color-gold,#d4af37)/40]">
        {DIFFICULTY_LABELS.divine}
      </span>
    );
  }
  return (
    <span className="rounded-full bg-[--color-sacred-surface-light] px-3 py-1 text-xs text-[--color-sacred-text-muted]">
      {DIFFICULTY_LABELS[difficulty] ?? difficulty}
    </span>
  );
}

export default function LectioDivinaPage() {
  const [currentStage, setCurrentStage] = useState<number>(0);
  const [emotion, setEmotion] = useState("");
  const [meditationResponse, setMeditationResponse] = useState("");
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [liturgicalCtx, setLiturgicalCtx] = useState<LiturgicalContext | null>(null);
  const { isLoading } = useLectioStore();
  const { recordSession } = useProgressStore();
  const sessionStartRef = useRef<Date>(new Date());
  const sessionRecordedRef = useRef(false);

  const stage = STAGES[currentStage];
  const StageIcon = STAGE_ICONS[stage];

  // Load liturgical context from backend on mount
  useEffect(() => {
    fetchLiturgicalContext().then(setLiturgicalCtx);
  }, []);

  // Record session when the user reaches Actio (final stage)
  useEffect(() => {
    if (stage === "actio" && !sessionRecordedRef.current) {
      sessionRecordedRef.current = true;
      const durationMinutes = Math.round(
        (Date.now() - sessionStartRef.current.getTime()) / 60000
      );
      recordSession({
        date: new Date().toISOString(),
        passageRef: `${MOCK_SCRIPTURE.book} ${MOCK_SCRIPTURE.chapter},${MOCK_SCRIPTURE.startVerse}-${MOCK_SCRIPTURE.endVerse}`,
        emotion: emotion || "nieznany",
        durationMinutes: Math.max(1, durationMinutes),
      });
    }
  }, [stage, emotion, recordSession]);

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
          className="mb-8 inline-flex items-center gap-2 text-sm text-[--color-sacred-text-muted] transition-colors hover:text-[--color-gold]"
        >
          <ArrowLeft className="h-4 w-4" />
          Powrot
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
              {/* Liturgical context banner */}
              {liturgicalCtx && (
                <div className="mb-6 rounded-xl border border-[--color-liturgical-accent]/20 bg-[--color-liturgical-glow] px-5 py-4 text-center">
                  <p className="text-xs tracking-widest uppercase text-[--color-sacred-text-muted]/50">
                    <Sparkles className="mr-1.5 inline h-3.5 w-3.5" />
                    Dziś w Kościele
                  </p>
                  {liturgicalCtx.feast && (
                    <p className="mt-1 text-sm font-medium text-[--color-parchment]">
                      {liturgicalCtx.feast}
                    </p>
                  )}
                  {liturgicalCtx.readings.length > 0 && (
                    <p className="mt-1 text-xs text-[--color-sacred-text-muted]/60">
                      Czytania: {liturgicalCtx.readings.map((r) => r.reference).join(" · ")}
                    </p>
                  )}
                </div>
              )}

              <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-[--color-gold]/30 bg-[--color-sacred-surface]">
                <Heart className="h-8 w-8 text-[--color-gold]" />
              </div>
              <h1 className="font-heading mb-4 text-3xl text-[--color-gold]">
                Jak sie dzis czujesz?
              </h1>
              <p className="mx-auto mb-8 max-w-md text-[--color-sacred-text-muted]">
                Podziel sie swoim stanem ducha. Pomoze to dobrac odpowiedni
                fragment Pisma Swietego i poprowadzic Twoja modlitwe.
              </p>
              <textarea
                value={emotion}
                onChange={(e) => setEmotion(e.target.value)}
                placeholder="Np. Czuje spokoj, ale tez lekki niepokoj o przyszlosc..."
                className="mx-auto block w-full max-w-lg resize-none rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-4 text-[--color-sacred-text] placeholder-[--color-sacred-text-muted]/50 transition-colors focus:border-[--color-gold]/50 focus:outline-none"
                rows={4}
              />
              <p className="mx-auto mt-4 max-w-md text-xs text-[--color-sacred-text-muted]/50">
                Twoje slowa sa bezpieczne. System nigdy nie osadza — tylko towarzyszy.
              </p>
            </div>
          )}

          {/* ── Lectio ── */}
          {stage === "lectio" && (
            <div className="animate-fade-in">
              <h2 className="font-heading mb-2 text-center text-2xl text-[--color-gold]">
                Lectio
              </h2>
              <p className="mb-8 text-center text-[--color-sacred-text-muted]">
                Czytaj uwazanie. Pozwol, aby slowa dotarly do Twojego serca.
              </p>

              <ScriptureDisplay
                book={MOCK_SCRIPTURE.book}
                chapter={MOCK_SCRIPTURE.chapter}
                startVerse={MOCK_SCRIPTURE.startVerse}
                endVerse={MOCK_SCRIPTURE.endVerse}
                text={MOCK_SCRIPTURE.text}
                translation={MOCK_SCRIPTURE.translation}
                historicalContext={MOCK_SCRIPTURE.historicalContext}
                patristicNote={MOCK_SCRIPTURE.patristicNote}
                originalLanguageKey={MOCK_SCRIPTURE.originalLanguageKey}
                catechismRef={MOCK_SCRIPTURE.catechismRef}
              />
            </div>
          )}

          {/* ── Meditatio ── */}
          {stage === "meditatio" && (
            <div className="animate-fade-in">
              <h2 className="font-heading mb-2 text-center text-2xl text-[--color-gold]">
                Meditatio
              </h2>
              <p className="mb-8 text-center text-[--color-sacred-text-muted]">
                Rozwazaj Slowo. Co Bog mowi do Ciebie przez ten fragment?
              </p>

              {/* Reflection layers (Quadriga) */}
              <div className="mb-8 space-y-4 animate-fade-in-stagger">
                {Object.entries(MOCK_REFLECTION_LAYERS).map(([layer, text]) => (
                  <div
                    key={layer}
                    className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5"
                  >
                    <h4 className="font-heading mb-2 text-xs uppercase tracking-wider text-[--color-gold]/60">
                      {layer === "literalis" && "Sensus Literalis — co tekst mowi"}
                      {layer === "allegoricus" && "Sensus Allegoricus — Chrystus w tekscie"}
                      {layer === "moralis" && "Sensus Moralis — co to znaczy dla mnie"}
                      {layer === "anagogicus" && "Sensus Anagogicus — ku wiecznosci"}
                    </h4>
                    <p className="text-sm leading-relaxed text-[--color-sacred-text-muted]">
                      {text}
                    </p>
                  </div>
                ))}
              </div>

              {/* Reflective questions */}
              <div className="mb-8 space-y-3">
                <h3 className="font-heading text-lg text-[--color-parchment]">
                  Pytania do refleksji
                </h3>
                {MOCK_QUESTIONS.map((question, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] p-4"
                  >
                    <p className="font-scripture text-[--color-gold-light]">
                      {question.text}
                    </p>
                    {question.scripture_echo && (
                      <p className="mt-1 text-xs text-[--color-sacred-text-muted]/50">
                        &ldquo;{question.scripture_echo}&rdquo;
                      </p>
                    )}
                  </div>
                ))}
              </div>

              <div>
                <label className="mb-2 block text-sm text-[--color-sacred-text-muted]">
                  Twoja refleksja
                </label>
                <textarea
                  value={meditationResponse}
                  onChange={(e) => setMeditationResponse(e.target.value)}
                  placeholder="Zapisz swoje przemyslenia..."
                  className="w-full resize-none rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-4 text-[--color-sacred-text] placeholder-[--color-sacred-text-muted]/50 transition-colors focus:border-[--color-gold]/50 focus:outline-none"
                  rows={6}
                />
              </div>
            </div>
          )}

          {/* ── Oratio ── */}
          {stage === "oratio" && (
            <div className="animate-fade-in">
              <h2 className="font-heading mb-2 text-center text-2xl text-[--color-gold]">
                Oratio
              </h2>
              <p className="mb-8 text-center text-[--color-sacred-text-muted]">
                Odpowiedz Bogu modlitwa. Oto modlitwa zainspirowana Twoja
                refleksja.
              </p>

              <div className="glow-candle relative overflow-hidden rounded-xl border border-[--color-gold]/20 bg-[--color-sacred-surface] p-8">
                <div className="pointer-events-none absolute right-4 top-4 text-4xl text-[--color-gold]/5">
                  ✝
                </div>
                <p className="font-scripture text-center text-lg leading-loose text-[--color-parchment]">
                  {MOCK_PRAYER}
                </p>
              </div>

              <p className="mt-6 text-center text-sm text-[--color-sacred-text-muted]">
                Mozesz odmowic te modlitwe wlasnymi slowami lub w ciszy serca.
              </p>
            </div>
          )}

          {/* ── Contemplatio ── */}
          {stage === "contemplatio" && (
            <div className="animate-fade-in">
              <h2 className="font-heading mb-2 text-center text-2xl text-[--color-gold]">
                Contemplatio
              </h2>
              <p className="mb-12 text-center text-[--color-sacred-text-muted]">
                Badz w ciszy przed Bogiem. Pozwol Mu dzialac.
              </p>

              <BreathingTimer
                durationMinutes={3}
                sacredWord={MOCK_CONTEMPLATION.sacredWord}
                sacredWordMeaning={MOCK_CONTEMPLATION.sacredWordMeaning}
                jesusPrayerRhythm={MOCK_CONTEMPLATION.jesusPrayerRhythm}
                closingPrayer={MOCK_CONTEMPLATION.closingPrayer}
              />
            </div>
          )}

          {/* ── Actio ── */}
          {stage === "actio" && (
            <div className="animate-fade-in text-center">
              <h2 className="font-heading mb-2 text-3xl text-[--color-gold]">Actio</h2>
              <p className="mb-8 text-[--color-sacred-text-muted]">
                Idz i zyj tym, co otrzymales/as.
              </p>

              <div className="mx-auto max-w-lg rounded-xl border border-[--color-gold]/20 bg-[--color-sacred-surface] p-8">
                <h3 className="font-heading mb-4 text-lg text-[--color-candlelight]">
                  Twoje dzisiejsze wyzwanie
                </h3>
                <p className="font-scripture leading-relaxed text-[--color-parchment]">
                  {MOCK_CHALLENGE.text}
                </p>

                {MOCK_CHALLENGE.scriptureAnchor && (
                  <p className="mt-4 text-xs text-[--color-gold]/50">
                    Zakotwiczenie: &ldquo;{MOCK_CHALLENGE.scriptureAnchor}&rdquo;
                  </p>
                )}

                <div className="mt-4 flex items-center justify-center gap-2">
                  <span className="rounded-full bg-[--color-gold]/10 px-3 py-1 text-xs text-[--color-gold]/70">
                    {MOCK_CHALLENGE.category}
                  </span>
                  <DifficultBadge difficulty={MOCK_CHALLENGE.difficulty} />
                </div>
              </div>

              {/* Evening Examen */}
              <div className="mx-auto mt-6 max-w-lg rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6 text-left">
                <h4 className="font-heading mb-3 text-sm uppercase tracking-wider text-[--color-gold]/60">
                  Rachunek sumienia wieczorny
                </h4>
                <div className="space-y-2 text-sm text-[--color-sacred-text-muted]">
                  <p>1. {MOCK_CHALLENGE.eveningExamen.retrospection}</p>
                  <p>2. {MOCK_CHALLENGE.eveningExamen.divinePresence}</p>
                  <p>3. {MOCK_CHALLENGE.eveningExamen.resolution}</p>
                </div>
              </div>

              <div className="sacred-divider mx-auto my-10 w-48" />

              <p className="font-scripture text-[--color-sacred-text-muted]">
                &ldquo;Badzcie wykonawcami slowa, a nie tylko
                sluchaczami&rdquo;
                <br />
                <span className="text-sm not-italic">— Jk 1:22</span>
              </p>

              <Link
                href="/dashboard"
                className="mt-8 inline-flex items-center gap-2 rounded-lg border border-[--color-gold]/30 bg-[--color-gold]/10 px-6 py-3 text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
              >
                Zobacz swoj Panel Duchowy
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
            className="flex items-center gap-2 rounded-lg border border-[--color-sacred-border] px-5 py-2.5 text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/30 hover:text-[--color-gold] disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ArrowLeft className="h-4 w-4" />
            Wstecz
          </button>

          {currentStage < STAGES.length - 1 && (
            <button
              onClick={() => goToStage(1)}
              disabled={!canGoNext() || isLoading}
              className="flex items-center gap-2 rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-5 py-2.5 text-[--color-gold] transition-all hover:bg-[--color-gold]/20 disabled:cursor-not-allowed disabled:opacity-30"
            >
              {isLoading ? "Modlitwa..." : "Dalej"}
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
