"use client";

import { useState } from "react";
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
} from "lucide-react";
import Link from "next/link";

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function searchBible(query: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query, limit: "12" });
  const res = await fetch(`${API_BASE}/api/v1/bible/search?${params}`);
  if (!res.ok) throw new Error(`Błąd wyszukiwania: ${res.status}`);
  const data = await res.json();
  return data.results ?? [];
}

async function analyzePassage(
  reference: string,
  originalQuery: string
): Promise<AnalysisResult> {
  const question = `${reference} — ${originalQuery}`;
  const res = await fetch(`${API_BASE}/api/v1/bible/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      translation: "BT",
      include_magisterium: true,
      include_patristic: true,
      max_passages: 5,
    }),
  });
  if (!res.ok) throw new Error(`Błąd analizy: ${res.status}`);
  const data = await res.json();
  return {
    teologiczny: data.literal_sense || "Brak danych.",
    historyczny: data.allegorical_sense || "Brak danych.",
    psychologiczny: data.moral_sense || "Brak danych.",
    duchowy: data.anagogical_sense || "Brak danych.",
  };
}

function SkeletonBlock() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-4 w-3/4 rounded-full bg-[--color-sacred-surface-light]" />
      <div className="h-4 w-full rounded-full bg-[--color-sacred-surface-light]" />
      <div className="h-4 w-5/6 rounded-full bg-[--color-sacred-surface-light]" />
      <div className="h-4 w-2/3 rounded-full bg-[--color-sacred-surface-light]" />
    </div>
  );
}

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

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;

    setIsSearching(true);
    setSearchError(null);
    setSearchResults(null);
    setSelectedResult(null);
    setAnalysis(null);

    try {
      const results = await searchBible(q);
      setSearchResults(results);
    } catch {
      setSearchError(
        "Nie udało się połączyć z bazą danych Pisma Świętego. Sprawdź połączenie z serwerem."
      );
    } finally {
      setIsSearching(false);
    }
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
      setAnalysisError(
        "Nie udało się wygenerować analizy tego fragmentu. Spróbuj ponownie."
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleBackToResults = () => {
    setSelectedResult(null);
    setAnalysis(null);
    setAnalysisError(null);
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
            Wpisz słowo, frazę lub werset — przeszukamy całe Pismo Święte
            i znajdziemy wszystkie pasujące fragmenty
          </p>
        </div>

        {/* Search input */}
        <form onSubmit={handleSearch} className="mb-8">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-sacred-text-muted" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Np. 'miłość', 'zdrada', 'nadzieja', 'J 3:16', 'Kazanie na Górze'…"
              className="w-full rounded-xl border border-sacred-border bg-sacred-surface py-4 pl-12 pr-28 text-sacred-text placeholder-sacred-text-muted/50 transition-colors focus:border-gold/50 focus:outline-none"
            />
            <button
              type="submit"
              disabled={isSearching || !query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg bg-gold/10 px-5 py-2 text-sm font-medium text-gold transition-all hover:bg-gold/20 disabled:opacity-40"
            >
              {isSearching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Szukaj"
              )}
            </button>
          </div>
        </form>

        {/* ── Searching indicator ── */}
        {isSearching && (
          <div className="py-16 text-center">
            <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-gold/50" />
            <p className="font-scripture text-sacred-text-muted">
              Przeszukuję Pismo Święte…
            </p>
          </div>
        )}

        {/* ── Search error ── */}
        {searchError && !isSearching && (
          <div className="flex items-start gap-3 rounded-xl border border-sacred-red-light/30 bg-sacred-red-light/5 p-5 text-sacred-red-light">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <p className="text-sm">{searchError}</p>
          </div>
        )}

        {/* ── No results ── */}
        {searchResults !== null && searchResults.length === 0 && !isSearching && (
          <div className="py-16 text-center">
            <BookOpen className="mx-auto mb-4 h-12 w-12 text-sacred-text-muted/30" />
            <p className="font-scripture text-lg text-sacred-text-muted">
              Nie znaleziono fragmentów dla zapytania &ldquo;{query}&rdquo;
            </p>
            <p className="mt-2 text-sm text-sacred-text-muted/60">
              Spróbuj innego słowa lub sformułowania
            </p>
          </div>
        )}

        {/* ── Search results list ── */}
        {searchResults && searchResults.length > 0 && !selectedResult && !isSearching && (
          <div className="animate-fade-in">
            <p className="mb-4 text-sm text-sacred-text-muted">
              Znaleziono{" "}
              <span className="font-semibold text-parchment">
                {searchResults.length}
              </span>{" "}
              {searchResults.length === 1
                ? "fragment"
                : searchResults.length < 5
                ? "fragmenty"
                : "fragmentów"}{" "}
              dla &ldquo;{query}&rdquo;
            </p>
            <div className="space-y-3">
              {searchResults.map((result, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSelectResult(result)}
                  className="group w-full rounded-xl border border-sacred-border bg-sacred-surface p-5 text-left transition-all hover:border-gold/30 hover:bg-sacred-surface-light"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="mb-1 font-medium text-gold">
                        {result.reference}
                      </p>
                      <p className="line-clamp-3 text-sm leading-relaxed text-sacred-text/80">
                        {result.content}
                      </p>
                    </div>
                    <ChevronRight className="mt-0.5 h-5 w-5 shrink-0 text-sacred-text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-gold" />
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="rounded-full bg-gold/5 px-2 py-0.5 text-xs text-gold/60">
                      Trafność: {Math.round(result.score * 100)}%
                    </span>
                    {result.book && (
                      <span className="text-xs text-sacred-text-muted">
                        {result.book}
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Selected passage + analysis ── */}
        {selectedResult && (
          <div className="animate-fade-in">
            <button
              onClick={handleBackToResults}
              className="mb-5 inline-flex items-center gap-2 text-sm text-sacred-text-muted transition-colors hover:text-gold"
            >
              <ArrowLeft className="h-4 w-4" />
              Wróć do wyników
            </button>

            {/* Passage card */}
            <div className="mb-6 rounded-xl border border-gold/20 bg-sacred-surface p-6">
              <p className="font-heading mb-1 text-lg text-gold">
                {selectedResult.reference}
              </p>
              <p className="font-scripture leading-relaxed text-sacred-text">
                {selectedResult.content}
              </p>
              <p className="mt-3 text-xs text-sacred-text-muted/60">
                Biblia Tysiąclecia
              </p>
            </div>

            {/* Dimension tabs */}
            <div className="flex gap-1 rounded-xl border border-sacred-border bg-sacred-surface p-1">
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
            <div className="mt-4 min-h-[160px] rounded-xl border border-sacred-border bg-sacred-surface p-6 md:p-8">
              <h3 className="font-heading mb-4 text-xl text-gold">
                Wymiar{" "}
                {DIMENSION_TABS.find((t) => t.key === activeDimension)?.label}
              </h3>

              {isAnalyzing && <SkeletonBlock />}

              {analysisError && !isAnalyzing && (
                <div className="flex items-start gap-3 text-sacred-red-light">
                  <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                  <p className="text-sm">{analysisError}</p>
                </div>
              )}

              {analysis && !isAnalyzing && (
                <p className="leading-relaxed text-sacred-text/90">
                  {analysis[activeDimension]}
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── Empty state (initial) ── */}
        {!isSearching && searchResults === null && !searchError && (
          <div className="py-20 text-center">
            <BookOpen className="mx-auto mb-4 h-16 w-16 text-sacred-text-muted/30" />
            <p className="font-scripture text-lg text-sacred-text-muted/50">
              Wpisz słowo lub fragment, aby przeszukać Pismo Święte
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {["miłość", "nadzieja", "przebaczenie", "strach", "J 3,16"].map(
                (hint) => (
                  <button
                    key={hint}
                    onClick={() => {
                      setQuery(hint);
                    }}
                    className="rounded-full border border-sacred-border px-3 py-1 text-sm text-sacred-text-muted transition-colors hover:border-gold/30 hover:text-parchment"
                  >
                    {hint}
                  </button>
                )
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
