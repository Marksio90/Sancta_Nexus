/**
 * Sancta Nexus Service Worker — v2
 *
 * Caching strategies:
 *   App shell (HTML/JS/CSS/icons) → stale-while-revalidate
 *   Google Fonts                  → cache-first (30 days)
 *   Scripture / Breviary API      → network-first + scripture cache (offline fallback)
 *   TTS audio                     → network-only (too large / dynamic)
 *   Other API                     → network-first, JSON error fallback
 *
 * Extra capabilities:
 *   Background Sync        — queues offline prayer journal entries
 *   Periodic Background    — pre-fetches tomorrow's scripture nightly
 *   Push Notifications     — VAPID push with action buttons
 *   Web reminders          — scheduled local notifications via setTimeout
 */

const CACHE_SHELL = "sancta-nexus-shell-v2";
const CACHE_FONTS = "sancta-nexus-fonts-v1";
const CACHE_SCRIPTURE = "sancta-nexus-scripture-v1";

const PRECACHE_URLS = [
  "/",
  "/lectio-divina",
  "/breviary",
  "/bible",
  "/spiritual-director",
  "/dashboard",
  "/offline",
  "/manifest.json",
  "/icons/icon-192.svg",
  "/icons/icon-512.svg",
];

// API routes worth caching for offline prayer
const SCRIPTURE_API_PATTERNS = [
  /\/api\/v1\/lectio-divina\/scripture\//,
  /\/api\/v1\/lectio-divina\/liturgical-context/,
  /\/api\/v1\/breviary\//,
  /\/api\/v1\/bible\/passages/,
];

// ── Install ───────────────────────────────────────────────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_SHELL)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate ──────────────────────────────────────────────────────────────────

self.addEventListener("activate", (event) => {
  const validCaches = [CACHE_SHELL, CACHE_FONTS, CACHE_SCRIPTURE];
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => !validCaches.includes(k)).map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ── Fetch ─────────────────────────────────────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET") return;

  // TTS audio — never cache (dynamic MP3 stream)
  if (url.pathname.startsWith("/api/v1/voice/tts")) {
    event.respondWith(fetch(request).catch(() => new Response("", { status: 503 })));
    return;
  }

  // Scripture / Breviary — network-first + scripture cache
  if (SCRIPTURE_API_PATTERNS.some((p) => p.test(url.pathname))) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_SCRIPTURE).then((c) => c.put(request, clone));
          }
          return res;
        })
        .catch(async () => {
          const cached = await caches.match(request, { cacheName: CACHE_SCRIPTURE });
          if (cached) return cached;
          return new Response(
            JSON.stringify({ error: "Offline", offline: true }),
            { headers: { "Content-Type": "application/json" }, status: 503 }
          );
        })
    );
    return;
  }

  // Other API — network-only with error fallback
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response(
          JSON.stringify({ error: "Offline — brak połączenia z serwerem" }),
          { headers: { "Content-Type": "application/json" }, status: 503 }
        )
      )
    );
    return;
  }

  // Google Fonts — cache-first
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    event.respondWith(
      caches.open(CACHE_FONTS).then((cache) =>
        cache.match(request).then(
          (cached) =>
            cached ||
            fetch(request).then((res) => {
              cache.put(request, res.clone());
              return res;
            })
        )
      )
    );
    return;
  }

  // App shell — stale-while-revalidate
  event.respondWith(
    caches.open(CACHE_SHELL).then((cache) =>
      cache.match(request).then((cached) => {
        const networkFetch = fetch(request).then((res) => {
          if (res.ok) cache.put(request, res.clone());
          return res;
        });
        return cached || networkFetch;
      })
    )
  );
});

// ── Background Sync ───────────────────────────────────────────────────────────

self.addEventListener("sync", (event) => {
  if (event.tag === "prayer-journal-sync") {
    event.waitUntil(syncPrayerJournal());
  }
  if (event.tag === "prefetch-scripture") {
    event.waitUntil(prefetchTomorrowScripture());
  }
});

