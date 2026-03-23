"use client";

import { useEffect } from "react";
import Link from "next/link";
import { RefreshCw, Home } from "lucide-react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Log to monitoring service in production
    console.error("[Sancta Nexus] Unhandled error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center px-6 text-center">
      <div className="max-w-md">
        {/* Sacred ornament */}
        <div className="mx-auto mb-8 flex h-20 w-20 items-center justify-center rounded-full border border-[--color-sacred-red]/30 bg-[--color-sacred-red]/5">
          <span className="text-3xl text-[--color-sacred-red-light]/60">✝</span>
        </div>

        <p className="mb-2 text-xs tracking-[0.4em] uppercase text-[--color-sacred-text-muted]/50">
          Wystąpił błąd
        </p>
        <h1 className="font-heading mb-4 text-3xl text-[--color-gold]">
          Coś poszło nie tak
        </h1>

        <div className="sacred-divider mx-auto mb-6 w-32" />

        <p className="mb-8 leading-relaxed text-[--color-sacred-text-muted]/70">
          Przepraszamy — napotkaliśmy nieoczekiwany błąd. Spróbuj ponownie
          lub wróć na stronę główną.
        </p>

        {error.message && (
          <p className="mb-8 rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface] px-4 py-3 text-xs text-[--color-sacred-text-muted]/50">
            {error.message}
          </p>
        )}

        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={reset}
            className="inline-flex items-center gap-2 rounded-xl border border-[--color-gold]/40 bg-[--color-gold]/10 px-6 py-3 text-sm font-medium text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
          >
            <RefreshCw className="h-4 w-4" />
            Spróbuj ponownie
          </button>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-xl border border-[--color-sacred-border] px-6 py-3 text-sm text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/30 hover:text-[--color-parchment]"
          >
            <Home className="h-4 w-4" />
            Strona główna
          </Link>
        </div>

        <p className="mt-10 font-scripture text-sm italic text-[--color-sacred-text-muted]/30">
          &ldquo;Pan jest moją mocą i tarczą&rdquo; — Ps 28,7
        </p>
      </div>
    </div>
  );
}
