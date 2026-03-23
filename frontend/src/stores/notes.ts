/**
 * Personal notes store — persists verse reflections to localStorage.
 * Keyed by verse reference string (e.g. "J 3,16").
 */
import { create } from "zustand";

interface NotesState {
  notes: Record<string, string>;
}

interface NotesActions {
  loadFromStorage: () => void;
  getNote: (ref: string) => string;
  saveNote: (ref: string, text: string) => void;
  deleteNote: (ref: string) => void;
  getAllNotes: () => { ref: string; text: string; savedAt: string }[];
}

const STORAGE_KEY = "sancta_nexus_notes";

export const useNotesStore = create<NotesState & NotesActions>((set, get) => ({
  notes: {},

  loadFromStorage: () => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        set({ notes: JSON.parse(raw) });
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  },

  getNote: (ref) => {
    // Lazy load from storage on first access
    if (typeof window !== "undefined") {
      const state = get();
      if (Object.keys(state.notes).length === 0) {
        try {
          const raw = localStorage.getItem(STORAGE_KEY);
          if (raw) {
            const notes = JSON.parse(raw) as Record<string, string>;
            set({ notes });
            return notes[ref] ?? "";
          }
        } catch { /* ignore */ }
      }
    }
    return get().notes[ref] ?? "";
  },

  saveNote: (ref, text) => {
    const notes = { ...get().notes, [ref]: text };
    set({ notes });
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
    }
  },

  deleteNote: (ref) => {
    const { [ref]: _removed, ...rest } = get().notes;
    set({ notes: rest });
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(rest));
    }
  },

  getAllNotes: () => {
    return Object.entries(get().notes)
      .filter(([, text]) => text.trim())
      .map(([ref, text]) => ({ ref, text, savedAt: new Date().toISOString() }));
  },
}));
