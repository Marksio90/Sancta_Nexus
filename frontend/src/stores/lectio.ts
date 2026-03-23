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
  generateSession: (emotionText: string, tradition?: string) => Promise<void>;
  startSession: (userId: string, tradition: SpiritualTradition) => Promise<void>;
  analyzeEmotion: (text: string, sessionId?: string) => Promise<EmotionAnalysis>;
  submitReflection: (stage: LectioDivinaStage, text: string, sessionId: string) => Promise<void>;
  getHistory: (userId: string) => Promise<void>;
  clearError: () => void;
  resetSession: () => void;
}

// Map snake_case pipeline response to camelCase LectioDivinaSession
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapPipelineResult(data: Record<string, any>, emotionText: string): LectioDivinaSession {
  const s = data.scripture ?? {};
  const m = data.meditation ?? {};
  const p = data.prayer ?? {};
  const c = data.contemplation ?? {};
  const a = data.action ?? {};
  const examen = a.evening_examen ?? {};

  return {
    id: crypto.randomUUID(),
    date: new Date().toISOString(),
    createdAt: new Date(),
    emotion: emotionText,
    meditationResponse: "",
    generatedPrayer: p.prayer_text ?? "",
    challenge: a.challenge_text ?? "",
    completedStages: [],
    tradition: data.tradition ?? "",
    kerygmaticTheme: data.kerygmatic_theme ?? "",

    passage: Object.keys(s).length > 0 ? {
      book: s.book ?? "",
      chapter: s.chapter ?? 1,
      startVerse: s.verse_start ?? 1,
      endVerse: s.verse_end ?? 1,
      text: s.text ?? "",
      translation: s.translation ?? "",
      historicalContext: s.historical_context,
      patristicNote: s.patristic_note,
      originalLanguageKey: s.original_language_key,
      catechismRef: s.catechism_ref,
    } : undefined as unknown as LectioDivinaSession["passage"],

    meditation: Object.keys(m).length > 0 ? {
      questions: (m.questions ?? []).map((q: Record<string, string>) => ({
        text: q.text ?? "",
        layer: q.layer ?? "literalis",
        scriptureEcho: q.scripture_echo,
      })),
      reflectionLayers: {
        literalis: m.reflection_layers?.literalis ?? "",
        allegoricus: m.reflection_layers?.allegoricus ?? "",
        moralis: m.reflection_layers?.moralis ?? "",
        anagogicus: m.reflection_layers?.anagogicus ?? "",
      },
      patristicInsight: m.patristic_insight,
      keyWord: m.key_word,
    } : undefined,

    prayer: Object.keys(p).length > 0 ? {
      prayerText: p.prayer_text ?? "",
      tradition: p.tradition ?? "",
      elements: p.elements ?? [],
      spiritualMovement: p.spiritual_movement,
    } : undefined,

    contemplation: Object.keys(c).length > 0 ? {
      guidanceText: c.guidance_text ?? "",
      sacredWord: c.sacred_word,
      sacredWordMeaning: c.sacred_word_meaning,
      breathingPattern: c.breathing_pattern ?? {
        inhaleSeconds: 4, holdSeconds: 2, exhaleSeconds: 6, cycles: 5,
      },
      jesusPrayerRhythm: c.jesus_prayer_rhythm,
      durationMinutes: c.duration_minutes ?? 3,
      ambientSuggestion: c.ambient_suggestion ?? "",
      closingPrayer: c.closing_prayer,
    } : undefined,

    action: Object.keys(a).length > 0 ? {
      challengeText: a.challenge_text ?? "",
      scriptureAnchor: a.scripture_anchor,
      difficulty: a.difficulty ?? "easy",
      category: a.category ?? "",
      virtueFocus: a.virtue_focus,
      eveningExamen: {
        retrospection: examen.retrospection ?? "",
        divinePresence: examen.divine_presence ?? "",
        resolution: examen.resolution ?? "",
      },
    } : undefined,
  };
}

export const useLectioStore = create<LectioState & LectioActions>((set, get) => ({
  currentSession: null,
  emotionAnalysis: null,
  history: [],
  isLoading: false,
  error: null,

  generateSession: async (emotionText: string, tradition = "") => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.post<Record<string, unknown>>(
        "/api/v1/lectio-divina/run",
        { emotion_text: emotionText, tradition, user_id: "anonymous" }
      );
      if (data.error) throw new Error(data.error as string);
      const session = mapPipelineResult(data as Record<string, unknown>, emotionText);
      set({ currentSession: session, isLoading: false });
    } catch (err) {
      // Pipeline unavailable — clear session so page falls back to mock data
      set({
        currentSession: null,
        isLoading: false,
        error: err instanceof Error ? err.message : "Nie udało się uruchomić sesji",
      });
    }
  },

  startSession: async (userId: string, tradition: SpiritualTradition) => {
    set({ isLoading: true, error: null });
    try {
      const session = await api.post<LectioDivinaSession>(
        "/api/v1/lectio-divina/session",
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

  analyzeEmotion: async (text: string, sessionId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const analysis = await api.post<EmotionAnalysis>(
        "/api/v1/lectio-divina/emotion",
        { text, session_id: sessionId, user_id: "anonymous" }
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

  submitReflection: async (stage: LectioDivinaStage, text: string, sessionId: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.post(
        "/api/v1/lectio-divina/reflection",
        { session_id: sessionId, user_id: "anonymous", stage, reflection_text: text }
      );
      set({ isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Nie udało się zapisać refleksji",
      });
    }
  },

  getHistory: async (userId: string) => {
    set({ isLoading: true, error: null });
    try {
      const history = await api.get<LectioDivinaSession[]>(
        `/api/v1/lectio-divina/history/${userId}`
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
