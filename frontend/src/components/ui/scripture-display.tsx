"use client";

import { useState, useEffect } from "react";
import { Share2, Check, MessageSquare, ChevronDown, ChevronUp } from "lucide-react";
import { useNotesStore } from "@/stores/notes";

export interface OriginalLanguageEntry {
  word: string;             // Original word (Hebrew/Greek)
  transliteration: string;  // Phonetic transliteration
  language: "hebrew" | "greek";
  meaning: string;          // Brief definition
  strongs?: string;         // Strong's number e.g. H7965 / G1515
}

interface ScriptureDisplayProps {
  book: string;
  chapter: number;
  startVerse: number;
  endVerse?: number;
  text: string;
  translation?: string;
  historicalContext?: string;
  patristicNote?: string;
  originalLanguageKey?: string;
  originalLanguages?: OriginalLanguageEntry[];
  catechismRef?: string;
  showNotes?: boolean;
}

export function ScriptureDisplay({
  book,
  chapter,
  startVerse,
  endVerse,
  text,
  translation,
  historicalContext,
  patristicNote,
  originalLanguageKey,
  originalLanguages,
  catechismRef,
  showNotes = true,
}: ScriptureDisplayProps) {
  const reference = endVerse
    ? `${book} ${chapter},${startVerse}-${endVerse}`
    : `${book} ${chapter},${startVerse}`;

  const [copied, setCopied] = useState(false);
  const [showOriginal, setShowOriginal] = useState(false);
  const [showNotesPanel, setShowNotesPanel] = useState(false);

  const { getNote, saveNote, loadFromStorage } = useNotesStore();
  const [noteText, setNoteText] = useState("");
  const [noteSaved, setNoteSaved] = useState(false);

  // Load persisted notes on mount
  useEffect(() => {
    loadFromStorage();
    setNoteText(getNote(reference));
  }, [reference, loadFromStorage, getNote]);

  const shareText = `„${text}" — ${reference}`;

  const handleShare = async () => {
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title: `Werset — ${reference}`, text: shareText });
        return;
      } catch { /* cancelled */ }
    }
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* blocked */ }
  };

  const handleSaveNote = () => {
    saveNote(reference, noteText);
    setNoteSaved(true);
    setTimeout(() => setNoteSaved(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Main scripture card */}
      <div className="glow-candle relative overflow-hidden rounded-xl border border-[--color-gold]/20 bg-[--color-sacred-surface] p-6 md:p-8">
        {/* Decorative corner ornaments */}
        <div className="pointer-events-none absolute left-3 top-3 text-[--color-gold]/10 text-2xl">❧</div>
        <div className="pointer-events-none absolute bottom-3 right-3 rotate-180 text-[--color-gold]/10 text-2xl">❧</div>

        {/* Reference header */}
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="font-heading text-lg text-[--color-gold]">{reference}</h3>
          <div className="flex items-center gap-2">
            {translation && (
              <span className="rounded-md bg-[--color-gold]/10 px-2.5 py-1 text-xs font-medium text-[--color-gold]/70">
                {translation}
              </span>
            )}
            {/* Share button */}
            <button
              onClick={handleShare}
              className="inline-flex items-center gap-1 rounded-md border border-[--color-sacred-border] px-2.5 py-1 text-xs text-[--color-sacred-text-muted]/60 transition-all hover:border-[--color-gold]/30 hover:text-[--color-gold]"
              title="Podziel się wersetem"
            >
              {copied ? <Check className="h-3 w-3" /> : <Share2 className="h-3 w-3" />}
              {copied ? "Skopiowano" : "Udostępnij"}
            </button>
          </div>
        </div>

        <div className="sacred-divider mb-6" />

        {/* Scripture text with illuminated drop cap */}
        <blockquote className="drop-cap font-scripture text-lg leading-loose text-[--color-parchment] md:text-xl">
          {text}
        </blockquote>

        <div className="sacred-divider mt-6" />

        {/* Bottom reference */}
        <p className="mt-4 text-right text-sm text-[--color-sacred-text-muted]">
          — {reference}
        </p>
      </div>

      {/* Enrichment cards */}
      <div className="animate-fade-in-stagger grid gap-4 md:grid-cols-2">
        {historicalContext && (
          <div className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5">
            <h4 className="font-heading mb-2 text-sm uppercase tracking-wider text-[--color-gold]/70">
              Kontekst historyczny
            </h4>
            <p className="text-sm leading-relaxed text-[--color-sacred-text-muted]">
              {historicalContext}
            </p>
          </div>
        )}

        {patristicNote && (
          <div className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5">
            <h4 className="font-heading mb-2 text-sm uppercase tracking-wider text-[--color-gold]/70">
              Ojcowie Kościoła
            </h4>
            <p className="font-scripture text-sm leading-relaxed text-[--color-sacred-text-muted]">
              {patristicNote}
            </p>
          </div>
        )}

        {originalLanguageKey && !originalLanguages && (
          <div className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5">
            <h4 className="font-heading mb-2 text-sm uppercase tracking-wider text-[--color-gold]/70">
              Słowo kluczowe
            </h4>
            <p className="text-sm leading-relaxed text-[--color-sacred-text-muted]">
              {originalLanguageKey}
            </p>
          </div>
        )}

        {catechismRef && (
          <div className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5">
            <h4 className="font-heading mb-2 text-sm uppercase tracking-wider text-[--color-gold]/70">
              Katechizm
            </h4>
            <p className="text-sm leading-relaxed text-[--color-sacred-text-muted]">
              {catechismRef}
            </p>
          </div>
        )}
      </div>

      {/* Original language section */}
      {originalLanguages && originalLanguages.length > 0 && (
        <div className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5">
          <button
            onClick={() => setShowOriginal((v) => !v)}
            className="flex w-full items-center justify-between"
          >
            <h4 className="font-heading text-sm uppercase tracking-wider text-[--color-gold]/70">
              Języki oryginalne · {originalLanguages[0].language === "hebrew" ? "Hebrajski" : "Grecki"}
            </h4>
            {showOriginal ? (
              <ChevronUp className="h-4 w-4 text-[--color-gold]/40" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[--color-gold]/40" />
            )}
          </button>

          {showOriginal && (
            <div className="mt-4 space-y-4 animate-fade-in">
              {originalLanguages.map((entry, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-bg] p-4"
                >
                  {/* Original word */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span
                        className="text-2xl font-bold text-[--color-gold]"
                        dir={entry.language === "hebrew" ? "rtl" : "ltr"}
                        lang={entry.language === "hebrew" ? "he" : "el"}
                      >
                        {entry.word}
                      </span>
                      <span className="ml-3 font-scripture text-base italic text-[--color-sacred-text-muted]">
                        {entry.transliteration}
                      </span>
                    </div>
                    {entry.strongs && (
                      <span className="shrink-0 rounded bg-[--color-sacred-surface] px-2 py-0.5 text-xs text-[--color-sacred-text-muted]/50">
                        {entry.strongs}
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-sm text-[--color-sacred-text-muted]">
                    {entry.meaning}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Personal notes */}
      {showNotes && (
        <div className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5">
          <button
            onClick={() => setShowNotesPanel((v) => !v)}
            className="flex w-full items-center justify-between"
          >
            <h4 className="font-heading text-sm uppercase tracking-wider text-[--color-gold]/70 flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Moje refleksje
              {getNote(reference) && (
                <span className="rounded-full bg-[--color-gold]/20 px-2 py-0.5 text-[10px] text-[--color-gold]">
                  zapisana
                </span>
              )}
            </h4>
            {showNotesPanel ? (
              <ChevronUp className="h-4 w-4 text-[--color-gold]/40" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[--color-gold]/40" />
            )}
          </button>

          {showNotesPanel && (
            <div className="mt-4 animate-fade-in">
              <textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder={`Co Pan mówi do mnie przez ten fragment?\n\nZapisz swoje refleksje, pytania, modlitwy…`}
                rows={5}
                className="w-full rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-bg] p-4 text-sm leading-relaxed text-[--color-sacred-text] placeholder:text-[--color-sacred-text-muted]/30 focus:border-[--color-gold]/40 focus:outline-none focus:ring-1 focus:ring-[--color-gold]/20 resize-none"
              />
              <div className="mt-3 flex items-center justify-between">
                <p className="text-xs text-[--color-sacred-text-muted]/40">
                  Notatki zapisywane lokalnie na urządzeniu
                </p>
                <button
                  onClick={handleSaveNote}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-4 py-2 text-xs font-medium text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
                >
                  {noteSaved ? (
                    <><Check className="h-3.5 w-3.5" /> Zapisano</>
                  ) : (
                    "Zapisz refleksję"
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
