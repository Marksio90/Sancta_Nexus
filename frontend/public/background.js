/**
 * Sancta Nexus — Capacitor Background Runner
 *
 * Uruchamiany przez @capacitor/background-runner co 24h.
 * Wykonuje lekkie zadania offline: pre-fetch liturgii, planowanie lokalnych powiadomień.
 *
 * Dostępne API w Background Runner:
 *   - CapacitorKV (klucz-wartość)
 *   - fetch (ograniczony)
 *   - Notifications.schedule (lokalne powiadomienia)
 *   NIE MA dostępu do: DOM, window, localStorage, Capacitor plugins
 */

// ── Stałe ────────────────────────────────────────────────────────────────────

const API_BASE = "https://api.sanctanexus.org";
const REMINDER_KEY = "daily_reminder_time";
const SAINT_CACHE_KEY = "cached_saint_today";
const SAINT_CACHE_DATE_KEY = "cached_saint_date";

// ── Pomocnicze ────────────────────────────────────────────────────────────────

function todayISO() {
  return new Date().toISOString().split("T")[0];
}

async function fetchSaintToday() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/breviary/saint-today`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// ── Główna funkcja (wywoływana przez Background Runner) ───────────────────────

addEventListener("background", async (event) => {
  const today = todayISO();

  // Sprawdź czy święty dnia jest już w cache
  const cachedDate = await CapacitorKV.get(SAINT_CACHE_DATE_KEY);
  let saint = null;

  if (cachedDate !== today) {
    // Pre-fetch świętego dnia
    saint = await fetchSaintToday();
    if (saint) {
      await CapacitorKV.set(SAINT_CACHE_KEY, JSON.stringify(saint));
      await CapacitorKV.set(SAINT_CACHE_DATE_KEY, today);
    }
  } else {
    const cached = await CapacitorKV.get(SAINT_CACHE_KEY);
    if (cached) {
      try { saint = JSON.parse(cached); } catch {}
    }
  }

  // Zaplanuj poranne powiadomienie
  const reminderTime = (await CapacitorKV.get(REMINDER_KEY)) || "07:00";
  const [hour, minute] = reminderTime.split(":").map(Number);

  const now = new Date();
  const fireDate = new Date(now);
  fireDate.setHours(hour, minute, 0, 0);

  // Jeśli godzina już minęła dziś → zaplanuj na jutro
  if (fireDate <= now) {
    fireDate.setDate(fireDate.getDate() + 1);
  }

  const title = saint
    ? `${saint.icon || "✝"} ${saint.name}`
    : "Sancta Nexus — Dzień dobry!";

  const body = saint
    ? `Módlmy się przez wstawiennictwo patrona dnia. Niech Pan błogosławi Twój dzień!`
    : "Zacznij dzień z modlitwą — Bóg czeka na Twoje serce.";

  await Notifications.schedule([
    {
      id: 1001,
      title,
      body,
      schedule: { at: fireDate },
      actionTypeId: "OPEN_DZISIAJ",
      extra: { url: "/dzisiaj" },
    },
  ]);

  event.detail.completed();
});
