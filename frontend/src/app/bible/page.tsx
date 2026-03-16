"use client";

import { useState } from "react";
import { Search, BookOpen, Clock, Brain, Flame, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { ScriptureDisplay } from "@/components/ui/scripture-display";

type Dimension = "teologiczny" | "historyczny" | "psychologiczny" | "duchowy";

interface DimensionTab {
  key: Dimension;
  label: string;
  icon: typeof BookOpen;
}

const DIMENSION_TABS: DimensionTab[] = [
  { key: "teologiczny", label: "Teologiczny", icon: BookOpen },
  { key: "historyczny", label: "Historyczny", icon: Clock },
  { key: "psychologiczny", label: "Psychologiczny", icon: Brain },
  { key: "duchowy", label: "Duchowy", icon: Flame },
];

/* ── Mock data ── */
const MOCK_RESPONSES: Record<Dimension, string> = {
  teologiczny:
    "Fragment Łk 15:11-32 przedstawia jedną z najważniejszych przypowieści Jezusa o miłosierdziu Bożym. Ojciec w przypowieści symbolizuje Boga, który nie wymaga od grzesznika pełnego rozliczenia, lecz wychodzi mu naprzeciw. Teologia miłosierdzia tutaj zawarta stoi w kontraście do legalizmu faryzeuszy (symbolizowanego przez starszego brata). Kluczowe pojęcie 'splanchnistheis' (wzruszył się głęboko) opisuje visceralne, macierzyńskie współczucie Boga.",
  historyczny:
    "Kontekst historyczny: W społeczeństwie żydowskim I wieku, prośba syna o podział majątku za życia ojca była równoznaczna z życzeniem mu śmierci — akt głębokiej hańby. Syn udaje się do 'dalekiego kraju' (prawdopodobnie tereny pogańskie), gdzie traci majątek. Pasienie świń stanowiło najniższy punkt upadku dla Żyda, gdyż świnie były zwierzętami nieczystymi (Kpł 11:7). Przywitanie ojca — bieg, uścisk, pierścień — naruszało normy godności patriarchy w kulturze bliskowschodniej.",
  psychologiczny:
    "Z perspektywy psychologicznej, przypowieść opisuje pełen cykl nawrócenia: od fałszywego poczucia autonomii, przez kryzys egzystencjalny, aż po reintegrację z rodziną. Młodszy syn przechodzi przez etapy: omnipotencja → konfrontacja z rzeczywistością → wstyd → pokora → przywrócenie tożsamości. Starszy brat reprezentuje mechanizm obronny 'sprawiedliwego gniewu', maskujący głębszą potrzebę bezwarunkowej akceptacji.",
  duchowy:
    "W tradycji duchowej, przypowieść o synu marnotrawnym jest mapą drogi duchowej każdego chrześcijanina. Ojcowie Kościoła widzieli w niej trzy etapy życia duchowego: odejście (grzech pierworodny), nawrócenie (droga oczyszczenia) i powrót do domu Ojca (zjednoczenie). Św. Augustyn widział w niej swoją własną historię. W praktyce modlitewnej, warto utożsamić się z każdą postacią: synem marnotrawnym, starszym bratem i ojcem.",
};

const MOCK_PASSAGE = {
  book: "Ewangelia wg św. Łukasza",
  chapter: 15,
  startVerse: 20,
  endVerse: 24,
  text: "Wybrał się więc i poszedł do swojego ojca. A gdy był jeszcze daleko, ujrzał go jego ojciec i wzruszył się głęboko; wybiegł naprzeciw niego, rzucił mu się na szyję i ucałował go. A syn rzekł do niego: 'Ojcze, zgrzeszyłem przeciw Bogu i względem ciebie, już nie jestem godzien nazywać się twoim synem'. Lecz ojciec rzekł do swoich sług: 'Przynieście szybko najlepszą szatę i ubierzcie go; dajcie mu też pierścień na rękę i sandały na nogi!'",
  translation: "Biblia Tysiąclecia",
};

export default function BiblePage() {
  const [query, setQuery] = useState("");
  const [activeDimension, setActiveDimension] =
    useState<Dimension>("teologiczny");
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setHasSearched(true);
    }
  };

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-2 text-sm text-sacred-text-muted transition-colors hover:text-gold"
        >
          <ArrowLeft className="h-4 w-4" />
          Powrót
        </Link>

        <div className="mb-10 text-center">
          <h1 className="font-heading mb-3 text-3xl text-gold md:text-4xl">
            Interaktywna Biblia
          </h1>
          <p className="text-sacred-text-muted">
            Zadaj pytanie o Pismo Święte i otrzymaj odpowiedź w czterech
            wymiarach
          </p>
        </div>

        {/* Search input */}
        <form onSubmit={handleSearch} className="mb-10">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-sacred-text-muted" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Np. 'Co oznacza przypowieść o synu marnotrawnym?' lub 'J 3:16'"
              className="w-full rounded-xl border border-sacred-border bg-sacred-surface py-4 pl-12 pr-4 text-sacred-text placeholder-sacred-text-muted/50 transition-colors focus:border-gold/50 focus:outline-none"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg bg-gold/10 px-5 py-2 text-sm font-medium text-gold transition-all hover:bg-gold/20"
            >
              Szukaj
            </button>
          </div>
        </form>

        {hasSearched ? (
          <div className="animate-fade-in">
            {/* Scripture passage */}
            <ScriptureDisplay
              book={MOCK_PASSAGE.book}
              chapter={MOCK_PASSAGE.chapter}
              startVerse={MOCK_PASSAGE.startVerse}
              endVerse={MOCK_PASSAGE.endVerse}
              text={MOCK_PASSAGE.text}
              translation={MOCK_PASSAGE.translation}
            />

            {/* Dimension tabs */}
            <div className="mt-8 flex gap-1 rounded-xl border border-sacred-border bg-sacred-surface p-1">
              {DIMENSION_TABS.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeDimension === tab.key;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveDimension(tab.key)}
                    className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-3 text-sm font-medium transition-all ${
                      isActive
                        ? "border border-gold/30 bg-gold/10 text-gold"
                        : "text-sacred-text-muted hover:text-parchment"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span className="hidden sm:inline">{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Dimension content */}
            <div className="mt-6 rounded-xl border border-sacred-border bg-sacred-surface p-6 md:p-8">
              <h3 className="font-heading mb-4 text-xl text-gold">
                Wymiar{" "}
                {
                  DIMENSION_TABS.find((t) => t.key === activeDimension)
                    ?.label
                }
              </h3>
              <p className="leading-relaxed text-sacred-text/90">
                {MOCK_RESPONSES[activeDimension]}
              </p>
            </div>
          </div>
        ) : (
          <div className="py-20 text-center">
            <BookOpen className="mx-auto mb-4 h-16 w-16 text-sacred-text-muted/30" />
            <p className="font-scripture text-lg text-sacred-text-muted/50">
              Wpisz pytanie lub fragment biblijny, aby rozpocząć
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
