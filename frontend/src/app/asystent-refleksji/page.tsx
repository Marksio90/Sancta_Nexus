"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Send,
  ArrowLeft,
  AlertTriangle,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { useReflectionStore } from "@/stores/reflection";
import { VoiceRecorder } from "@/components/voice/VoiceRecorder";

/* ── Disclaimer text ─────────────────────────────────────────────────────── */
const DISCLAIMER =
  "Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy. Nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty.";

/* ── Component ───────────────────────────────────────────────────────────── */
export default function AsystentRefleksjiPage() {
  const router = useRouter();
  const { isAuthenticated, loadFromStorage } = useAuthStore();

  const {
    session,
    messages,
    isLoading,
    error,
    traditions,
    startSession,
    sendMessage,
    loadTraditions,
    reset,
  } = useReflectionStore();

  const [selectedTradition, setSelectedTradition] = useState("ignatian");
  const [input, setInput] = useState("");
  const [expandedMsg, setExpandedMsg] = useState<string | null>(null);
  const [sessionStarted, setSessionStarted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /* ── Auth check ─────────────────────────────────────────────────────── */
  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

  /* ── Load traditions ────────────────────────────────────────────────── */
  useEffect(() => {
    loadTraditions();
    return () => {
      reset();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Scroll to bottom ───────────────────────────────────────────────── */
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /* ── Start session ──────────────────────────────────────────────────── */
  const handleStartSession = useCallback(
    async (tradition: string) => {
      setSessionStarted(true);
      await startSession(tradition);
    },
    [startSession]
  );

  /* ── Tradition chip click ───────────────────────────────────────────── */
  const handleTraditionSelect = (id: string) => {
    setSelectedTradition(id);
    handleStartSession(id);
  };

  /* ── Send message ───────────────────────────────────────────────────── */
  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // Start session if not yet started
    if (!session && !sessionStarted) {
      await handleStartSession(selectedTradition);
      return;
    }

    const content = input.trim();
    setInput("");
    await sendMessage(content);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(e as unknown as React.FormEvent);
    }
  };

  const sessionReady = session !== null && messages.length > 0;
  const showTraditionSelector = !sessionStarted && messages.length === 0;

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col px-4 py-8">
      <div className="mx-auto w-full max-w-3xl flex-1 flex flex-col">

        {/* Back link */}
        <Link
          href="/"
          className="mb-6 inline-flex items-center gap-2 text-sm text-[--color-sacred-text-muted] transition-colors hover:text-[--color-gold]"
        >
          <ArrowLeft className="h-4 w-4" />
          Powrót
        </Link>

        {/* Header */}
        <div className="mb-6 text-center">
          <p className="mb-1 text-xs tracking-[0.4em] uppercase text-[--color-gold]/40">
            Contemplata et Meditata
          </p>
          <h1 className="font-heading mb-3 text-3xl text-[--color-gold]">
            Asystent refleksji
          </h1>
          <p className="text-sm text-[--color-sacred-text-muted]">
            Podziel się myślami po modlitwie lub Lectio Divina. Asystent pomoże
            Ci wrócić do Słowa Bożego.
          </p>
        </div>

        {/* Top disclaimer banner */}
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-600/20 bg-amber-900/10 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500/80" />
          <p className="text-sm leading-relaxed text-[--color-sacred-text-muted]">
            {DISCLAIMER}
          </p>
        </div>

        {/* Tradition selector — shown only before first message */}
        {showTraditionSelector && (
          <div className="mb-6">
            <p className="mb-3 text-sm font-medium text-[--color-sacred-text-muted]">
              Wybierz tradycję duchową:
            </p>
            <div className="flex flex-wrap gap-2">
              {traditions.map((t) => (
                <button
                  key={t.id}
                  onClick={() => handleTraditionSelect(t.id)}
                  className={`rounded-full border px-4 py-2 text-sm transition-all ${
                    selectedTradition === t.id
                      ? "border-[--color-gold]/50 bg-[--color-gold]/15 text-[--color-gold]"
                      : "border-[--color-sacred-border] bg-[--color-sacred-surface] text-[--color-sacred-text-muted] hover:border-[--color-gold]/25 hover:text-[--color-parchment]"
                  }`}
                >
                  {t.name}
                </button>
              ))}
            </div>
            {selectedTradition && traditions.find((t) => t.id === selectedTradition) && (
              <p className="mt-2 text-xs text-[--color-sacred-text-muted]/60">
                {traditions.find((t) => t.id === selectedTradition)?.description}
              </p>
            )}
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="mb-4 rounded-lg border border-red-800/30 bg-red-900/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Chat area */}
        <div className="flex flex-1 flex-col rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface] min-h-[480px]">

          {/* Messages */}
          <div className="flex-1 space-y-4 overflow-y-auto p-4 md:p-6">
            {messages.length === 0 && !isLoading && (
              <div className="py-16 text-center">
                <p className="font-scripture text-[--color-sacred-text-muted]/50">
                  {sessionStarted
                    ? "Łączenie z asystentem refleksji…"
                    : "Wybierz tradycję duchową i zacznij rozmowę."}
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
                  {msg.role === "assistant" && (
                    <p className="mb-1.5 text-xs font-semibold text-[--color-gold]">
                      Asystent refleksji ·{" "}
                      {traditions.find((t) => t.id === (session?.tradition ?? selectedTradition))?.name ?? ""}
                    </p>
                  )}

                  <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                  {/* Per-message disclaimer */}
                  {msg.role === "assistant" && msg.disclaimer && (
                    <p className="mt-2 text-xs italic text-[--color-sacred-text-muted]/50">
                      {msg.disclaimer}
                    </p>
                  )}

                  {/* Scriptures & follow-up questions */}
                  {msg.role === "assistant" &&
                    ((msg.suggested_scriptures?.length ?? 0) > 0 ||
                      (msg.follow_up_questions?.length ?? 0) > 0) && (
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
                            {msg.suggested_scriptures?.slice(0, 3).map((s, i) => (
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
                              </div>
                            ))}

                            {msg.follow_up_questions?.slice(0, 3).map((q, i) => (
                              <button
                                key={i}
                                onClick={() => setInput(q)}
                                className="block w-full rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-bg]/50 px-3 py-2 text-left text-xs italic text-[--color-sacred-text-muted]/70 transition-colors hover:border-[--color-gold]/30 hover:text-[--color-gold]/70"
                              >
                                → {q}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface-light] px-4 py-3">
                  <p className="text-xs font-semibold text-[--color-gold]">
                    Asystent refleksji
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
          <form
            onSubmit={handleSend}
            className="border-t border-[--color-sacred-border] p-4"
          >
            <div className="flex gap-3">
              <div className="relative flex-1">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    sessionReady
                      ? "Podziel się refleksją… (Enter = wyślij)"
                      : "Wybierz tradycję powyżej, aby rozpocząć…"
                  }
                  rows={2}
                  className="w-full resize-none rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-bg] px-4 py-3 pb-9 text-sm text-[--color-sacred-text] placeholder-[--color-sacred-text-muted]/40 transition-colors focus:border-[#d4af37]/50 focus:outline-none"
                  disabled={isLoading || (!sessionReady && !showTraditionSelector)}
                />
                <div className="absolute bottom-2 left-3">
                  <VoiceRecorder
                    onTranscript={(text) => setInput((prev) => prev ? `${prev} ${text}` : text)}
                    placeholder="Mów swoją refleksję…"
                    disabled={isLoading || (!sessionReady && !showTraditionSelector)}
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="self-end flex items-center gap-2 rounded-lg border border-[#d4af37]/40 bg-[#d4af37]/10 px-5 py-3 text-[#d4af37] transition-all hover:bg-[#d4af37]/20 disabled:cursor-not-allowed disabled:opacity-30"
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

        {/* Bottom disclaimer */}
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-[--color-sacred-border] bg-[--color-sacred-surface]/50 px-4 py-3">
          <Info className="h-4 w-4 shrink-0 text-[--color-sacred-text-muted]/50" />
          <p className="text-xs text-[--color-sacred-text-muted]/60 leading-relaxed">
            {DISCLAIMER}
          </p>
        </div>
      </div>
    </div>
  );
}
