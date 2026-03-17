import { create } from "zustand";
import { api } from "@/lib/api";
import type {
  LectioDivinaSession,
  LectioDivinaStage,
  SpiritualTradition,
} from "@/types";

interface EmotionAnalysis {
  emotion: string;
  confidence: number;
  details?: string;
}

interface LectioState {
  currentSession: LectioDivinaSession | null;
  emotionAnalysis: EmotionAnalysis | null;
  history: LectioDivinaSession[];
  isLoading: boolean;
  error: string | null;
}

interface LectioActions {
  startSession: (userId: string, tradition: SpiritualTradition) => Promise<void>;
  analyzeEmotion: (text: string) => Promise<EmotionAnalysis>;
  submitReflection: (stage: LectioDivinaStage, text: string) => Promise<void>;
  getHistory: () => Promise<void>;
  clearError: () => void;
  resetSession: () => void;
}

export const useLectioStore = create<LectioState & LectioActions>((set, get) => ({
  currentSession: null,
  emotionAnalysis: null,
  history: [],
  isLoading: false,
  error: null,

  startSession: async (userId: string, tradition: SpiritualTradition) => {
    set({ isLoading: true, error: null });
    try {
      const session = await api.post<LectioDivinaSession>(
        "/api/v1/lectio-divina/sessions",
        { user_id: userId, tradition }
      );
      set({ currentSession: session, isLoading: false, emotionAnalysis: null });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Nie udało się rozpocząć sesji",
      });
    }
  },

  analyzeEmotion: async (text: string) => {
    set({ isLoading: true, error: null });
    try {
      const session = get().currentSession;
      const analysis = await api.post<EmotionAnalysis>(
        "/api/v1/lectio-divina/analyze-emotion",
        {
          text,
          session_id: session?.id,
        }
      );
      set({ emotionAnalysis: analysis, isLoading: false });
      return analysis;
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Nie udało się przeanalizować emocji",
      });
      throw err;
    }
  },

  submitReflection: async (stage: LectioDivinaStage, text: string) => {
    set({ isLoading: true, error: null });
    try {
      const session = get().currentSession;
      if (!session) throw new Error("Brak aktywnej sesji");

      const updated = await api.post<LectioDivinaSession>(
        `/api/v1/lectio-divina/sessions/${session.id}/reflections`,
        { stage, text }
      );
      set({ currentSession: updated, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Nie udało się zapisać refleksji",
      });
    }
  },

  getHistory: async () => {
    set({ isLoading: true, error: null });
    try {
      const history = await api.get<LectioDivinaSession[]>(
        "/api/v1/lectio-divina/sessions"
      );
      set({ history, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Nie udało się pobrać historii",
      });
    }
  },

  clearError: () => set({ error: null }),

  resetSession: () => set({ currentSession: null, emotionAnalysis: null }),
}));
