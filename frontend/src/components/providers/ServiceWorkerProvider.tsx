"use client";

import { useEffect } from "react";
import { prefetchTodayScripture } from "@/lib/offline-cache";
import {
  subscribeWebPush,
  requestNotificationPermission,
  scheduleLocalReminders,
  initCapacitorPush,
} from "@/lib/notifications";

/**
 * ServiceWorkerProvider
 *
 * Responsibilities:
 *  1. Register /sw.js service worker
 *  2. Pre-fetch today's scripture into IndexedDB for offline use
 *  3. Subscribe to VAPID web push (if permission already granted)
 *  4. Initialise Capacitor push notifications (no-op on web)
 *  5. Register Periodic Background Sync (Chrome 80+) for daily scripture
 *  6. Schedule local prayer reminders via Capacitor or SW postMessage
 */
export function ServiceWorkerProvider() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    // Offline scripture pre-fetch (IndexedDB) — no permission needed
    prefetchTodayScripture().catch(() => {});

    // ── Capacitor native push (no-op on plain web) ────────────────────────
    initCapacitorPush((_title, _body) => {
      // Could show an in-app toast here
    }).catch(() => {});

    if (!("serviceWorker" in navigator)) return;

    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then(async (reg) => {
        // ── Periodic Background Sync ──────────────────────────────────────
        try {
          const pbsm = (reg as unknown as {
            periodicSync?: {
              register(tag: string, opts: { minInterval: number }): Promise<void>;
            };
          }).periodicSync;
          if (pbsm) {
            await pbsm.register("daily-scripture-prefetch", {
              minInterval: 24 * 60 * 60 * 1000,
            });
          }
        } catch {
          // Chrome only — ignored elsewhere
        }

        // ── Web Push subscription ─────────────────────────────────────────
        if (Notification.permission === "granted") {
          subscribeWebPush().catch(() => {});
        }

        // Tell SW to pre-fetch tomorrow's scripture in background
        reg.active?.postMessage({ type: "PREFETCH_SCRIPTURE" });
      })
      .catch((err) => console.warn("[SW] Registration failed:", err));

    // ── Prayer reminders ──────────────────────────────────────────────────
    if (Notification.permission === "granted") {
      scheduleLocalReminders().catch(() => {});
    } else if (Notification.permission === "default") {
      // Ask non-intrusively after 30s on first visit
      const t = setTimeout(async () => {
        const granted = await requestNotificationPermission();
        if (granted) {
          subscribeWebPush().catch(() => {});
          scheduleLocalReminders().catch(() => {});
        }
      }, 30_000);
      return () => clearTimeout(t);
    }
  }, []);

  return null;
}
