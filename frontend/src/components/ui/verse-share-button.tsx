"use client";

import { Share2, Copy, Check } from "lucide-react";
import { useState } from "react";

interface VerseShareButtonProps {
  text: string;
  ref_: string;
}

export function VerseShareButton({ text, ref_ }: VerseShareButtonProps) {
  const [copied, setCopied] = useState(false);

  const shareText = `„${text}" — ${ref_}\n\nZnalezione w Sancta Nexus`;

  const handleShare = async () => {
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({
          title: `Werset dnia — ${ref_}`,
          text: shareText,
        });
        return;
      } catch {
        // User cancelled or not supported — fall through to clipboard
      }
    }
    // Clipboard fallback
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked
    }
  };

  return (
    <button
      onClick={handleShare}
      className="inline-flex items-center gap-1.5 rounded-lg border border-[--color-sacred-border] px-3 py-1.5 text-xs text-[--color-sacred-text-muted]/60 transition-all hover:border-[--color-gold]/30 hover:text-[--color-gold]"
      title="Podziel się tym wersetem"
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5" />
          Skopiowano
        </>
      ) : (
        <>
          <Share2 className="h-3.5 w-3.5" />
          Podziel się
        </>
      )}
    </button>
  );
}
