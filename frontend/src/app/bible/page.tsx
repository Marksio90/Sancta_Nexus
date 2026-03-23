"use client";

import { useState, useRef } from "react";
import {
  Search,
  BookOpen,
  Clock,
  Brain,
  Flame,
  ArrowLeft,
  ChevronRight,
  AlertCircle,
  Loader2,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

/* ── Types ─────────────────────────────────────────────────────────────── */

type Dimension = "teologiczny" | "historyczny" | "psychologiczny" | "duchowy";

interface DimensionTab {
  key: Dimension;
  label: string;
  sublabel: string;
  icon: typeof BookOpen;
  color: string;
}

interface SearchResult {
  reference: string;
  content: string;
  score: number;
  book: string;
  chapter: number;
  verse: number;
}

interface AnalysisResult {
  teologiczny: string;
  historyczny: string;
  psychologiczny: string;
  duchowy: string;
}

/* ── Constants ─────────────────────────────────────────────────────────── */

const DIMENSION_TABS: DimensionTab[] = [
  {
    key: "teologiczny",
    label: "Teologiczny",
    sublabel: "Sensus litteralis",
    icon: BookOpen,
    color: "text-amber-400",
  },
  {
    key: "historyczny",
    label: "Historyczny",
    sublabel: "Sensus allegoricus",
    icon: Clock,
    color: "text-blue-400",
  },
  {
    key: "psychologiczny",
    label: "Psychologiczny",
    sublabel: "Sensus moralis",
    icon: Brain,
    color: "text-purple-400",
  },
  {
    key: "duchowy",
    label: "Duchowy",
    sublabel: "Sensus anagogicus",
    icon: Flame,
    color: "text-rose-400",
  },
];

const SEARCH_HINTS = [
  "miłość",
  "nadzieja",
  "przebaczenie",
  "strach",
  "zdrada",
  "wiara",
  "modlitwa",
  "miłosierdzie",
  "J 3,16",
  "Ps 23",
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ── API helpers ───────────────────────────────────────────────────────── */

async function searchBible(query: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query, limit: "15" });
  const res = await fetch(`${API_BASE}/api/v1/bible/search?${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.results ?? [];
}

async function analyzePassage(
  reference: string,
  originalQuery: string
): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/api/v1/bible/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: `${reference} — ${originalQuery}`,
      translation: "BT",
      include_magisterium: true,
      include_patristic: true,
      max_passages: 5,
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return {
    teologiczny: data.literal_sense || "Analiza niedostępna.",
    historyczny: data.allegorical_sense || "Analiza niedostępna.",
    psychologiczny: data.moral_sense || "Analiza niedostępna.",
    duchowy: data.anagogical_sense || "Analiza niedostępna.",
  };
}

/* ── Skeleton loader ───────────────────────────────────────────────────── */

function SkeletonText({ lines = 4 }: { lines?: number }) {
  const widths = ["w-3/4", "w-full", "w-5/6", "w-2/3", "w-4/5", "w-full"];
  return (
    <div className="animate-pulse space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`h-4 rounded-full bg-[--color-sacred-surface-light] ${widths[i % widths.length]}`}
        />
      ))}
    </div>
  );
}

/* ── Score badge ───────────────────────────────────────────────────────── */

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80
      ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20"
      : pct >= 60
        ? "text-amber-400 bg-amber-400/10 border-amber-400/20"
        : "text-[--color-sacred-text-muted] bg-[--color-sacred-surface-light] border-[--color-sacred-border]";
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-xs font-medium ${color}`}
    >
      {pct}% trafność
    </span>
  );
}

/* ── Main component ────────────────────────────────────────────────────── */

