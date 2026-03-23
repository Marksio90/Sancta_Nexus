"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, ArrowLeft, AlertTriangle, BookOpen, ChevronDown, ChevronUp } from "lucide-react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

/* ── Tradition mapping ────────────────────────────────────────────────── */
const TRADITIONS = [
  {
    id: "ignatian",
    label: "Ignacjańska",
    description: "Rozeznawanie duchowe, Ćwiczenia Duchowe św. Ignacego",
  },
  {
    id: "carmelite",
    label: "Karmelitańska",
    description: "Modlitwa kontemplacyjna, św. Teresa z Ávili, św. Jan od Krzyża",
  },
  {
    id: "benedictine",
    label: "Benedyktyńska",
    description: "Ora et labora, Reguła św. Benedykta, Liturgia Godzin",
  },
  {
    id: "franciscan",
    label: "Franciszkańska",
    description: "Ubóstwo duchowe, radość, bliskość ze stworzeniem",
  },
  {
    id: "dominican",
    label: "Dominikańska",
    description: "Contemplata aliis tradere — kontemplacja przekazywana innym",
  },
];

/* ── Types ────────────────────────────────────────────────────────────── */
interface Message {
  id: string;
  role: "user" | "director";
  content: string;
  timestamp: Date;
  scriptures?: { reference: string; passage: string; explanation: string }[];
  followUps?: string[];
  prayerSuggestion?: string;
  spiritualState?: string;
}

interface StartSessionResponse {
  session_id: string;
  opening_message: string;
}

interface MessageApiResponse {
  director_response: string;
  suggested_scriptures: { reference: string; passage: string; explanation: string }[];
  follow_up_questions: string[];
  prayer_suggestion?: string;
  spiritual_state?: string;
}

/* ── Anonymous user ID (persistent across sessions) ────────────────────── */
function getAnonId(): string {
  if (typeof window === "undefined") return "anon";
  let id = localStorage.getItem("sancta_nexus_anon_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("sancta_nexus_anon_id", id);
  }
  return id;
}

