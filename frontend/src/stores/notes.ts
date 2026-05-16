/**
 * Verse notes store — personal scripture reflections.
 *
 * Primary storage: backend API (/api/v1/notes).
 * Offline fallback: localStorage (same key as before for backwards compat).
 *
 * Strategy:
 *  - On load: fetch from backend; merge with any localStorage data not yet synced.
 *  - On save/delete: write to backend first; fall back to localStorage on API error.
 *  - isBackendSynced flag lets UI show sync status.
 */
import { create } from "zustand";
import { api } from "@/lib/api";

interface NoteItem {
  ref: string;
  text: string;
  saved_at?: string;
}

interface NotesState {
  notes: Record<string, string>;
  isBackendSynced: boolean;
  isLoading: boolean;
}

interface NotesActions {
  loadFromStorage: () => void;
  loadFromBackend: () => Promise<void>;
  getNote: (ref: string) => string;
  saveNote: (ref: string, text: string) => Promise<void>;
  deleteNote: (ref: string) => Promise<void>;
  getAllNotes: () => { ref: string; text: string; savedAt: string }[];
}

const STORAGE_KEY = "sancta_nexus_notes";

function readLocalStorage(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, string>) : {};
  } catch {
    return {};
  }
}

function writeLocalStorage(notes: Record<string, string>): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
  }
}

export const useNotesStore = create<NotesState & NotesActions>((set, get) => ({
  notes: {},
  isBackendSynced: false,
  isLoading: false,

  loadFromStorage: () => {
    set({ notes: readLocalStorage() });
  },

  loadFromBackend: async () => {
    set({ isLoading: true });
    try {
      const items = await api.get<NoteItem[]>("/api/v1/notes");
      const notes: Record<string, string> = {};
      for (const item of items) {
        notes[item.ref] = item.text;
      }
      // Merge: backend wins; keep any local-only refs not yet uploaded.
      const local = readLocalStorage();
      for (const [ref, text] of Object.entries(local)) {
        if (!(ref in notes) && text.trim()) {
          notes[ref] = text;
          // Fire-and-forget upload of locally-only note.
          api
            .put(`/api/v1/notes/${encodeURIComponent(ref)}`, { text })
            .catch(() => {/* will retry next time */});
        }
      }
      writeLocalStorage(notes);
      set({ notes, isBackendSynced: true, isLoading: false });
    } catch {
      // Backend unavailable — fall back to localStorage.
      set({ notes: readLocalStorage(), isBackendSynced: false, isLoading: false });
    }
  },

  getNote: (ref) => get().notes[ref] ?? "",

  saveNote: async (ref, text) => {
    // Optimistic update.
    const notes = { ...get().notes, [ref]: text };
    set({ notes });
    writeLocalStorage(notes);

    try {
      await api.put(`/api/v1/notes/${encodeURIComponent(ref)}`, { text });
      set({ isBackendSynced: true });
    } catch {
      set({ isBackendSynced: false });
    }
  },

  deleteNote: async (ref) => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { [ref]: _removed, ...rest } = get().notes;
    set({ notes: rest });
    writeLocalStorage(rest);

    try {
      await api.delete(`/api/v1/notes/${encodeURIComponent(ref)}`);
    } catch {
      set({ isBackendSynced: false });
    }
  },

  getAllNotes: () =>
    Object.entries(get().notes)
      .filter(([, text]) => text.trim())
      .map(([ref, text]) => ({ ref, text, savedAt: new Date().toISOString() })),
}));
