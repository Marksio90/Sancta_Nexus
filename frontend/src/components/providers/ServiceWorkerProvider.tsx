"use client";

import { useEffect } from "react";

/**
 * Registers the service worker and schedules daily prayer reminders.
 * Must be rendered in a client component inside <body>.
 */
export function ServiceWorkerProvider() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((reg) => {
        console.info("[SW] Registered", reg.scope);

        // Schedule daily prayer notification (if permission granted)
        scheduleDailyPrayer();
      })
      .catch((err) => console.warn("[SW] Registration failed:", err));
  }, []);

  return null;
}

async function scheduleDailyPrayer() {
  if (!("Notification" in window)) return;

  // Only ask if not yet determined
  if (Notification.permission === "default") {
    // Don't ask immediately — wait for user interaction elsewhere
    return;
  }

  if (Notification.permission !== "granted") return;

  // Use localStorage to avoid showing notification more than once per day
  const lastKey = "sancta_nexus_last_notif";
  const last = localStorage.getItem(lastKey);
  const today = new Date().toDateString();
  if (last === today) return;

  localStorage.setItem(lastKey, today);

  const hour = new Date().getHours();
  const timeToMorning = hour < 7 ? (7 - hour) * 3600000 : 0;

  if (timeToMorning > 0) {
    setTimeout(() => {
      new Notification("Sancta Nexus — Jutrznia", {
        body: "Dobry poranek! Czas na Lectio Divina — Słowo Boże czeka.",
        icon: "/icons/icon-192.svg",
        tag: "morning-prayer",
      });
    }, timeToMorning);
  }
}