/* ── Component ────────────────────────────────────────────────────────── */
export default function SpiritualDirectorPage() {
  const [selectedTradition, setSelectedTradition] = useState("ignatian");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedMsg, setExpandedMsg] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const userId = useRef(getAnonId());

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /* ── Start new session when tradition changes ──────────────────────── */
  const startSession = useCallback(
    async (tradition: string) => {
      setMessages([]);
      setSessionId(null);
      setError(null);
      setIsTyping(true);
      try {
        const res = await api.post<StartSessionResponse>(
          "/api/v1/spiritual-director/session",
          { user_id: userId.current, tradition }
        );
        setSessionId(res.session_id);
        setMessages([
          {
            id: crypto.randomUUID(),
            role: "director",
            content: res.opening_message,
            timestamp: new Date(),
          },
        ]);
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? "Nie można połączyć się z kierownikiem duchowym. Spróbuj ponownie."
            : "Wystąpił błąd. Sprawdź połączenie.";
        setError(msg);
      } finally {
        setIsTyping(false);
      }
    },
    []
  );

  /* ── Auto-start on mount ───────────────────────────────────────────── */
  useEffect(() => {
    startSession(selectedTradition);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Tradition change ──────────────────────────────────────────────── */
  const handleTraditionChange = (id: string) => {
    setSelectedTradition(id);
    startSession(id);
  };

  /* ── Send message ──────────────────────────────────────────────────── */
  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping || !sessionId) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);
    setError(null);

    try {
      const res = await api.post<MessageApiResponse>(
        "/api/v1/spiritual-director/message",
        { session_id: sessionId, user_id: userId.current, content: userMsg.content }
      );

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "director",
          content: res.director_response,
          timestamp: new Date(),
          scriptures: res.suggested_scriptures,
          followUps: res.follow_up_questions,
          prayerSuggestion: res.prayer_suggestion ?? undefined,
          spiritualState: res.spiritual_state ?? undefined,
        },
      ]);
    } catch {
      setError("Nie udało się wysłać wiadomości. Spróbuj ponownie.");
      setMessages((prev) => prev.slice(0, -1)); // remove user message on error
      setInput(userMsg.content);
    } finally {
      setIsTyping(false);
    }
  };

  /* ── Keyboard shortcut: Enter to send ─────────────────────────────── */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(e as unknown as React.FormEvent);
    }
  };

  return (
    <div className="flex min-h-screen flex-col px-4 py-8">
      <div className="mx-auto w-full max-w-3xl flex-1">
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-2 text-sm text-[--color-sacred-text-muted] transition-colors hover:text-[--color-gold]"
        >
          <ArrowLeft className="h-4 w-4" />
          Powrót
        </Link>

        <div className="mb-6 text-center">
          <p className="mb-1 text-xs tracking-[0.4em] uppercase text-[--color-gold]/40">
            Towarzyszenie duchowe
          </p>
          <h1 className="font-heading mb-3 text-3xl text-[--color-gold]">
            Kierownik Duchowy AI
          </h1>
          <p className="text-sm text-[--color-sacred-text-muted]">
            Rozmowa w duchu wybranej tradycji — prowadzona przez AI, zakorzeniona w Piśmie
          </p>
        </div>

        {/* Disclaimer */}
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-[--color-sacred-red]/20 bg-[--color-sacred-red]/5 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[--color-sacred-red-light]" />
          <p className="text-sm leading-relaxed text-[--color-sacred-text-muted]">
            <strong className="text-[--color-parchment]">Uwaga:</strong> AI nie zastępuje
            ludzkiego kierownika duchowego. W poważnych kwestiach zwróć się do kapłana.
          </p>
        </div>

        {/* Tradition selector */}
        <div className="mb-6 grid grid-cols-2 gap-2 md:grid-cols-5">
          {TRADITIONS.map((t) => (
            <button
              key={t.id}
              onClick={() => handleTraditionChange(t.id)}
              className={`rounded-lg border p-3 text-left transition-all ${
                selectedTradition === t.id
                  ? "border-[--color-gold]/40 bg-[--color-gold]/10 text-[--color-gold]"
                  : "border-[--color-sacred-border] bg-[--color-sacred-surface] text-[--color-sacred-text-muted] hover:border-[--color-gold]/20"
              }`}
            >
              <p className="text-sm font-semibold">{t.label}</p>
              <p className="mt-1 hidden text-[10px] leading-tight opacity-60 md:block">
                {t.description}
              </p>
            </button>
          ))}
        </div>

        {/* Error banner */}
        {error && (
          <div className="mb-4 rounded-lg border border-[--color-sacred-red]/30 bg-[--color-sacred-red]/10 px-4 py-3 text-sm text-[--color-sacred-red-light]">
            {error}
          </div>
        )}

        {/* Chat area */}
        <div className="flex min-h-[480px] flex-col rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface]">
          {/* Messages */}
          <div className="flex-1 space-y-4 overflow-y-auto p-4 md:p-6">
            {messages.length === 0 && !isTyping && (
              <div className="py-16 text-center">
                <p className="font-scripture text-[--color-sacred-text-muted]/50">
                  Łączenie z kierownikiem duchowym…
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[82%] rounded-xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-[--color-gold]/10 text-[--color-parchment]"
                      : "border border-[--color-sacred-border] bg-[--color-sacred-surface-light] text-[--color-sacred-text]"
                  }`}
                >
                  {msg.role === "director" && (
                    <p className="mb-1.5 text-xs font-semibold text-[--color-gold]">
                      Kierownik Duchowy ·{" "}
                      {TRADITIONS.find((t) => t.id === selectedTradition)?.label}
                    </p>
                  )}
                  <p className="leading-relaxed">{msg.content}</p>

                  {/* Suggested scriptures + follow-ups */}
                  {msg.role === "director" &&
                    (msg.scriptures?.length || msg.followUps?.length || msg.prayerSuggestion) && (
                      <div className="mt-3 border-t border-[--color-sacred-border] pt-3">
                        <button
                          onClick={() =>
                            setExpandedMsg(expandedMsg === msg.id ? null : msg.id)
                          }
                          className="flex items-center gap-1.5 text-xs text-[--color-gold]/60 transition-colors hover:text-[--color-gold]"
                        >
                          <BookOpen className="h-3.5 w-3.5" />
                          Pismo i pytania do refleksji
                          {expandedMsg === msg.id ? (
                            <ChevronUp className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5" />
                          )}
                        </button>

                        {expandedMsg === msg.id && (
                          <div className="mt-3 animate-fade-in space-y-3">
                            {msg.scriptures?.slice(0, 2).map((s, i) => (
                              <div
                                key={i}
                                className="rounded-lg border border-[--color-gold]/15 bg-[--color-sacred-bg] p-3"
                              >
                                <p className="text-xs font-semibold text-[--color-gold]/70">
                                  {s.reference}
                                </p>
                                <p className="font-scripture mt-1 text-sm italic text-[--color-parchment]/80">
                                  {s.passage}
                                </p>
                                {s.explanation && (
                                  <p className="mt-1 text-xs text-[--color-sacred-text-muted]/60">
                                    {s.explanation}
                                  </p>
                                )}
                              </div>
                            ))}

                            {msg.followUps?.slice(0, 2).map((q, i) => (
                              <p
                                key={i}
                                className="cursor-pointer text-xs italic text-[--color-sacred-text-muted]/60 transition-colors hover:text-[--color-gold]/60"
                                onClick={() => setInput(q)}
                              >
                                → {q}
                              </p>
                            ))}

                            {msg.prayerSuggestion && (
                              <p className="rounded bg-[--color-gold]/5 px-3 py-2 text-xs text-[--color-gold]/70">
                                🕯 {msg.prayerSuggestion}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface-light] px-4 py-3">
                  <p className="text-xs font-semibold text-[--color-gold]">
                    Kierownik Duchowy
                  </p>
                  <div className="mt-2 flex gap-1">
                    <span className="animate-sacred-pulse h-2 w-2 rounded-full bg-[--color-gold]/50" />
                    <span className="animate-sacred-pulse h-2 w-2 rounded-full bg-[--color-gold]/50 [animation-delay:0.5s]" />
                    <span className="animate-sacred-pulse h-2 w-2 rounded-full bg-[--color-gold]/50 [animation-delay:1s]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSend} className="border-t border-[--color-sacred-border] p-4">
            <div className="flex gap-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Napisz swoją myśl lub pytanie… (Enter = wyślij)"
                rows={2}
                className="flex-1 resize-none rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-bg] px-4 py-3 text-sm text-[--color-sacred-text] placeholder-[--color-sacred-text-muted]/40 transition-colors focus:border-[--color-gold]/50 focus:outline-none"
                disabled={isTyping || !sessionId}
              />
              <button
                type="submit"
                disabled={!input.trim() || isTyping || !sessionId}
                className="self-end flex items-center gap-2 rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-5 py-3 text-[--color-gold] transition-all hover:bg-[--color-gold]/20 disabled:cursor-not-allowed disabled:opacity-30"
              >
                <Send className="h-4 w-4" />
                <span className="hidden sm:inline">Wyślij</span>
              </button>
            </div>
            <p className="mt-2 text-right text-xs text-[--color-sacred-text-muted]/30">
              Shift+Enter = nowa linia
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
