"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  Search,
  Shield,
  BookMarked,
  Trash2,
  X,
  Check,
  ChevronLeft,
  ChevronRight,
  Edit3,
  TrendingUp,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import {
  useJournalStore,
  JournalEntry,
  CreateEntryData,
  UpdateEntryData,
} from "@/stores/journal";
import { useInsightsStore, PATTERN_LABELS } from "@/stores/insights";

/* ── Constants ───────────────────────────────────────────────────────────── */
const MOODS = [
  "spokój",
  "radość",
  "wdzięczność",
  "smutek",
  "niepokój",
  "nadzieja",
  "zagubienie",
  "miłość",
  "tęsknota",
  "pokuta",
];

const MOOD_COLORS: Record<string, string> = {
  spokój: "bg-blue-900/30 text-blue-300 border-blue-700/30",
  radość: "bg-yellow-900/30 text-yellow-300 border-yellow-700/30",
  wdzięczność: "bg-green-900/30 text-green-300 border-green-700/30",
  smutek: "bg-slate-800/40 text-slate-400 border-slate-700/30",
  niepokój: "bg-orange-900/30 text-orange-300 border-orange-700/30",
  nadzieja: "bg-emerald-900/30 text-emerald-300 border-emerald-700/30",
  zagubienie: "bg-gray-800/40 text-gray-400 border-gray-700/30",
  miłość: "bg-rose-900/30 text-rose-300 border-rose-700/30",
  tęsknota: "bg-violet-900/30 text-violet-300 border-violet-700/30",
  pokuta: "bg-purple-900/30 text-purple-300 border-purple-700/30",
};

/* ── Entry form ──────────────────────────────────────────────────────────── */
interface EntryFormProps {
  initial?: JournalEntry;
  onSave: (data: CreateEntryData) => Promise<void>;
  onCancel: () => void;
  isSaving: boolean;
}

