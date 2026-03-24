"use client";

/**
 * InstallPrompt — guides users to install Sancta Nexus as a native app.
 *
 * Three scenarios handled:
 *   1. Android Chrome / Edge  → BeforeInstallPromptEvent (native A2HS dialog)
 *   2. iOS Safari             → Manual instructions ("Share → Add to Home Screen")
 *   3. Already installed (standalone mode) → hidden
 *
 * Shown once per session, dismissed to localStorage for 7 days.
 */

import { useEffect, useState, useCallback } from "react";
import { X, Download, Share, Smartphone } from "lucide-react";

const DISMISS_KEY = "sancta_install_dismissed_until";
const DISMISS_DAYS = 7;

// BeforeInstallPromptEvent is not in standard TS lib
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

type Platform = "android" | "ios" | "desktop" | "installed";

function detectPlatform(): Platform {
  if (typeof window === "undefined") return "desktop";
  // Already running as installed PWA or Capacitor
  if (
    window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in window.navigator &&
      (window.navigator as { standalone?: boolean }).standalone === true)
  ) {
    return "installed";
  }
  const ua = navigator.userAgent;
  if (/iPad|iPhone|iPod/.test(ua)) return "ios";
  if (/Android/.test(ua)) return "android";
  return "desktop";
}

export function InstallPrompt() {
  const [platform, setPlatform] = useState<Platform>("desktop");
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const p = detectPlatform();
    setPlatform(p);
    if (p === "installed") return;

    // Check dismissal
    const dismissedUntil = localStorage.getItem(DISMISS_KEY);
    if (dismissedUntil && Date.now() < parseInt(dismissedUntil)) return;

    // Android: wait for browser event
    if (p === "android" || p === "desktop") {
      const handler = (e: Event) => {
        e.preventDefault();
        setDeferredPrompt(e as BeforeInstallPromptEvent);
        setVisible(true);
      };
      window.addEventListener("beforeinstallprompt", handler);
      return () => window.removeEventListener("beforeinstallprompt", handler);
    }

    // iOS: always show manual instructions after a short delay
    if (p === "ios") {
      const t = setTimeout(() => setVisible(true), 3000);
      return () => clearTimeout(t);
    }
  }, []);

  const dismiss = useCallback(() => {
    setVisible(false);
    const until = Date.now() + DISMISS_DAYS * 86_400_000;
    localStorage.setItem(DISMISS_KEY, String(until));
  }, []);

  const install = useCallback(async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const choice = await deferredPrompt.userChoice;
    if (choice.outcome === "accepted") {
      setVisible(false);
    }
    setDeferredPrompt(null);
  }, [deferredPrompt]);

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-label="Zainstaluj Sancta Nexus"
      className="
        fixed bottom-20 left-4 right-4 z-50
        md:bottom-6 md:left-auto md:right-6 md:max-w-sm
        animate-fade-in
      "
    >
      <div className="rounded-2xl border border-[--color-gold]/25 bg-[--color-sacred-surface] p-4 shadow-2xl shadow-black/40">
        {/* Header */}
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[--color-gold]/30 bg-[--color-gold]/10">
              <Smartphone className="h-5 w-5 text-[--color-gold]" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[--color-parchment]">
                Zainstaluj Sancta Nexus
              </p>
              <p className="text-xs text-[--color-sacred-text-muted]/60">
                Modlitwa zawsze pod ręką
              </p>
            </div>
          </div>
          <button
            onClick={dismiss}
            aria-label="Zamknij"
            className="rounded-lg p-1 text-[--color-sacred-text-muted]/40 hover:text-[--color-sacred-text-muted]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Benefits */}
        <ul className="mb-4 space-y-1 text-xs text-[--color-sacred-text-muted]">
          <li className="flex items-center gap-2">
            <span className="text-[--color-gold]">✓</span> Działa offline — w
            kościele i na rekolekcjach
          </li>
          <li className="flex items-center gap-2">
            <span className="text-[--color-gold]">✓</span> Przypomnienia o
            modlitwie (Jutrznia, Nieszpory)
          </li>
          <li className="flex items-center gap-2">
            <span className="text-[--color-gold]">✓</span> Pełnoekranowe, bez
            paska przeglądarki
          </li>
        </ul>

        {/* Actions */}
        {platform === "ios" ? (
          <div className="rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-bg] p-3">
            <p className="text-xs text-[--color-sacred-text-muted]">
              W Safari: naciśnij{" "}
              <Share className="mb-0.5 inline h-3.5 w-3.5 text-[--color-gold]" />{" "}
              <strong className="text-[--color-parchment]">Udostępnij</strong>{" "}
              → <strong className="text-[--color-parchment]">Dodaj do ekranu&nbsp;głównego</strong>
            </p>
          </div>
        ) : (
          <button
            onClick={install}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-[--color-gold]/40 bg-[--color-gold]/10 py-2.5 text-sm font-medium text-[--color-gold] transition-all hover:bg-[--color-gold]/20 active:scale-[0.98]"
          >
            <Download className="h-4 w-4" />
            Zainstaluj aplikację
          </button>
        )}

        {/* Dismiss */}
        <button
          onClick={dismiss}
          className="mt-2 w-full text-center text-xs text-[--color-sacred-text-muted]/40 hover:text-[--color-sacred-text-muted]/60"
        >
          Może później
        </button>
      </div>
    </div>
  );
}
