"use client";

/**
 * AiFeedback — thumbs up / thumbs down / flag on AI-generated content.
 *
 * Usage:
 *   <AiFeedback module="lectio" contentId={sessionId} />
 *
 * On feedback submission the component:
 *  1. Updates local UI state immediately (optimistic).
 *  2. POSTs to /api/v1/feedback (no auth required — feedback is anonymous
 *     but user_id injected server-side from JWT if present).
 *  3. Shows a thank-you message for 3 seconds, then collapses.
 *
 * Flag (🚩) opens a compact reason selector before submitting:
 *  - Teologicznie błędne
 *  - Powtarzające się / zbyt ogólne
 *  - Inne
 *
 * The backend endpoint is a stub that accepts the payload — actual
 * analytics integration is added in a follow-up sprint.
 */

import { useState, useCallback } from "react";
import { api } from "@/lib/api";

type Rating = "up" | "down" | null;

type FlagReason =
  | "theologically_incorrect"
  | "repetitive_or_generic"
  | "other";

const FLAG_REASONS: { value: FlagReason; label: string }[] = [
  { value: "theologically_incorrect", label: "Teologicznie błędne" },
  { value: "repetitive_or_generic", label: "Powtarzające się / zbyt ogólne" },
  { value: "other", label: "Inne" },
];

interface Props {
  /** Backend module identifier: lectio | reflection | examen | prayer */
  module: string;
  /** Session or content identifier */
  contentId?: string;
}

export function AiFeedback({ module, contentId }: Props) {
  const [rating, setRating] = useState<Rating>(null);
  const [flagging, setFlagging] = useState(false);
  const [flagged, setFlagged] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [thankyou, setThankyou] = useState(false);

  const submit = useCallback(
    async (payload: Record<string, unknown>) => {
      try {
        await api.post("/api/v1/feedback", payload);
      } catch {
        // Non-critical — swallow silently
      }
      setSubmitted(true);
      setThankyou(true);
      setTimeout(() => setThankyou(false), 3000);
    },
    []
  );

  const handleRate = useCallback(
    async (value: "up" | "down") => {
      if (submitted) return;
      setRating(value);
      await submit({ module, content_id: contentId, rating: value });
    },
    [submit, module, contentId, submitted]
  );

  const handleFlag = useCallback(async (reason: FlagReason) => {
    setFlagging(false);
    setFlagged(true);
    await submit({ module, content_id: contentId, flag: reason });
  }, [submit, module, contentId]);

  if (thankyou) {
    return (
      <p className="text-xs text-gray-400 py-1">
        Dziękujemy za opinię — pomaga nam poprawiać jakość treści.
      </p>
    );
  }

  return (
    <div className="flex items-center gap-2 mt-3">
      {/* Thumbs up */}
      <button
        onClick={() => handleRate("up")}
        disabled={submitted}
        aria-label="Dobra odpowiedź"
        aria-pressed={rating === "up"}
        className={`rounded-lg px-2 py-1 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-green-400 ${
          rating === "up"
            ? "bg-green-100 text-green-700"
            : "text-gray-400 hover:text-green-600 hover:bg-green-50"
        } disabled:opacity-40`}
      >
        👍
      </button>

      {/* Thumbs down */}
      <button
        onClick={() => handleRate("down")}
        disabled={submitted}
        aria-label="Słaba odpowiedź"
        aria-pressed={rating === "down"}
        className={`rounded-lg px-2 py-1 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-red-400 ${
          rating === "down"
            ? "bg-red-100 text-red-700"
            : "text-gray-400 hover:text-red-600 hover:bg-red-50"
        } disabled:opacity-40`}
      >
        👎
      </button>

      {/* Flag / report */}
      {!flagged && !submitted && (
        <div className="relative">
          <button
            onClick={() => setFlagging((v) => !v)}
            aria-label="Zgłoś problem z tą odpowiedzią"
            aria-expanded={flagging}
            className="rounded-lg px-2 py-1 text-xs text-gray-400 hover:text-orange-600 hover:bg-orange-50 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-orange-400"
          >
            🚩
          </button>

          {flagging && (
            <div
              className="absolute bottom-8 left-0 z-10 min-w-[200px] rounded-xl border border-gray-200 bg-white py-2 shadow-lg"
              role="menu"
            >
              <p className="px-3 pb-1 text-xs font-medium text-gray-500">
                Powód zgłoszenia:
              </p>
              {FLAG_REASONS.map((r) => (
                <button
                  key={r.value}
                  role="menuitem"
                  onClick={() => handleFlag(r.value)}
                  className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 focus:outline-none focus:bg-gray-50"
                >
                  {r.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {flagged && (
        <span className="text-xs text-orange-500">Zgłoszono ✓</span>
      )}
    </div>
  );
}