function EntryForm({ initial, onSave, onCancel, isSaving }: EntryFormProps) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [content, setContent] = useState(initial?.content ?? "");
  const [mood, setMood] = useState(initial?.mood ?? "");
  const [scriptureRef, setScriptureRef] = useState(
    initial?.scripture_reference ?? ""
  );
  const [tagsInput, setTagsInput] = useState(
    initial?.tags?.join(", ") ?? ""
  );
  const [formError, setFormError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) {
      setFormError("Treść wpisu jest wymagana.");
      return;
    }
    setFormError("");
    const tags = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    await onSave({
      title: title.trim() || undefined,
      content: content.trim(),
      mood: mood || undefined,
      scripture_reference: scriptureRef.trim() || undefined,
      tags: tags.length > 0 ? tags : undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Title */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Tytuł (opcjonalny)
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Nadaj tytuł wpisowi…"
          className="w-full rounded-lg border border-white/10 bg-[#0d0b1a] px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:border-[#d4af37]/50 focus:outline-none"
        />
      </div>

      {/* Content */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Refleksja <span className="text-[#d4af37]">*</span>
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Napisz swoją refleksję, modlitwę lub owoc Lectio Divina…"
          rows={6}
          className="w-full resize-y rounded-lg border border-white/10 bg-[#0d0b1a] px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:border-[#d4af37]/50 focus:outline-none"
        />
        {formError && (
          <p className="mt-1 text-xs text-red-400">{formError}</p>
        )}
      </div>

      {/* Mood */}
      <div>
        <label className="mb-2 block text-xs font-medium text-gray-500">
          Nastrój duchowy (opcjonalny)
        </label>
        <div className="flex flex-wrap gap-2">
          {MOODS.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMood(mood === m ? "" : m)}
              className={`rounded-full border px-3 py-1 text-xs transition-all ${
                mood === m
                  ? "border-[#d4af37]/50 bg-[#d4af37]/15 text-[#d4af37]"
                  : "border-white/10 bg-white/5 text-gray-500 hover:border-[#d4af37]/25"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Scripture reference */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Odniesienie biblijne (opcjonalne)
        </label>
        <input
          type="text"
          value={scriptureRef}
          onChange={(e) => setScriptureRef(e.target.value)}
          placeholder="np. J 15,9"
          className="w-full rounded-lg border border-white/10 bg-[#0d0b1a] px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:border-[#d4af37]/50 focus:outline-none"
        />
      </div>

      {/* Tags */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Tagi (opcjonalne, oddzielone przecinkami)
        </label>
        <input
          type="text"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          placeholder="np. modlitwa, pokój, Lectio Divina"
          className="w-full rounded-lg border border-white/10 bg-[#0d0b1a] px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:border-[#d4af37]/50 focus:outline-none"
        />
      </div>

      {/* Buttons */}
      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={isSaving}
          className="flex items-center gap-2 rounded-lg border border-[#d4af37]/40 bg-[#d4af37]/10 px-5 py-2.5 text-sm font-medium text-[#d4af37] transition-all hover:bg-[#d4af37]/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Check className="h-4 w-4" />
          {isSaving ? "Zapisywanie…" : "Zapisz wpis"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm text-gray-500 transition-all hover:text-gray-200"
        >
          <X className="h-4 w-4" />
          Anuluj
        </button>
      </div>
    </form>
  );
}

/* ── Entry card ──────────────────────────────────────────────────────────── */
function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString("pl-PL", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

/* ── Main page ───────────────────────────────────────────────────────────── */
type ViewMode = "list" | "create" | "edit" | "detail";

export default function DziennikPage() {
  const router = useRouter();
  const { isAuthenticated, loadFromStorage } = useAuthStore();
  const {
    entries,
    total,
    currentPage,
    isLoading,
    error,
    loadEntries,
    createEntry,
    updateEntry,
    deleteEntry,
    clearError,
  } = useJournalStore();

  const { data: insights, loading: insightsLoading, fetch: fetchInsights } = useInsightsStore();

  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null);
  const [search, setSearch] = useState("");
  const [moodFilter, setMoodFilter] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [showInsights, setShowInsights] = useState(false);

  /* ── Auth check ─────────────────────────────────────────────────────── */
  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

  /* ── Load entries ───────────────────────────────────────────────────── */
  const fetchEntries = useCallback(
    (page: number = 1) => {
      loadEntries(page, search || undefined, moodFilter || undefined);
    },
    [loadEntries, search, moodFilter]
  );

  useEffect(() => {
    if (isAuthenticated) {
      fetchEntries(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, search, moodFilter]);

  /* ── Create ─────────────────────────────────────────────────────────── */
  const handleCreate = async (data: CreateEntryData) => {
    setIsSaving(true);
    try {
      await createEntry(data);
      setViewMode("list");
    } catch {
      // Error is set in the store
    } finally {
      setIsSaving(false);
    }
  };

  /* ── Update ─────────────────────────────────────────────────────────── */
  const handleUpdate = async (data: UpdateEntryData) => {
    if (!selectedEntry) return;
    setIsSaving(true);
    try {
      await updateEntry(selectedEntry.id, data);
      setViewMode("list");
      setSelectedEntry(null);
    } catch {
      // Error is set in the store
    } finally {
      setIsSaving(false);
    }
  };

  /* ── Delete ─────────────────────────────────────────────────────────── */
  const handleDelete = async (id: string) => {
    try {
      await deleteEntry(id);
      if (selectedEntry?.id === id) {
        setSelectedEntry(null);
        setViewMode("list");
      }
      setDeleteConfirm(null);
    } catch {
      // Error handled in store
    }
  };

  const totalPages = Math.ceil(total / 20);

  if (!isAuthenticated) return null;

  /* ── Create / Edit form view ─────────────────────────────────────────── */
  if (viewMode === "create" || viewMode === "edit") {
    return (
      <div className="min-h-screen px-4 py-8">
        <div className="mx-auto w-full max-w-2xl">
          <button
            onClick={() => {
              setViewMode("list");
              setSelectedEntry(null);
              clearError();
            }}
            className="mb-6 inline-flex items-center gap-2 text-sm text-gray-500 transition-colors hover:text-[#d4af37]"
          >
            <ChevronLeft className="h-4 w-4" />
            Powrót do dziennika
          </button>

          <h1 className="font-heading mb-6 text-2xl text-[#d4af37]">
            {viewMode === "create" ? "Nowy wpis" : "Edytuj wpis"}
          </h1>

          {error && (
            <div className="mb-4 rounded-lg border border-red-800/30 bg-red-900/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="rounded-xl border border-white/10 bg-white/5 p-6">
            <EntryForm
              initial={viewMode === "edit" ? selectedEntry ?? undefined : undefined}
              onSave={viewMode === "create" ? handleCreate : handleUpdate}
              onCancel={() => {
                setViewMode("list");
                setSelectedEntry(null);
                clearError();
              }}
              isSaving={isSaving}
            />
          </div>
        </div>
      </div>
    );
  }

  /* ── Detail view ────────────────────────────────────────────────────── */
  if (viewMode === "detail" && selectedEntry) {
    return (
      <div className="min-h-screen px-4 py-8">
        <div className="mx-auto w-full max-w-2xl">
          <button
            onClick={() => {
              setViewMode("list");
              setSelectedEntry(null);
            }}
            className="mb-6 inline-flex items-center gap-2 text-sm text-gray-500 transition-colors hover:text-[#d4af37]"
          >
            <ChevronLeft className="h-4 w-4" />
            Powrót do dziennika
          </button>

          <div className="rounded-xl border border-white/10 bg-white/5 p-6">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                {selectedEntry.title && (
                  <h2 className="font-heading text-xl text-[#d4af37] mb-1">
                    {selectedEntry.title}
                  </h2>
                )}
                <p className="text-xs text-gray-500/60">
                  {formatDate(selectedEntry.created_at)}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setViewMode("edit")}
                  className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-xs text-gray-500 transition-all hover:border-[#d4af37]/30 hover:text-[#d4af37]"
                >
                  <Edit3 className="h-3.5 w-3.5" />
                  Edytuj
                </button>
                {deleteConfirm === selectedEntry.id ? (
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleDelete(selectedEntry.id)}
                      className="rounded-lg border border-red-700/40 bg-red-900/20 px-3 py-2 text-xs text-red-400 transition-all hover:bg-red-900/40"
                    >
                      Potwierdź
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="rounded-lg border border-white/10 px-3 py-2 text-xs text-gray-500"
                    >
                      Anuluj
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(selectedEntry.id)}
                    className="flex items-center gap-1.5 rounded-lg border border-red-900/30 px-3 py-2 text-xs text-red-500/70 transition-all hover:border-red-700/40 hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Usuń
                  </button>
                )}
              </div>
            </div>

            {selectedEntry.mood && (
              <span
                className={`inline-block rounded-full border px-3 py-1 text-xs mb-4 ${
                  MOOD_COLORS[selectedEntry.mood] ??
                  "border-white/10 text-gray-500"
                }`}
              >
                {selectedEntry.mood}
              </span>
            )}

            <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">
              {selectedEntry.content}
            </p>

            {selectedEntry.scripture_reference && (
              <div className="mt-4 rounded-lg border border-[#d4af37]/15 bg-[#0d0b1a] p-3">
                <p className="text-xs font-semibold text-[#d4af37]/70">
                  {selectedEntry.scripture_reference}
                </p>
              </div>
            )}

            {selectedEntry.tags && selectedEntry.tags.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1.5">
                {selectedEntry.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-white/10 bg-[#0d0b1a] px-2.5 py-0.5 text-xs text-gray-500"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ── List view ──────────────────────────────────────────────────────── */
  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto w-full max-w-4xl">

        {/* Header */}
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="mb-1 text-xs tracking-[0.4em] uppercase text-[#d4af37]/40">
              Cor ad Cor Loquitur
            </p>
            <h1 className="font-heading text-3xl text-[#d4af37]">
              Dziennik duchowy
            </h1>
          </div>
          <button
            onClick={() => {
              clearError();
              setViewMode("create");
            }}
            className="flex items-center gap-2 rounded-xl border border-[#d4af37]/40 bg-[#d4af37]/10 px-4 py-2.5 text-sm font-medium text-[#d4af37] transition-all hover:bg-[#d4af37]/20"
          >
            <Plus className="h-4 w-4" />
            Nowy wpis
          </button>
        </div>

        {/* Privacy notice */}
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-white/10 bg-white/5/50 px-4 py-3">
          <Shield className="h-4 w-4 shrink-0 text-[#d4af37]/60" />
          <p className="text-sm text-gray-500/70">
            Twoje wpisy są prywatne — tylko Ty je widzisz
          </p>
        </div>

        {/* Moja droga — journey insights */}
        <div className="mb-6">
          <button
            onClick={() => {
              setShowInsights((v) => !v);
              if (!showInsights && !insights) fetchInsights();
            }}
            className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/5/60 px-4 py-3 transition-all hover:border-[#d4af37]/25"
          >
            <div className="flex items-center gap-2.5">
              <TrendingUp className="h-4 w-4 text-[#d4af37]/70" />
              <span className="text-sm font-medium text-gray-500">
                Moja droga duchowa
              </span>
              {insights?.ai_enabled && insights.entry_count > 0 && (
                <span className="rounded-full bg-[#d4af37]/10 px-2 py-0.5 text-[10px] text-[#d4af37]/70">
                  {insights.entry_count} wpisów
                </span>
              )}
            </div>
            {showInsights ? (
              <ChevronUp className="h-4 w-4 text-gray-500/50" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-500/50" />
            )}
          </button>

          {showInsights && (
            <div className="mt-2 rounded-xl border border-white/10 bg-white/5 p-5">
              {insightsLoading && (
                <div className="flex items-center justify-center py-8">
                  <div className="flex gap-1">
                    {[0, 0.3, 0.6].map((delay, i) => (
                      <span
                        key={i}
                        className="animate-sacred-pulse h-2 w-2 rounded-full bg-[#d4af37]/50"
                        style={{ animationDelay: `${delay}s` }}
                      />
                    ))}
                  </div>
                </div>
              )}

              {!insightsLoading && insights && !insights.ai_enabled && (
                <div className="py-4 text-center">
                  <p className="text-sm text-gray-500/60">
                    {insights.disclaimer}
                  </p>
                </div>
              )}

              {!insightsLoading && insights && insights.ai_enabled && insights.entry_count === 0 && (
                <div className="py-4 text-center">
                  <BookMarked className="mx-auto mb-3 h-8 w-8 text-[#d4af37]/20" />
                  <p className="text-sm text-gray-500/60">
                    Dodaj pierwsze wpisy do dziennika, aby zobaczyć analizę drogi duchowej.
                  </p>
                </div>
              )}

              {!insightsLoading && insights && insights.ai_enabled && insights.entry_count > 0 && (
                <>
                  {/* Journey stage card */}
                  <div className="mb-5 rounded-lg border border-[#d4af37]/15 bg-[#d4af37]/5 p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[10px] uppercase tracking-widest text-[#d4af37]/40">
                          Etap drogi
                        </p>
                        <h3 className="font-heading text-lg text-[#d4af37]">
                          {insights.journey.stage_name_pl}
                        </h3>
                        <p className="mt-0.5 text-xs text-gray-500/70 leading-relaxed">
                          {insights.journey.stage_description}
                        </p>
                      </div>
                      <span className="shrink-0 text-2xl font-light text-[#d4af37]/50">
                        {insights.journey.progress_percentage}%
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-[#d4af37]/50 to-[#d4af37]"
                        style={{ width: `${insights.journey.progress_percentage}%` }}
                      />
                    </div>

                    {insights.journey.next_growth_area && (
                      <p className="mt-3 text-xs text-gray-500/60 italic">
                        Obszar wzrostu: {insights.journey.next_growth_area}
                      </p>
                    )}
                  </div>

                  {/* Patterns */}
                  {insights.patterns.length > 0 && (
                    <div className="mb-4">
                      <div className="mb-2 flex items-center gap-2">
                        <Sparkles className="h-3.5 w-3.5 text-[#d4af37]/50" />
                        <p className="text-xs font-medium text-gray-500">
                          Wzory duchowe
                        </p>
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {insights.patterns.slice(0, 4).map((pattern, i) => (
                          <div
                            key={i}
                            className="rounded-lg border border-white/10 bg-[#0d0b1a] p-3"
                          >
                            <p className="mb-1 text-[10px] uppercase tracking-wider text-[#d4af37]/40">
                              {PATTERN_LABELS[pattern.type] ?? pattern.type}
                            </p>
                            <p className="text-xs text-gray-500/80 leading-relaxed">
                              {pattern.description}
                            </p>
                            {pattern.related_scriptures && pattern.related_scriptures.length > 0 && (
                              <p className="mt-1.5 text-[10px] text-[#d4af37]/50 italic font-scripture">
                                {pattern.related_scriptures.slice(0, 2).join(", ")}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Disclaimer */}
                  <p className="text-[11px] italic text-gray-500/40 leading-relaxed border-t border-white/10 pt-3">
                    {insights.disclaimer}
                  </p>
                </>
              )}
            </div>
          )}
        </div>

        {/* Search & filter */}
        <div className="mb-6 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500/40" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Szukaj w wpisach…"
              className="w-full rounded-lg border border-white/10 bg-white/5 py-2.5 pl-10 pr-4 text-sm text-gray-200 placeholder-gray-600 focus:border-[#d4af37]/50 focus:outline-none"
            />
          </div>
          <select
            value={moodFilter}
            onChange={(e) => setMoodFilter(e.target.value)}
            className="rounded-lg border border-white/10 bg-[#0d0b1a] px-4 py-2.5 text-sm text-gray-300 focus:border-[#d4af37]/50 focus:outline-none"
          >
            <option value="">Wszystkie nastroje</option>
            {MOODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 rounded-lg border border-red-800/30 bg-red-900/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="flex gap-1">
              <span className="animate-sacred-pulse h-2 w-2 rounded-full bg-[#d4af37]/50" />
              <span className="animate-sacred-pulse h-2 w-2 rounded-full bg-[#d4af37]/50 [animation-delay:0.5s]" />
              <span className="animate-sacred-pulse h-2 w-2 rounded-full bg-[#d4af37]/50 [animation-delay:1s]" />
            </div>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && entries.length === 0 && (
          <div className="rounded-xl border border-white/10 bg-white/5 py-16 text-center">
            <BookMarked className="mx-auto mb-4 h-12 w-12 text-[#d4af37]/20" />
            <p className="font-heading text-lg text-[#d4af37]/50">
              Brak wpisów
            </p>
            <p className="mt-2 text-sm text-gray-500/60">
              {search || moodFilter
                ? "Nie znaleziono wpisów dla wybranych filtrów."
                : "Zacznij od napisania pierwszej refleksji."}
            </p>
            {!search && !moodFilter && (
              <button
                onClick={() => setViewMode("create")}
                className="mt-4 inline-flex items-center gap-2 rounded-lg border border-[#d4af37]/40 bg-[#d4af37]/10 px-4 py-2 text-sm font-medium text-[#d4af37] transition-all hover:bg-[#d4af37]/20"
              >
                <Plus className="h-4 w-4" />
                Dodaj pierwszy wpis
              </button>
            )}
          </div>
        )}

        {/* Entries grid */}
        {!isLoading && entries.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className="group relative rounded-xl border border-white/10 bg-white/5 p-5 transition-all hover:border-[#d4af37]/25 hover:shadow-[0_4px_20px_rgba(0,0,0,0.2)] cursor-pointer"
                onClick={() => {
                  setSelectedEntry(entry);
                  setViewMode("detail");
                }}
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-heading text-base text-gray-200 truncate">
                      {entry.title ?? "Bez tytułu"}
                    </h3>
                    <p className="text-xs text-gray-500/60 mt-0.5">
                      {formatDate(entry.created_at)}
                    </p>
                  </div>
                  {entry.mood && (
                    <span
                      className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs ${
                        MOOD_COLORS[entry.mood] ??
                        "border-white/10 text-gray-500"
                      }`}
                    >
                      {entry.mood}
                    </span>
                  )}
                </div>

                <p className="text-sm text-gray-500/70 leading-relaxed line-clamp-3">
                  {entry.content.slice(0, 150)}
                  {entry.content.length > 150 ? "…" : ""}
                </p>

                {entry.scripture_reference && (
                  <p className="mt-3 text-xs text-[#d4af37]/50 font-scripture italic">
                    {entry.scripture_reference}
                  </p>
                )}

                {entry.tags && entry.tags.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {entry.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-white/10 bg-[#0d0b1a] px-2 py-0.5 text-[10px] text-gray-500/60"
                      >
                        {tag}
                      </span>
                    ))}
                    {entry.tags.length > 3 && (
                      <span className="text-[10px] text-gray-500/40 px-1 py-0.5">
                        +{entry.tags.length - 3}
                      </span>
                    )}
                  </div>
                )}

                {/* Quick delete */}
                <div
                  className="absolute right-3 bottom-3 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                >
                  {deleteConfirm === entry.id ? (
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleDelete(entry.id)}
                        className="rounded px-2 py-1 text-[10px] text-red-400 border border-red-700/40 bg-red-900/20 hover:bg-red-900/40"
                      >
                        Usuń
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(null)}
                        className="rounded px-2 py-1 text-[10px] text-gray-500 border border-white/10"
                      >
                        Nie
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteConfirm(entry.id)}
                      className="rounded p-1.5 text-gray-500/30 hover:text-red-500/70 transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {!isLoading && totalPages > 1 && (
          <div className="mt-8 flex items-center justify-center gap-3">
            <button
              onClick={() => fetchEntries(currentPage - 1)}
              disabled={currentPage <= 1}
              className="flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-sm text-gray-500 transition-all hover:text-[#d4af37] disabled:cursor-not-allowed disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" />
              Poprzednia
            </button>
            <span className="text-sm text-gray-500">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => fetchEntries(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-sm text-gray-500 transition-all hover:text-[#d4af37] disabled:cursor-not-allowed disabled:opacity-30"
            >
              Następna
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
