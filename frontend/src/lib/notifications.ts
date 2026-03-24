/**
 * Push Notifications — VAPID web push + Capacitor native push.
 *
 * Strategy:
 *   - Native (Capacitor iOS/Android): @capacitor/push-notifications → FCM/APNs
 *   - Web (Chrome/Edge/Firefox): Notification API + service worker push
 *   - Fallback: local notifications via @capacitor/local-notifications
 *
 * Prayer reminder schedule (defaults):
 *   06:00 — Jutrznia / Laudes
 *   12:00 — Modlitwa w południe (Sexta)
 *   18:00 — Nieszpory (Vespers)
 *   21:00 — Kompleta (Compline)
 */

const API_BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
    : "";

// ── Web Push Subscription ─────────────────────────────────────────────────────

export async function subscribeWebPush(): Promise<PushSubscription | null> {
  if (typeof window === "undefined") return null;
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return null;

  try {
    const reg = await navigator.serviceWorker.ready;

    const existingSub = await reg.pushManager.getSubscription();
    if (existingSub) return existingSub;

    // VAPID public key from env
    const vapidKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
    if (!vapidKey) return null;

    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey),
    });

    // Register with backend
    await sendSubscriptionToServer(sub);
    return sub;
  } catch {
    return null;
  }
}

async function sendSubscriptionToServer(sub: PushSubscription): Promise<void> {
  const json = sub.toJSON();
  await fetch(`${API_BASE}/api/v1/notifications/subscribe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      endpoint: json.endpoint,
      keys: json.keys,
    }),
  });
}

// ── Notification Permission ───────────────────────────────────────────────────

export async function requestNotificationPermission(): Promise<boolean> {
  if (typeof window === "undefined" || !("Notification" in window)) return false;

  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;

  const result = await Notification.requestPermission();
  return result === "granted";
}

export function getNotificationPermission(): "granted" | "denied" | "default" | "unsupported" {
  if (typeof window === "undefined" || !("Notification" in window)) return "unsupported";
  return Notification.permission;
}

// ── Capacitor Push Notifications ─────────────────────────────────────────────

export async function initCapacitorPush(
  onReceived: (title: string, body: string) => void,
): Promise<void> {
  try {
    const { PushNotifications } = await import("@capacitor/push-notifications");

    const result = await PushNotifications.requestPermissions();
    if (result.receive !== "granted") return;

    await PushNotifications.register();

    PushNotifications.addListener("registration", async (token) => {
      // Send FCM/APNs token to backend
      await fetch(`${API_BASE}/api/v1/notifications/device-token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: token.value, platform: "capacitor" }),
      });
    });

    PushNotifications.addListener("pushNotificationReceived", (notification) => {
      onReceived(
        notification.title ?? "Sancta Nexus",
        notification.body ?? "Czas na modlitwę",
      );
    });
  } catch {
    // Not running in Capacitor — ignore
  }
}

// ── Local Scheduled Notifications (offline prayer reminders) ─────────────────

export interface PrayerReminder {
  id: number;
  hour: number;
  minute: number;
  title: string;
  body: string;
  url: string;
}

export const DEFAULT_REMINDERS: PrayerReminder[] = [
  {
    id: 1,
    hour: 6,
    minute: 0,
    title: "🌅 Jutrznia — Sancta Nexus",
    body: "Dobry poranek! Lectio Divina czeka. Zacznij dzień ze Słowem.",
    url: "/lectio-divina",
  },
  {
    id: 2,
    hour: 12,
    minute: 0,
    title: "☀️ Modlitwa południowa",
    body: "Czas zatrzymać się i porozmawiać z Bogiem.",
    url: "/breviary",
  },
  {
    id: 3,
    hour: 18,
    minute: 0,
    title: "🌇 Nieszpory",
    body: "Liturgia Godzin — zakończ dzień modlitwą.",
    url: "/breviary",
  },
  {
    id: 4,
    hour: 21,
    minute: 0,
    title: "🌙 Kompleta",
    body: "Rachunek sumienia i nocna modlitwa Kościoła.",
    url: "/breviary",
  },
];

export async function scheduleLocalReminders(
  reminders: PrayerReminder[] = DEFAULT_REMINDERS,
): Promise<void> {
  try {
    const { LocalNotifications } = await import(
      "@capacitor/local-notifications"
    );

    const perm = await LocalNotifications.requestPermissions();
    if (perm.display !== "granted") return;

    // Cancel existing prayer reminders first
    const pending = await LocalNotifications.getPending();
    const prayerIds = DEFAULT_REMINDERS.map((r) => ({ id: r.id }));
    const toCancel = pending.notifications
      .filter((n) => prayerIds.some((p) => p.id === n.id))
      .map((n) => ({ id: n.id }));

    if (toCancel.length > 0) {
      await LocalNotifications.cancel({ notifications: toCancel });
    }

    // Schedule recurring daily notifications
    const notifications = reminders.map((r) => {
      const scheduleAt = new Date();
      scheduleAt.setHours(r.hour, r.minute, 0, 0);
      if (scheduleAt.getTime() < Date.now()) {
        scheduleAt.setDate(scheduleAt.getDate() + 1);
      }
      return {
        id: r.id,
        title: r.title,
        body: r.body,
        schedule: { at: scheduleAt, repeats: true, every: "day" as const },
        extra: { url: r.url },
        smallIcon: "ic_stat_cross",
        iconColor: "#d4af37",
      };
    });

    await LocalNotifications.schedule({ notifications });
  } catch {
    // Not in Capacitor — fall back to web scheduling
    scheduleWebReminders(reminders);
  }
}

// ── Web fallback reminders (service worker postMessage) ──────────────────────

function scheduleWebReminders(reminders: PrayerReminder[]): void {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;

  navigator.serviceWorker.ready.then((reg) => {
    reg.active?.postMessage({
      type: "SCHEDULE_PRAYER_REMINDERS",
      reminders,
    });
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
