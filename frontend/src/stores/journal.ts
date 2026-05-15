import { create } from "zustand";
import { api } from "@/lib/api";

export interface JournalEntry {
  id: string;
  title: string | null;
  content: string;
  tags: string[];
  mood: string | null;
  scripture_reference: string | null;
  created_at: string;
  updated_at: string;
}

interface JournalListResponse {
  entries: JournalEntry[];
  total: number;
  page: number;
  page_size: number;
}

export type CreateEntryData = {
  title?: string;
  content: string;
  tags?: string[];
  mood?: string;
  scripture_reference?: string;
};

export type UpdateEntryData = Partial<CreateEntryData>;

interface JournalStore {
  entries: JournalEntry[];
  total: number;
  currentPage: number;
  isLoading: boolean;
  error: string | null;

  loadEntries: (page?: number, search?: string, mood?: string) => Promise<void>;
  createEntry: (data: CreateEntryData) => Promise<JournalEntry>;
  updateEntry: (id: string, data: UpdateEntryData) => Promise<void>;
  deleteEntry: (id: string) => Promise<void>;
  clearError: () => void;
}

export const useJournalStore = create<JournalStore>((set) => ({
  entries: [],
  total: 0,
  currentPage: 1,
  isLoading: false,
  error: null,

  loadEntries: async (page = 1, search?: string, mood?: string) => {
    set({ isLoading: true, error: null });
    try {
      const params: Record<string, string> = {
        page: String(page),
        page_size: "20",
      };
      if (search) params.search = search;
      if (mood) params.mood = mood;

      const res = await api.get<JournalListResponse>(
        "/api/v1/journal/entries",
        { params }
      );

      set({
        entries: res.entries,
        total: res.total,
        currentPage: res.page,
        isLoading: false,
      });
    } catch (err) {
      set({
        isLoading: false,
        error:
          err instanceof Error
            ? err.message
            : "Nie udało się pobrać wpisów dziennika",
      });
    }
  },

  createEntry: async (data: CreateEntryData) => {
    set({ error: null });
    const res = await api.post<JournalEntry>("/api/v1/journal/entries", data);
    set((state) => ({
      entries: [res, ...state.entries],
      total: state.total + 1,
    }));
    return res;
  },

  updateEntry: async (id: string, data: UpdateEntryData) => {
    set({ error: null });
    const res = await api.put<JournalEntry>(
      `/api/v1/journal/entries/${id}`,
      data
    );
    set((state) => ({
      entries: state.entries.map((e) => (e.id === id ? res : e)),
    }));
  },

  deleteEntry: async (id: string) => {
    set({ error: null });
    await api.delete(`/api/v1/journal/entries/${id}`);
    set((state) => ({
      entries: state.entries.filter((e) => e.id !== id),
      total: state.total - 1,
    }));
  },

  clearError: () => set({ error: null }),
}));
