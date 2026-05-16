/**
 * Progress store — prayer streak, session history, themes, journey progress.
 *
 * Primary storage: backend API (/api/v1/progress).
 * Offline fallback: localStorage (same key as before).
 *
 * On first load: fetch stats from backend, merge with any locally recorded
 * sessions not yet uploaded.
 * On recordSession: POST to backend; always write to localStorage too so data
 * survives network interruptions.
 */
import { create } from "zustand";
import { api } from "@/lib/api";

export interface SessionRecord {
  id: string;
  date: string; // ISO date string
  passageRef: string;
  emotion: string;
  durationMinutes: number;
}

interface ProgressState {
  prayerStreak: number;
  totalSessions: number;
  lastPrayerDate: string | null;
  sessions: SessionRecord[]; // local cache (for offline streak)
  themes: { name: string; count: number }[];
  journeyProgress: { purgativa: number; illuminativa: number; unitiva: number };
  isBackendSynced: boolean;
}

interface ProgressActions {
  loadFromStorage: () => void;
  loadFromBackend: () => Promise<void>;
  recordSession: (session: Omit<SessionRecord, "id">, theme?: string) => Promise<void>;
  addTheme: (theme: string) => void;
}

const STORAGE_KEY = "sancta_nexus_progress";

function computeStreak(sessions: SessionRecord[]): number {
  if (sessions.length === 0) return 0;
  const sorted = [...sessions].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  let streak = 0;
  const expected = new Date(today);
  for (const s of sorted) {
    const d = new Date(s.date);
    d.setHours(0, 0, 0, 0);
    if (d.getTime() === expected.getTime()) {
      streak++;
      expected.setDate(expected.getDate() - 1);
    } else if (d.getTime() < expected.getTime()) {
      break;
    }
  }
  return streak;
}

function computeJourneyProgress(total: number) {
  return {
    purgativa: Math.min(100, total * 5),
    illuminativa: total >= 20 ? Math.min(100, (total - 20) * 5) : 0,
    unitiva: total >= 40 ? Math.min(100, (total - 40) * 5) : 0,
  };
}

function readLocal(): Partial<ProgressState> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Partial<ProgressState>) : {};
  } catch {
    return {};
  }
}

function writeLocal(data: { sessions: SessionRecord[]; themes: { name: string; count: number }[] }) {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }
}

export const useProgressStore = create<ProgressState & ProgressActions>((set, get) => ({
  prayerStreak: 0,
  totalSessions: 0,
  lastPrayerDate: null,
  sessions: [],
  themes: [],
  journeyProgress: { purgativa: 0, illuminativa: 0, unitiva: 0 },
  isBackendSynced: false,

  loadFromStorage: () => {
    const data = readLocal();
    const sessions = data.sessions ?? [];
    set({
      sessions,
      themes: data.themes ?? [],
      totalSessions: sessions.length,
      prayerStreak: computeStreak(sessions),
      lastPrayerDate: sessions[0]?.date ?? null,
      journeyProgress: computeJourneyProgress(sessions.length),
    });
  },

  loadFromBackend: async () => {
    try {
      const stats = await api.get<{
        prayer_streak: number;
        total_sessions: number;
        last_prayer_date: string | null;
        themes: { name: string; count: number }[];
        journey_progress: { purgativa: number; illuminativa: number; unitiva: number };
      }>("/api/v1/progress");

      const local = readLocal();
      const localSessions = local.sessions ?? [];

      set({
        prayerStreak: stats.prayer_streak,
        totalSessions: stats.total_sessions,
        lastPrayerDate: stats.last_prayer_date,
        themes: stats.themes,
        journeyProgress: stats.journey_progress,
        sessions: localSessions, // keep local session records for offline use
        isBackendSynced: true,
      });

      // Upload any locally-stored sessions not yet in the backend.
      const uploadCutoff = stats.last_prayer_date
        ? new Date(stats.last_prayer_date).getTime()
        : 0;
      const unsynced = localSessions.filter(
        (s) => new Date(s.date).getTime() > uploadCutoff
      );
      for (const s of unsynced) {
        api
          .post("/api/v1/progress/session", {
            date: s.date,
            passage_ref: s.passageRef,
            emotion: s.emotion,
            duration_minutes: s.durationMinutes,
          })
          .catch(() => {/* will retry on next load */});
      }
    } catch {
      // Backend unavailable — use localStorage data.
      get().loadFromStorage();
      set({ isBackendSynced: false });
    }
  },

  recordSession: async (session, theme) => {
    const newSession: SessionRecord = {
      ...session,
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    };
    const prev = get();
    const sessions = [newSession, ...prev.sessions].slice(0, 200);

    // Optimistic local update.
    set({
      sessions,
      themes: prev.themes,
      totalSessions: sessions.length,
      prayerStreak: computeStreak(sessions),
      lastPrayerDate: newSession.date,
      journeyProgress: computeJourneyProgress(sessions.length),
    });
    writeLocal({ sessions, themes: prev.themes });

    // Persist to backend.
    try {
      await api.post("/api/v1/progress/session", {
        date: session.date,
        passage_ref: session.passageRef,
        emotion: session.emotion,
        duration_minutes: session.durationMinutes,
        theme: theme ?? null,
      });
      set({ isBackendSynced: true });
    } catch {
      set({ isBackendSynced: false });
    }
  },

  addTheme: (theme: string) => {
    const prev = get();
    const existing = prev.themes.find((t) => t.name === theme);
    const themes = existing
      ? prev.themes.map((t) =>
          t.name === theme ? { ...t, count: t.count + 1 } : t
        )
      : [...prev.themes, { name: theme, count: 1 }];
    const sorted = themes.sort((a, b) => b.count - a.count).slice(0, 10);
    set({ themes: sorted });
    const raw = readLocal();
    writeLocal({ sessions: raw.sessions ?? [], themes: sorted });
  },
}));
