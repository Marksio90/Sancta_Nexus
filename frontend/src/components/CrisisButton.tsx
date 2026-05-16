"use client";

/**
 * CrisisButton — always-visible crisis support access point.
 *
 * Renders as a subtle fixed-position button in the bottom-right corner.
 * On click, expands into a panel with:
 *  - Immediate comfort message (Ps 34,19)
 *  - Polish crisis line: Telefon Zaufania 116 123
 *  - Chat link: 116123.pl
 *  - Encouragement to speak with a priest or therapist
 *
 * Design principles:
 *  - Never dismissible via timeout; user must close explicitly.
 *  - High-contrast red trigger button (accessible).
 *  - Does not replace professional help — panel makes this explicit.
 *  - z-index above all other UI elements.
 */

import { useState, useCallback } from "react";

export function CrisisButton() {
  const [isOpen, setIsOpen] = useState(false);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  return (
    <>
      {/* Trigger button — always visible */}
      {!isOpen && (
        <button
          onClick={open}
          aria-label="Potrzebuję pomocy — wsparcie kryzysowe"
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-red-600 px-4 py-3 text-sm font-semibold text-white shadow-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
          style={{ zIndex: 9999 }}
        >
          <span aria-hidden="true" className="text-lg">🤝</span>
          <span className="hidden sm:inline">Potrzebuję pomocy</span>
        </button>
      )}

      {/* Crisis support panel */}
      {isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Wsparcie kryzysowe"
          className="fixed inset-x-4 bottom-4 z-50 mx-auto max-w-sm rounded-2xl bg-white p-6 shadow-2xl sm:right-6 sm:left-auto"
          style={{ zIndex: 9999 }}
        >
          <button
            onClick={close}
            aria-label="Zamknij panel wsparcia"
            className="absolute right-4 top-4 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-400 rounded"
          >
            <span aria-hidden="true" className="text-xl">✕</span>
          </button>

          {/* Scripture anchor */}
          <p className="mb-3 text-center text-sm font-medium italic text-gray-500">
            „Pan jest blisko ludzi skruszonych w sercu, ocala złamanych na duchu."
          </p>
          <p className="mb-4 text-center text-xs text-gray-400">— Ps 34,19</p>

          <p className="mb-4 text-center text-base font-semibold text-gray-900">
            Nie jesteś sam/sama.
          </p>

          {/* Primary crisis line */}
          <a
            href="tel:116123"
            className="mb-3 flex w-full items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-3 font-bold text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors"
            aria-label="Zadzwoń na Telefon Zaufania 116 123"
          >
            <span aria-hidden="true">📞</span>
            Telefon Zaufania: 116 123
          </a>

          {/* Chat alternative */}
          <a
            href="https://116123.pl"
            target="_blank"
            rel="noopener noreferrer"
            className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-400 transition-colors"
          >
            <span aria-hidden="true">💬</span>
            Czat online: 116123.pl
          </a>

          {/* Contextual note */}
          <p className="text-center text-xs text-gray-400 leading-relaxed">
            Możesz też porozmawiać z kapłanem, kierownikiem duchowym
            lub terapeutą. Twoje życie ma wartość.
          </p>
        </div>
      )}

      {/* Backdrop (closes panel on click) */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20"
          style={{ zIndex: 9998 }}
          aria-hidden="true"
          onClick={close}
        />
      )}
    </>
  );
}
