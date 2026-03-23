/**
 * Progress store — persists prayer streak and session counts to localStorage.
 * Works without auth; when backend is available the data is synced from API.
 */
import { create } from "zustand";

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
  sessions: SessionRecord[];
  themes: { name: string; count: number }[];
  journeyProgress: { purgativa: number; illuminativa: number; unitiva: number };
}

interface ProgressActions {
  loadFromStorage: () => void;
  recordSession: (session: Omit<SessionRecord, "id">) => void;
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
  let expected = new Date(today);

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
  // Simple progression: every 5 sessions = 10% on next stage
  const purgativa = Math.min(100, total * 5);
  const illuminativa = total >= 20 ? Math.min(100, (total - 20) * 5) : 0;
  const unitiva = total >= 40 ? Math.min(100, (total - 40) * 5) : 0;
  return { purgativa, illuminativa, unitiva };
}

export const useProgressStore = create<ProgressState & ProgressActions>(
  (set, get) => ({
    prayerStreak: 0,
    totalSessions: 0,
    lastPrayerDate: null,
    sessions: [],
    themes: [],
    journeyProgress: { purgativa: 0, illuminativa: 0, unitiva: 0 },

    loadFromStorage: () => {
      if (typeof window === "undefined") return;
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const data = JSON.parse(raw) as Partial<ProgressState>;
        const sessions = data.sessions ?? [];
        set({
          sessions,
          themes: data.themes ?? [],
          totalSessions: sessions.length,
          prayerStreak: computeStreak(sessions),
          lastPrayerDate: sessions[0]?.date ?? null,
          journeyProgress: computeJourneyProgress(sessions.length),
        });
      } catch {
        // corrupt storage — reset
        localStorage.removeItem(STORAGE_KEY);
      }
    },

    recordSession: (session) => {
      const newSession: SessionRecord = {
        ...session,
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      };
      const prev = get();
      const sessions = [newSession, ...prev.sessions].slice(0, 200); // cap at 200

      const updated: Partial<ProgressState> = {
        sessions,
        themes: prev.themes,
        totalSessions: sessions.length,
        prayerStreak: computeStreak(sessions),
        lastPrayerDate: newSession.date,
        journeyProgress: computeJourneyProgress(sessions.length),
      };
      set(updated);
      if (typeof window !== "undefined") {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ sessions: updated.sessions, themes: updated.themes })
        );
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
      if (typeof window !== "undefined") {
        const raw = localStorage.getItem(STORAGE_KEY);
        const data = raw ? JSON.parse(raw) : {};
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...data, themes: sorted }));
      }
    },
  })
);
