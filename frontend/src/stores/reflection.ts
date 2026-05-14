import { create } from "zustand";
import { api } from "@/lib/api";

export interface TraditionInfo {
  id: string;
  name: string;
  description: string;
  key_practices?: string[];
}

export interface ReflectionSession {
  session_id: string;
  tradition: string;
  status: string;
  opening_message: string;
}

export interface ReflectionMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  disclaimer?: string;
  follow_up_questions?: string[];
  suggested_scriptures?: { reference: string; passage: string }[];
  spiritual_state?: string;
}

interface StartSessionApiResponse {
  session_id: string;
  tradition: string;
  status: string;
  opening_message: string;
}

interface SendMessageApiResponse {
  session_id: string;
  assistant_response: string;
  disclaimer?: string;
  follow_up_questions?: string[];
  suggested_scriptures?: { reference: string; passage: string }[];
  spiritual_state?: string;
}

interface ReflectionStore {
  session: ReflectionSession | null;
  messages: ReflectionMessage[];
  isLoading: boolean;
  error: string | null;
  traditions: TraditionInfo[];

  startSession: (tradition: string, initialIntention?: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  loadTraditions: () => Promise<void>;
  reset: () => void;
}

const DEFAULT_TRADITIONS: TraditionInfo[] = [
  {
    id: "ignatian",
    name: "Ignacjańska",
    description: "Rozeznawanie duchowe, Ćwiczenia Duchowe św. Ignacego",
  },
  {
    id: "carmelite",
    name: "Karmelitańska",
    description: "Modlitwa kontemplacyjna, św. Teresa z Ávili, św. Jan od Krzyża",
  },
  {
    id: "benedictine",
    name: "Benedyktyńska",
    description: "Ora et labora, Reguła św. Benedykta, Liturgia Godzin",
  },
  {
    id: "franciscan",
    name: "Franciszkańska",
    description: "Ubóstwo duchowe, radość, bliskość ze stworzeniem",
  },
  {
    id: "dominican",
    name: "Dominikańska",
    description: "Contemplata aliis tradere — kontemplacja przekazywana innym",
  },
];

export const useReflectionStore = create<ReflectionStore>((set, get) => ({
  session: null,
  messages: [],
  isLoading: false,
  error: null,
  traditions: DEFAULT_TRADITIONS,

  startSession: async (tradition: string, initialIntention?: string) => {
    set({ isLoading: true, error: null, messages: [], session: null });
    try {
      const body: Record<string, string> = { tradition };
      if (initialIntention) body.initial_intention = initialIntention;

      const res = await api.post<StartSessionApiResponse>(
        "/api/v1/reflection-assistant/session",
        body
      );

      const session: ReflectionSession = {
        session_id: res.session_id,
        tradition: res.tradition,
        status: res.status,
        opening_message: res.opening_message,
      };

      const openingMessage: ReflectionMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.opening_message,
        timestamp: new Date(),
      };

      set({ session, messages: [openingMessage], isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error:
          err instanceof Error
            ? err.message
            : "Nie udało się rozpocząć sesji refleksji",
      });
    }
  },

  sendMessage: async (content: string) => {
    const { session } = get();
    if (!session) return;

    const userMessage: ReflectionMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      const res = await api.post<SendMessageApiResponse>(
        "/api/v1/reflection-assistant/message",
        {
          session_id: session.session_id,
          content,
        }
      );

      const assistantMessage: ReflectionMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.assistant_response,
        timestamp: new Date(),
        disclaimer: res.disclaimer,
        follow_up_questions: res.follow_up_questions,
        suggested_scriptures: res.suggested_scriptures,
        spiritual_state: res.spiritual_state,
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isLoading: false,
      }));
    } catch (err) {
      set((state) => ({
        messages: state.messages.filter((m) => m.id !== userMessage.id),
        isLoading: false,
        error:
          err instanceof Error
            ? err.message
            : "Nie udało się wysłać wiadomości",
      }));
    }
  },

  loadTraditions: async () => {
    try {
      const traditions = await api.get<TraditionInfo[]>(
        "/api/v1/reflection-assistant/traditions"
      );
      if (traditions && traditions.length > 0) {
        set({ traditions });
      }
    } catch {
      // Keep default traditions on error
    }
  },

  reset: () =>
    set({ session: null, messages: [], error: null, isLoading: false }),
}));
