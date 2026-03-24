/**
 * Offline-first prayer cache using IndexedDB.
 *
 * Stores daily scripture, generated prayers, and reflections so the app
 * works fully offline — in church, on retreat, in the mountains.
 *
 * Database: "sancta-nexus-offline"
 * Stores:
 *   - scripture   : daily liturgical passages keyed by date (YYYY-MM-DD)
 *   - prayers     : generated prayer texts keyed by session ID
 *   - reflections : meditation layers keyed by passage reference
 *   - meta        : last sync timestamp etc.
 */

const DB_NAME = "sancta-nexus-offline";
const DB_VERSION = 1;

type StoreName = "scripture" | "prayers" | "reflections" | "meta";

// ── DB init ───────────────────────────────────────────────────────────────────

let _db: IDBDatabase | null = null;

function openDB(): Promise<IDBDatabase> {
  if (_db) return Promise.resolve(_db);

  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);

    req.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains("scripture")) {
        db.createObjectStore("scripture", { keyPath: "date" });
      }
      if (!db.objectStoreNames.contains("prayers")) {
        db.createObjectStore("prayers", { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains("reflections")) {
        db.createObjectStore("reflections", { keyPath: "ref" });
      }
      if (!db.objectStoreNames.contains("meta")) {
        db.createObjectStore("meta", { keyPath: "key" });
      }
    };

    req.onsuccess = (e) => {
      _db = (e.target as IDBOpenDBRequest).result;
      resolve(_db);
    };

    req.onerror = () => reject(req.error);
  });
}

// ── Generic helpers ───────────────────────────────────────────────────────────

async function put<T>(store: StoreName, value: T): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(value);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function get<T>(store: StoreName, key: string): Promise<T | undefined> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readonly");
    const req = tx.objectStore(store).get(key);
    req.onsuccess = () => resolve(req.result as T | undefined);
    req.onerror = () => reject(req.error);
  });
}

async function getAll<T>(store: StoreName): Promise<T[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readonly");
    const req = tx.objectStore(store).getAll();
    req.onsuccess = () => resolve(req.result as T[]);
    req.onerror = () => reject(req.error);
  });
}

async function deleteOldEntries(store: StoreName, keepDays = 7): Promise<void> {
  const db = await openDB();
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - keepDays);
  const cutoffStr = cutoff.toISOString().split("T")[0];

  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    const objStore = tx.objectStore(store);
    const req = objStore.openCursor();
    req.onsuccess = (e) => {
      const cursor = (e.target as IDBRequest<IDBCursorWithValue>).result;
      if (!cursor) return;
      const key = cursor.key as string;
      if (key < cutoffStr) cursor.delete();
      cursor.continue();
    };
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// ── Scripture cache ───────────────────────────────────────────────────────────

export interface CachedScripture {
  date: string; // YYYY-MM-DD (keyPath)
  passage: {
    book: string;
    chapter: number;
    startVerse: number;
    endVerse: number;
    text: string;
    translation: string;
    historicalContext?: string;
    patristicNote?: string;
    originalLanguageKey?: string;
    catechismRef?: string;
  };
  liturgicalContext?: {
    season: string;
    feast: string | null;
    readings: { label: string; reference: string }[];
  };
  cachedAt: number; // Date.now()
}

export async function cacheScripture(data: CachedScripture): Promise<void> {
  await put("scripture", data);
}

export async function getCachedScripture(
  date: string,
): Promise<CachedScripture | undefined> {
  return get<CachedScripture>("scripture", date);
}

export async function getTodayScripture(): Promise<CachedScripture | undefined> {
  const today = new Date().toISOString().split("T")[0];
  return getCachedScripture(today);
}

// ── Prayer cache ──────────────────────────────────────────────────────────────

export interface CachedPrayer {
  id: string;         // session ID (keyPath)
  date: string;
  prayerText: string;
  passage?: string;   // passage reference
  emotion?: string;
  cachedAt: number;
}

export async function cachePrayer(prayer: CachedPrayer): Promise<void> {
  await put("prayers", prayer);
}

export async function getCachedPrayer(
  id: string,
): Promise<CachedPrayer | undefined> {
  return get<CachedPrayer>("prayers", id);
}

export async function getAllCachedPrayers(): Promise<CachedPrayer[]> {
  return getAll<CachedPrayer>("prayers");
}

// ── Reflection cache ──────────────────────────────────────────────────────────

export interface CachedReflection {
  ref: string; // passage reference (keyPath)
  layers: {
    literalis: string;
    allegoricus: string;
    moralis: string;
    anagogicus: string;
  };
  questions: { text: string; layer: string; scriptureEcho: string }[];
  cachedAt: number;
}

export async function cacheReflection(r: CachedReflection): Promise<void> {
  await put("reflections", r);
}

export async function getCachedReflection(
  ref: string,
): Promise<CachedReflection | undefined> {
  return get<CachedReflection>("reflections", ref);
}

// ── Meta / sync state ─────────────────────────────────────────────────────────

export async function setMeta(key: string, value: unknown): Promise<void> {
  await put("meta", { key, value, updatedAt: Date.now() });
}

export async function getMeta<T>(key: string): Promise<T | undefined> {
  const row = await get<{ key: string; value: T }>("meta", key);
  return row?.value;
}

// ── Pre-fetch today's scripture ───────────────────────────────────────────────

const API_BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
    : "";

export async function prefetchTodayScripture(): Promise<void> {
  if (typeof window === "undefined" || typeof indexedDB === "undefined") return;

  const today = new Date().toISOString().split("T")[0];

  // Check freshness — re-fetch after 6 hours
  const cached = await getCachedScripture(today);
  if (cached && Date.now() - cached.cachedAt < 6 * 3600_000) return;

  try {
    const [scriptureRes, liturgyRes] = await Promise.all([
      fetch(`${API_BASE}/api/v1/lectio-divina/scripture/${today}`),
      fetch(`${API_BASE}/api/v1/lectio-divina/liturgical-context?date=${today}`),
    ]);

    if (scriptureRes.ok) {
      const data = await scriptureRes.json();
      const liturgy = liturgyRes.ok ? await liturgyRes.json() : undefined;
      await cacheScripture({
        date: today,
        passage: data,
        liturgicalContext: liturgy,
        cachedAt: Date.now(),
      });
    }
  } catch {
    // Silently fail — network unavailable
  }

  // Clean entries older than 7 days
  await deleteOldEntries("scripture", 7);
}
