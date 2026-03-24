import { create } from "zustand";
import { api } from "@/lib/api";
import type { SpiritualTradition } from "@/types";

interface DirectorSession {
  session_id: string;
  user_id: string;
  tradition: SpiritualTradition;
  status: string;
  created_at: string;
}

interface TraditionInfo {
  id: SpiritualTradition;
  name: string;
  description: string;
  key_practices: string[];
}

export interface DirectorMessage {
  id: string;
  role: "user" | "director";
  content: string;
  timestamp: Date;
  scriptures?: { reference: string; passage: string; explanation: string }[];
  followUps?: string[];
  prayerSuggestion?: string;
  spiritualState?: string;
}

interface StartSessionApiResponse {
  session_id: string;
  user_id: string;
  tradition: SpiritualTradition;
  status: string;
  created_at: string;
  opening_message: string;
}

interface SendMessageApiResponse {
  session_id: string;
  director_response: string;
  emotion_analysis: Record<string, unknown>;
  suggested_scriptures: { reference: string; passage: string; explanation: string }[];
  spiritual_state?: string;
  follow_up_questions: string[];
  prayer_suggestion?: string;
}

interface DirectorState {
  currentSession: DirectorSession | null;
  messages: DirectorMessage[];
  isTyping: boolean;
  isLoading: boolean;
  traditions: TraditionInfo[];
  error: string | null;
}

interface DirectorActions {
  startSession: (userId: string, tradition: SpiritualTradition) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  loadTraditions: () => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const useDirectorStore = create<DirectorState & DirectorActions>(
  (set, get) => ({
    currentSession: null,
    messages: [],
    isTyping: false,
    isLoading: false,
    traditions: [],
    error: null,

    startSession: async (userId: string, tradition: SpiritualTradition) => {
      set({ isLoading: true, error: null, messages: [], currentSession: null });
      try {
        const res = await api.post<StartSessionApiResponse>(
          "/api/v1/spiritual-director/session",
          { user_id: userId, tradition }
        );
        const session: DirectorSession = {
          session_id: res.session_id,
          user_id: res.user_id,
          tradition: res.tradition,
          status: res.status,
          created_at: res.created_at,
        };
        const openingMessage: DirectorMessage = {
          id: crypto.randomUUID(),
          role: "director",
          content: res.opening_message,
          timestamp: new Date(),
        };
        set({ currentSession: session, messages: [openingMessage], isLoading: false });
      } catch (err) {
        set({
          isLoading: false,
          error:
            err instanceof Error ? err.message : "Nie udało się rozpocząć sesji",
        });
      }
    },

    sendMessage: async (content: string) => {
      const { currentSession } = get();
      if (!currentSession) return;

      const userMessage: DirectorMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      set((state) => ({
        messages: [...state.messages, userMessage],
        isTyping: true,
        error: null,
      }));

      try {
        const res = await api.post<SendMessageApiResponse>(
          "/api/v1/spiritual-director/message",
          {
            session_id: currentSession.session_id,
            user_id: currentSession.user_id,
            content,
          }
        );

        const directorMessage: DirectorMessage = {
          id: crypto.randomUUID(),
          role: "director",
          content: res.director_response,
          timestamp: new Date(),
          scriptures: res.suggested_scriptures,
          followUps: res.follow_up_questions,
          prayerSuggestion: res.prayer_suggestion ?? undefined,
          spiritualState: res.spiritual_state ?? undefined,
        };

        set((state) => ({
          messages: [...state.messages, directorMessage],
          isTyping: false,
        }));
      } catch (err) {
        // Remove optimistically-added user message on failure
        set((state) => ({
          messages: state.messages.filter((m) => m.id !== userMessage.id),
          isTyping: false,
          error:
            err instanceof Error
              ? err.message
              : "Nie udało się wysłać wiadomości",
        }));
      }
    },

    loadTraditions: async () => {
      set({ isLoading: true, error: null });
      try {
        const traditions = await api.get<TraditionInfo[]>(
          "/api/v1/spiritual-director/traditions"
        );
        set({ traditions, isLoading: false });
      } catch (err) {
        set({
          isLoading: false,
          error:
            err instanceof Error
              ? err.message
              : "Nie udało się pobrać tradycji",
        });
      }
    },

    clearError: () => set({ error: null }),

    reset: () => set({ currentSession: null, messages: [], error: null }),
  })
);