export default function BiblePage() {
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [activeDimension, setActiveDimension] = useState<Dimension>("teologiczny");

  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearch = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    setQuery(trimmed);
    setIsSearching(true);
    setSearchError(null);
    setSearchResults(null);
    setSelectedResult(null);
    setAnalysis(null);
    try {
      const results = await searchBible(trimmed);
      setSearchResults(results);
    } catch {
      setSearchError(
        "Nie udało się połączyć z bazą Pisma Świętego. Upewnij się, że serwer jest uruchomiony."
      );
    } finally {
      setIsSearching(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch(query);
  };

  const handleSelectResult = async (result: SearchResult) => {
    setSelectedResult(result);
    setAnalysis(null);
    setAnalysisError(null);
    setIsAnalyzing(true);
    setActiveDimension("teologiczny");
    try {
      const data = await analyzePassage(result.reference, query);
      setAnalysis(data);
    } catch {
      setAnalysisError("Nie udało się wygenerować analizy. Spróbuj ponownie.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleBackToResults = () => {
    setSelectedResult(null);
    setAnalysis(null);
    setAnalysisError(null);
  };

  const handleHintClick = (hint: string) => {
    setQuery(hint);
    handleSearch(hint);
    inputRef.current?.focus();
  };

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-4xl">

        {/* Back */}
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-2 text-sm text-sacred-text-muted transition-colors hover:text-gold"
        >
          <ArrowLeft className="h-4 w-4" />
          Strona główna
        </Link>

        {/* Header */}
        <div className="mb-10 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-[--color-gold]/20 bg-[--color-gold]/8">
            <Sparkles className="h-7 w-7 text-[--color-gold]" />
          </div>
          <h1 className="font-heading mb-3 text-4xl text-gold md:text-5xl">
            Interaktywna Biblia
          </h1>
          <p className="mx-auto max-w-md text-[--color-sacred-text-muted]/70">
            Wpisz słowo, frazę lub sygnaturę — przeszukamy całe{" "}
            <span className="font-medium text-[--color-parchment]/70">
              31 102 wersety
            </span>{" "}
            katolickiego kanonu
          </p>
        </div>

        {/* Search bar */}
        <form onSubmit={handleFormSubmit} className="mb-6">
          <div className="relative">
            <Search className="absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[--color-sacred-text-muted]/50" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Np. 'miłość', 'zdrada', 'nadzieja', 'J 3,16', 'Kazanie na Górze'…"
              className="w-full rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] py-5 pl-14 pr-32 text-[--color-sacred-text] placeholder-[--color-sacred-text-muted]/40 shadow-[0_4px_24px_rgba(0,0,0,0.2)] transition-all focus:border-[--color-gold]/40 focus:outline-none focus:shadow-[0_4px_32px_rgba(212,175,55,0.08)]"
            />
            <button
              type="submit"
              disabled={isSearching || !query.trim()}
              className="absolute right-3 top-1/2 -translate-y-1/2 inline-flex items-center gap-2 rounded-xl bg-[--color-gold]/15 px-5 py-2.5 text-sm font-semibold text-[--color-gold] transition-all hover:bg-[--color-gold]/25 disabled:opacity-40"
            >
              {isSearching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Szukaj"
              )}
            </button>
          </div>
        </form>

        {/* Search hints */}
        {!isSearching && searchResults === null && !searchError && (
          <div className="mb-10 flex flex-wrap justify-center gap-2">
            {SEARCH_HINTS.map((hint) => (
              <button
                key={hint}
                onClick={() => handleHintClick(hint)}
                className="rounded-full border border-[--color-sacred-border] px-4 py-1.5 text-sm text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/30 hover:bg-[--color-gold]/5 hover:text-[--color-parchment]"
              >
                {hint}
              </button>
            ))}
          </div>
        )}

        {/* ── Searching ── */}
        {isSearching && (
          <div className="flex flex-col items-center py-24 text-center">
            <div className="relative mb-6">
              <div className="h-16 w-16 rounded-full border border-[--color-gold]/10 bg-[--color-sacred-surface]" />
              <Loader2 className="absolute inset-0 m-auto h-8 w-8 animate-spin text-[--color-gold]/50" />
            </div>
            <p className="font-scripture text-lg text-[--color-sacred-text-muted]">
              Przeszukuję Pismo Święte&hellip;
            </p>
            <p className="mt-1 text-xs text-[--color-sacred-text-muted]/40">
              Szukam w 31 102 wersetach
            </p>
          </div>
        )}

        {/* ── Error ── */}
        {searchError && !isSearching && (
          <div className="flex items-start gap-4 rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
            <div>
              <p className="font-medium text-red-400">Błąd połączenia</p>
              <p className="mt-1 text-sm text-red-400/70">{searchError}</p>
            </div>
          </div>
        )}

        {/* ── No results ── */}
        {searchResults !== null && searchResults.length === 0 && !isSearching && (
          <div className="flex flex-col items-center py-20 text-center">
            <BookOpen className="mb-4 h-14 w-14 text-[--color-sacred-text-muted]/20" />
            <p className="font-scripture text-lg text-[--color-sacred-text-muted]">
              Nie znaleziono fragmentów dla &ldquo;{query}&rdquo;
            </p>
            <p className="mt-2 text-sm text-[--color-sacred-text-muted]/50">
              Spróbuj innego słowa lub uproszczonej frazy
            </p>
          </div>
        )}

        {/* ── Results list ── */}
        {searchResults && searchResults.length > 0 && !selectedResult && !isSearching && (
          <div className="animate-fade-in">
            <div className="mb-5 flex items-center justify-between">
              <p className="text-sm text-[--color-sacred-text-muted]">
                Znaleziono{" "}
                <span className="font-semibold text-[--color-parchment]">
                  {searchResults.length}
                </span>{" "}
                {searchResults.length === 1
                  ? "fragment"
                  : searchResults.length < 5
                    ? "fragmenty"
                    : "fragmentów"}{" "}
                — kliknij, aby przeanalizować
              </p>
            </div>

            <div className="space-y-3">
              {searchResults.map((result, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSelectResult(result)}
                  className="group w-full rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5 text-left transition-all duration-200 hover:border-[--color-gold]/30 hover:bg-[--color-sacred-surface-light] hover:shadow-[0_4px_20px_rgba(0,0,0,0.25)]"
                >
                  <div className="flex items-start gap-4">
                    {/* Index number */}
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[--color-sacred-border] text-xs text-[--color-sacred-text-muted] transition-colors group-hover:border-[--color-gold]/30 group-hover:text-[--color-gold]">
                      {idx + 1}
                    </span>

                    <div className="flex-1 min-w-0">
                      {/* Reference */}
                      <div className="mb-1.5 flex items-center gap-3 flex-wrap">
                        <span className="font-heading text-base text-[--color-gold]">
                          {result.reference}
                        </span>
                        <ScoreBadge score={result.score} />
                      </div>
                      {/* Content preview */}
                      <p className="line-clamp-2 text-sm leading-relaxed text-[--color-sacred-text]/70">
                        {result.content}
                      </p>
                    </div>

                    <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-[--color-sacred-text-muted]/40 transition-all duration-200 group-hover:translate-x-0.5 group-hover:text-[--color-gold]" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Selected passage + analysis ── */}
        {selectedResult && (
          <div className="animate-fade-in">

            {/* Back to results */}
            <button
              onClick={handleBackToResults}
              className="mb-6 inline-flex items-center gap-2 text-sm text-[--color-sacred-text-muted] transition-colors hover:text-[--color-gold]"
            >
              <ArrowLeft className="h-4 w-4" />
              Wróć do wyników ({searchResults?.length})
            </button>

            {/* Passage */}
            <div className="mb-6 rounded-2xl border border-[--color-gold]/20 bg-[--color-sacred-surface] p-7 shadow-[0_4px_32px_rgba(212,175,55,0.05)]">
              <div className="mb-4 flex items-center gap-3">
                <BookOpen className="h-5 w-5 text-[--color-gold]/60" />
                <span className="font-heading text-lg text-[--color-gold]">
                  {selectedResult.reference}
                </span>
                <ScoreBadge score={selectedResult.score} />
              </div>
              <blockquote className="border-l-2 border-[--color-gold]/20 pl-5">
                <p className="font-scripture text-lg leading-relaxed text-[--color-sacred-text]">
                  {selectedResult.content}
                </p>
              </blockquote>
              <p className="mt-4 text-xs text-[--color-sacred-text-muted]/40">
                Biblia Tysiąclecia · Wydanie V
              </p>
            </div>

            {/* Quadriga label */}
            <div className="mb-3 text-center">
              <p className="text-xs tracking-[0.3em] uppercase text-[--color-sacred-text-muted]/40">
                Quadriga — cztery sensy Pisma Świętego
              </p>
            </div>

            {/* Dimension tabs */}
            <div className="mb-4 grid grid-cols-4 gap-1.5 rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-1.5">
              {DIMENSION_TABS.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeDimension === tab.key;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveDimension(tab.key)}
                    className={`flex flex-col items-center gap-1 rounded-xl px-2 py-3 text-center transition-all duration-200 ${
                      isActive
                        ? "border border-[--color-gold]/25 bg-[--color-gold]/10 shadow-sm"
                        : "hover:bg-[--color-sacred-surface-light]"
                    }`}
                  >
                    <Icon
                      className={`h-4 w-4 ${isActive ? tab.color : "text-[--color-sacred-text-muted]/50"}`}
                    />
                    <span
                      className={`text-xs font-medium ${isActive ? "text-[--color-gold]" : "text-[--color-sacred-text-muted]"}`}
                    >
                      <span className="hidden sm:inline">{tab.label}</span>
                      <span className="sm:hidden">{tab.label.slice(0, 3)}</span>
                    </span>
                    <span className="hidden text-[10px] text-[--color-sacred-text-muted]/30 sm:block">
                      {tab.sublabel}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Dimension content */}
            <div className="min-h-[200px] rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-7">
              {(() => {
                const tab = DIMENSION_TABS.find((t) => t.key === activeDimension)!;
                const Icon = tab.icon;
                return (
                  <>
                    <div className="mb-5 flex items-center gap-3">
                      <Icon className={`h-5 w-5 ${tab.color}`} />
                      <div>
                        <h3 className="font-heading text-lg text-[--color-gold]">
                          Wymiar {tab.label}
                        </h3>
                        <p className="text-xs text-[--color-sacred-text-muted]/40">
                          {tab.sublabel}
                        </p>
                      </div>
                    </div>

                    {isAnalyzing && <SkeletonText lines={5} />}

                    {analysisError && !isAnalyzing && (
                      <div className="flex items-start gap-3 text-red-400">
                        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                        <p className="text-sm">{analysisError}</p>
                      </div>
                    )}

                    {analysis && !isAnalyzing && (
                      <p className="leading-relaxed text-[--color-sacred-text]/85">
                        {analysis[activeDimension]}
                      </p>
                    )}
                  </>
                );
              })()}
            </div>
          </div>
        )}

        {/* ── Initial empty state ── */}
        {!isSearching && searchResults === null && !searchError && (
          <div className="flex flex-col items-center py-24 text-center">
            <div className="relative mb-6">
              <BookOpen className="h-20 w-20 text-[--color-sacred-text-muted]/10" />
              <Sparkles className="absolute -top-1 -right-1 h-6 w-6 text-[--color-gold]/20" />
            </div>
            <p className="font-scripture text-xl text-[--color-sacred-text-muted]/40">
              &ldquo;Szukajcie, a znajdziecie&rdquo;
            </p>
            <p className="mt-1 text-xs text-[--color-sacred-text-muted]/25">
              Mt 7,7
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
