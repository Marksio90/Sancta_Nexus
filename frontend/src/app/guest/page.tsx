"use client";

/**
 * Guest Lectio Divina — one free session without registration.
 *
 * Flow:
 *  1. Emotion input form
 *  2. Loading state while AI pipeline runs
 *  3. Result display (scripture → meditation → prayer → contemplation → action)
 *  4. CTA: email capture → redirect to /auth/register?email=...
 *
 * One free session per IP per 24 h (enforced by backend).
 */

import { useState, useCallback, FormEvent } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface GuestResult {
  guest_session_id: string;
  scripture: { text?: string; reference?: string; translation?: string } | null;
  meditation: { questions?: string[]; key_word?: string } | null;
  prayer: { text?: string } | null;
  contemplation: { guidance?: string } | null;
  action: { challenge?: string } | null;
  tradition: string;
  kerygmatic_theme: string;
  error: string | null;
  cta: string;
}

type Phase = "input" | "loading" | "result" | "captured";

export default function GuestPage() {
  const [phase, setPhase] = useState<Phase>("input");
  const [emotionText, setEmotionText] = useState("");
  const [result, setResult] = useState<GuestResult | null>(null);
  const [email, setEmail] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);

  const handleStart = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!emotionText.trim()) return;
      setSubmitError(null);
      setPhase("loading");

      try {
        const data = await api.post<GuestResult>("/api/v1/guest/lectio", {
          emotion_text: emotionText.trim(),
          tradition: "",
        });
        setResult(data);
        setPhase("result");
      } catch (err: unknown) {
        const msg =
          err instanceof Error && err.message.includes("429")
            ? "Możesz skorzystać z jednej bezpłatnej sesji na 24 godziny. Zaloguj się, aby kontynuować."
            : "Coś poszło nie tak. Spróbuj ponownie za chwilę.";
        setSubmitError(msg);
        setPhase("input");
      }
    },
    [emotionText]
  );

  const handleCapture = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!result || !email.trim()) return;
      setCaptureError(null);

      try {
        await api.post("/api/v1/guest/capture-email", {
          guest_session_id: result.guest_session_id,
          email: email.trim(),
        });
        setPhase("captured");
      } catch {
        setCaptureError("Nie udało się zapisać adresu. Przejdź do rejestracji ręcznie.");
      }
    },
    [result, email]
  );

  if (phase === "input") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <div className="mb-8 text-center">
          <h1 className="font-cinzel text-3xl font-bold text-sacred-text mb-3">
            Lectio Divina — bezpłatna sesja
          </h1>
          <p className="text-gray-400 text-sm">
            Jedna bezpłatna sesja na 24 godziny · Bez rejestracji
          </p>
        </div>

        <form onSubmit={handleStart} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Jak się teraz czujesz? Co jest na Twoim sercu?
            </label>
            <textarea
              value={emotionText}
              onChange={(e) => setEmotionText(e.target.value)}
              placeholder="Napisz kilka zdań o swoim stanie ducha, zmartwieniach lub radościach…"
              rows={5}
              maxLength={2000}
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sacred-text placeholder-gray-500 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30 resize-none"
              required
            />
            <p className="mt-1 text-right text-xs text-gray-500">
              {emotionText.length}/2000
            </p>
          </div>

          {submitError && (
            <p className="rounded-lg bg-red-900/30 px-4 py-3 text-sm text-red-300">
              {submitError}
            </p>
          )}

          <button
            type="submit"
            disabled={!emotionText.trim()}
            className="w-full rounded-xl bg-amber-600 px-6 py-4 font-semibold text-white hover:bg-amber-700 disabled:opacity-40 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2"
          >
            Rozpocznij Lectio Divina
          </button>

          <p className="text-center text-xs text-gray-500">
            Masz już konto?{" "}
            <Link href="/auth/login" className="text-amber-500 hover:underline">
              Zaloguj się
            </Link>{" "}
            — brak limitu sesji.
          </p>
        </form>
      </div>
    );
  }

  if (phase === "loading") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-amber-500/30 border-t-amber-500" />
        <p className="text-gray-400 text-sm animate-pulse">
          Przygotowuję Twoje Lectio Divina…
        </p>
        <p className="text-xs text-gray-600 max-w-xs text-center">
          Asystent analizuje Twój stan ducha i wybiera fragment Pisma Świętego.
          To może potrwać do 30 sekund.
        </p>
      </div>
    );
  }

  if (phase === "result" && result) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 space-y-8">
        {/* Disclaimer */}
        <p className="text-center text-xs text-gray-500 italic">
          Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy.
          Nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty.
        </p>

        {result.error && (
          <div className="rounded-xl bg-red-900/30 px-6 py-4 text-red-300 text-sm">
            {result.error}
          </div>
        )}

        {/* Scripture */}
        {result.scripture && (
          <Section title="Lectio — Słowo Boże">
            {result.scripture.reference && (
              <p className="text-sm font-medium text-amber-400 mb-2">
                {result.scripture.reference}
              </p>
            )}
            <blockquote className="border-l-2 border-amber-500/40 pl-4 italic text-gray-200">
              {result.scripture.text}
            </blockquote>
          </Section>
        )}

        {/* Meditation */}
        {result.meditation && (
          <Section title="Meditatio — Rozważanie">
            {result.meditation.key_word && (
              <p className="text-sm text-amber-400 mb-2">
                Słowo kluczowe: <strong>{result.meditation.key_word}</strong>
              </p>
            )}
            {Array.isArray(result.meditation.questions) &&
              result.meditation.questions.length > 0 && (
                <ul className="space-y-2">
                  {result.meditation.questions.map((q, i) => (
                    <li key={i} className="flex gap-2 text-gray-300 text-sm">
                      <span className="text-amber-500 mt-0.5">•</span>
                      <span>{q}</span>
                    </li>
                  ))}
                </ul>
              )}
          </Section>
        )}

        {/* Prayer */}
        {result.prayer?.text && (
          <Section title="Oratio — Modlitwa">
            <p className="text-gray-200 leading-relaxed text-sm italic">
              {result.prayer.text}
            </p>
          </Section>
        )}

        {/* Contemplation */}
        {result.contemplation?.guidance && (
          <Section title="Contemplatio — Kontemplacja">
            <p className="text-gray-300 text-sm leading-relaxed">
              {result.contemplation.guidance}
            </p>
          </Section>
        )}

        {/* Action */}
        {result.action?.challenge && (
          <Section title="Actio — Wyzwanie dnia">
            <p className="text-gray-200 font-medium text-sm">
              {result.action.challenge}
            </p>
          </Section>
        )}

        {/* Email CTA */}
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 px-6 py-6 space-y-4">
          <p className="text-sm text-gray-300">{result.cta}</p>

          <form onSubmit={handleCapture} className="flex gap-3 flex-col sm:flex-row">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Twój adres e-mail"
              required
              className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-sacred-text placeholder-gray-500 focus:border-amber-500/50 focus:outline-none"
            />
            <button
              type="submit"
              className="rounded-xl bg-amber-600 px-5 py-3 text-sm font-semibold text-white hover:bg-amber-700 transition-colors whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              Zapisz sesję
            </button>
          </form>

          {captureError && (
            <p className="text-xs text-red-400">{captureError}</p>
          )}

          <p className="text-center text-xs text-gray-600">
            lub{" "}
            <Link href="/auth/register" className="text-amber-500 hover:underline">
              utwórz konto bezpośrednio
            </Link>
          </p>
        </div>
      </div>
    );
  }

  if (phase === "captured") {
    const registerUrl = `/auth/register${email ? `?email=${encodeURIComponent(email)}` : ""}`;
    return (
      <div className="mx-auto max-w-md px-4 py-24 text-center space-y-6">
        <div className="text-5xl">🙏</div>
        <h2 className="font-cinzel text-2xl font-semibold text-sacred-text">
          Dziękujemy!
        </h2>
        <p className="text-gray-300 text-sm leading-relaxed">
          Twój adres e-mail został zapamiętany. Dokończ rejestrację, by zapisać
          sesję i śledzić swój postęp duchowy.
        </p>
        <Link
          href={registerUrl}
          className="inline-block rounded-xl bg-amber-600 px-8 py-4 font-semibold text-white hover:bg-amber-700 transition-colors"
        >
          Utwórz konto — to zajmie 30 sekund
        </Link>
        <p className="text-xs text-gray-600">
          <Link href="/" className="hover:underline">
            Wróć do strony głównej
          </Link>
        </p>
      </div>
    );
  }

  return null;
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-5 space-y-3">
      <h2 className="font-cinzel text-base font-semibold text-amber-400">
        {title}
      </h2>
      {children}
    </div>
  );
}
