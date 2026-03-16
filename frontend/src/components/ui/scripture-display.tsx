"use client";

interface ScriptureDisplayProps {
  book: string;
  chapter: number;
  startVerse: number;
  endVerse?: number;
  text: string;
  translation?: string;
}

export function ScriptureDisplay({
  book,
  chapter,
  startVerse,
  endVerse,
  text,
  translation,
}: ScriptureDisplayProps) {
  const reference = endVerse
    ? `${book} ${chapter},${startVerse}-${endVerse}`
    : `${book} ${chapter},${startVerse}`;

  return (
    <div className="glow-candle rounded-xl border border-[--color-gold]/20 bg-[--color-sacred-surface] p-6 md:p-8">
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

      {/* Scripture text */}
      <blockquote className="font-scripture text-lg leading-loose text-[--color-parchment] md:text-xl">
        {text}
      </blockquote>

      <div className="sacred-divider mt-6" />

      {/* Bottom reference */}
      <p className="mt-4 text-right text-sm text-[--color-sacred-text-muted]">
        — {reference}
      </p>
    </div>
  );
}