async function syncPrayerJournal() {
  try {
    const db = await openJournalDB();
    const pending = await getAllPendingEntries(db);
    for (const entry of pending) {
      try {
        const res = await fetch("/api/v1/users/journal", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(entry.data),
        });
        if (res.ok) await markSynced(db, entry.id);
      } catch {
        // Will retry on next sync trigger
      }
    }
  } catch {
    // IndexedDB unavailable
  }
}

async function prefetchTomorrowScripture() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const dateStr = tomorrow.toISOString().split("T")[0];
  try {
    const res = await fetch(`/api/v1/lectio-divina/scripture/${dateStr}`);
    if (res.ok) {
      const cache = await caches.open(CACHE_SCRIPTURE);
      cache.put(new Request(`/api/v1/lectio-divina/scripture/${dateStr}`), res);
    }
  } catch {
    // Offline — retry via next periodic sync
  }
}

// ── Periodic Background Sync ──────────────────────────────────────────────────

self.addEventListener("periodicsync", (event) => {
  if (event.tag === "daily-scripture-prefetch") {
    event.waitUntil(prefetchTomorrowScripture());
  }
});

// ── Push Notifications ────────────────────────────────────────────────────────

self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {};
  const title = data.title || "Sancta Nexus";
  const options = {
    body: data.body || "Czas na modlitwę — Lectio Divina czeka",
    icon: "/icons/icon-192.svg",
    badge: "/icons/icon-192.svg",
    tag: data.tag || "sancta-nexus-prayer",
    requireInteraction: false,
    data: { url: data.url || "/lectio-divina" },
    actions: [
      { action: "open", title: "Otwórz" },
      { action: "dismiss", title: "Może później" },
    ],
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  if (event.action === "dismiss") return;
  const url = event.notification.data?.url || "/";
  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((wins) => {
        const existing = wins.find((w) => w.url === url);
        if (existing) return existing.focus();
        return clients.openWindow(url);
      })
  );
});

// ── Message Handler ───────────────────────────────────────────────────────────

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") self.skipWaiting();
  if (event.data?.type === "SCHEDULE_PRAYER_REMINDERS") {
    scheduleWebReminders(event.data.reminders ?? []);
  }
  if (event.data?.type === "PREFETCH_SCRIPTURE") {
    prefetchTomorrowScripture();
  }
});

// ── Web reminder scheduler (Capacitor fallback) ───────────────────────────────

const _scheduledReminders = new Map();

function scheduleWebReminders(reminders) {
  for (const timeout of _scheduledReminders.values()) clearTimeout(timeout);
  _scheduledReminders.clear();
  reminders.forEach(scheduleNext);
}

function scheduleNext(reminder) {
  const next = new Date();
  next.setHours(reminder.hour, reminder.minute, 0, 0);
  if (next.getTime() <= Date.now()) next.setDate(next.getDate() + 1);
  const delay = next.getTime() - Date.now();

  const timeout = setTimeout(async () => {
    await self.registration.showNotification(reminder.title, {
      body: reminder.body,
      icon: "/icons/icon-192.svg",
      badge: "/icons/icon-192.svg",
      tag: `prayer-reminder-${reminder.id}`,
      data: { url: reminder.url },
    });
    scheduleNext(reminder); // reschedule for tomorrow
  }, delay);

  _scheduledReminders.set(reminder.id, timeout);
}

// ── Tiny IndexedDB helper (offline journal queue) ─────────────────────────────

function openJournalDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("sancta-journal-sync", 1);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains("pending")) {
        db.createObjectStore("pending", { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = () => reject(req.error);
  });
}

function getAllPendingEntries(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("pending", "readonly");
    const req = tx.objectStore("pending").getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function markSynced(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("pending", "readwrite");
    tx.objectStore("pending").delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
