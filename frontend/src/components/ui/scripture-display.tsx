"use client";

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
  catechismRef?: string;
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
  catechismRef,
}: ScriptureDisplayProps) {
  const reference = endVerse
    ? `${book} ${chapter},${startVerse}-${endVerse}`
    : `${book} ${chapter},${startVerse}`;

  return (
    <div className="space-y-6">
      {/* Main scripture card */}
      <div className="glow-candle relative overflow-hidden rounded-xl border border-[--color-gold]/20 bg-[--color-sacred-surface] p-6 md:p-8">
        {/* Decorative corner ornaments */}
        <div className="pointer-events-none absolute left-3 top-3 text-[--color-gold]/10 text-2xl">
          ❧
        </div>
        <div className="pointer-events-none absolute bottom-3 right-3 rotate-180 text-[--color-gold]/10 text-2xl">
          ❧
        </div>

        {/* Reference header */}
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-heading text-lg text-[--color-gold]">
            {reference}
          </h3>
          {translation && (
            <span className="rounded-md bg-[--color-gold]/10 px-2.5 py-1 text-xs font-medium text-[--color-gold]/70">
              {translation}
            </span>
          )}
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

      {/* Enrichment cards — only shown when data is available */}
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
              Ojcowie Kosciola
            </h4>
            <p className="font-scripture text-sm leading-relaxed text-[--color-sacred-text-muted]">
              {patristicNote}
            </p>
          </div>
        )}

        {originalLanguageKey && (
          <div className="rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5">
            <h4 className="font-heading mb-2 text-sm uppercase tracking-wider text-[--color-gold]/70">
              Slowo kluczowe
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
    </div>
  );
}
