import { create } from "zustand";
import { api } from "@/lib/api";
import type { ChatMessage, SpiritualTradition } from "@/types";

interface DirectorSession {
  id: string;
  tradition: SpiritualTradition;
  createdAt: string;
  messageCount: number;
}

interface TraditionInfo {
  id: SpiritualTradition;
  name: string;
  description: string;
}

interface DirectorState {
  sessions: DirectorSession[];
  currentSession: DirectorSession | null;
  messages: ChatMessage[];
  isTyping: boolean;
  isLoading: boolean;
  traditions: TraditionInfo[];
  error: string | null;
}

interface DirectorActions {
  startSession: (tradition: SpiritualTradition) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  loadTraditions: () => Promise<void>;
  loadSessions: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  clearError: () => void;
}

interface SendMessageResponse {
  message: ChatMessage;
  reply: ChatMessage;
}

export const useDirectorStore = create<DirectorState & DirectorActions>(
  (set, get) => ({
    sessions: [],
    currentSession: null,
    messages: [],
    isTyping: false,
    isLoading: false,
    traditions: [],
    error: null,

    startSession: async (tradition: SpiritualTradition) => {
      set({ isLoading: true, error: null });
      try {
        const session = await api.post<DirectorSession>(
          "/api/v1/spiritual-director/sessions",
          { tradition }
        );
        set({
          currentSession: session,
          messages: [],
          isLoading: false,
        });
      } catch (err) {
        set({
          isLoading: false,
          error:
            err instanceof Error ? err.message : "Nie udało się rozpocząć sesji",
        });
      }
    },

    sendMessage: async (content: string) => {
      const session = get().currentSession;
      if (!session) return;

      const userMessage: ChatMessage = {
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
        const data = await api.post<SendMessageResponse>(
          `/api/v1/spiritual-director/sessions/${session.id}/messages`,
          { content }
        );

        set((state) => ({
          messages: [
            ...state.messages.filter((m) => m.id !== userMessage.id),
            data.message,
            data.reply,
          ],
          isTyping: false,
        }));
      } catch (err) {
        set({
          isTyping: false,
          error:
            err instanceof Error
              ? err.message
              : "Nie udało się wysłać wiadomości",
        });
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

    loadSessions: async () => {
      set({ isLoading: true, error: null });
      try {
        const sessions = await api.get<DirectorSession[]>(
          "/api/v1/spiritual-director/sessions"
        );
        set({ sessions, isLoading: false });
      } catch (err) {
        set({
          isLoading: false,
          error:
            err instanceof Error ? err.message : "Nie udało się pobrać sesji",
        });
      }
    },

    loadSession: async (sessionId: string) => {
      set({ isLoading: true, error: null });
      try {
        const [session, messages] = await Promise.all([
          api.get<DirectorSession>(
            `/api/v1/spiritual-director/sessions/${sessionId}`
          ),
          api.get<ChatMessage[]>(
            `/api/v1/spiritual-director/sessions/${sessionId}/messages`
          ),
        ]);
        set({ currentSession: session, messages, isLoading: false });
      } catch (err) {
        set({
          isLoading: false,
          error:
            err instanceof Error ? err.message : "Nie udało się załadować sesji",
        });
      }
    },

    clearError: () => set({ error: null }),
  })
);
