"use client";

/**
 * VoiceRecorder — Speech-to-Text for prayer input.
 *
 * Strategy (waterfall):
 *   1. Web Speech API (browser-native, no backend call, no latency)
 *   2. MediaRecorder → POST /api/v1/voice/stt  (Whisper, for Firefox/mobile)
 *
 * Props
 * -----
 * onTranscript  - Called with the final transcription string
 * placeholder   - Helper text shown when idle
 * disabled      - Disable the mic button
 * language      - BCP-47 language tag (default: "pl-PL")
 * className     - Extra CSS classes on root element
 */

import { useRef, useState, useCallback, useEffect } from "react";
import { Mic, MicOff, Loader2 } from "lucide-react";


interface VoiceRecorderProps {
  onTranscript: (text: string) => void;
  placeholder?: string;
  disabled?: boolean;
  language?: string;
  className?: string;
}

type RecorderState = "idle" | "recording" | "processing" | "error";

// ── Web Speech API type augmentation ─────────────────────────────────────────
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}
interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}
interface SpeechRecognitionInstance extends EventTarget {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}

function getSpeechRecognition(): (new () => SpeechRecognitionInstance) | null {
  if (typeof window === "undefined") return null;
  return (
    (window as unknown as { SpeechRecognition?: new () => SpeechRecognitionInstance }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognitionInstance }).webkitSpeechRecognition ??
    null
  );
}

export function VoiceRecorder({
  onTranscript,
  placeholder = "Mów swoją modlitwę…",
  disabled = false,
  language = "pl-PL",
  className = "",
}: VoiceRecorderProps) {
  const [recState, setRecState] = useState<RecorderState>("idle");
  const [interim, setInterim] = useState(""); // live interim text
  const [available, setAvailable] = useState(true);

  const srRef = useRef<SpeechRecognitionInstance | null>(null);
  const mediaRecRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Check availability on mount
  useEffect(() => {
    const hasSR = !!getSpeechRecognition();
    const hasMR = typeof window !== "undefined" && !!window.MediaRecorder;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!hasSR && !hasMR) setAvailable(false);
  }, []);

  // ── Web Speech API path ───────────────────────────────────────────────────

  const startWebSpeech = useCallback(() => {
    const SR = getSpeechRecognition();
    if (!SR) return false;

    const sr = new SR();
    sr.lang = language;
    sr.interimResults = true;
    sr.maxAlternatives = 1;

    sr.onresult = (e: SpeechRecognitionEvent) => {
      // Accumulate all final results (iterate forward to preserve order)
      let finalText = "";
      let interimText = "";
      for (let i = 0; i < e.results.length; i++) {
        const result = e.results[i];
        if (result.isFinal) {
          finalText += result[0].transcript;
        } else {
          interimText = result[0].transcript;
        }
      }
      setInterim(interimText);
      if (finalText) {
        onTranscript(finalText.trim());
        setInterim("");
        setRecState("idle");
      }
    };

    sr.onerror = () => {
      setRecState("error");
      setInterim("");
      setTimeout(() => setRecState("idle"), 2000);
    };

    // Unconditionally reset — captures stale recState otherwise (closure bug)
    sr.onend = () => {
      setRecState("idle");
      setInterim("");
    };

    srRef.current = sr;
    sr.start();
    setRecState("recording");
    return true;
  }, [language, onTranscript]);

  // ── MediaRecorder + Whisper path ──────────────────────────────────────────

  const startMediaRecorder = useCallback(async () => {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setAvailable(false);
      return;
    }

    chunksRef.current = [];
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/ogg;codecs=opus";

    const mr = new MediaRecorder(stream, { mimeType });
    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    mr.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      setRecState("processing");

      const blob = new Blob(chunksRef.current, { type: mimeType });
      const formData = new FormData();
      formData.append("file", blob, "recording.webm");
      formData.append("language", language.split("-")[0]);

      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
        const res = await fetch("/api/v1/voice/stt", {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
        if (res.ok) {
          const data = await res.json();
          onTranscript(data.text);
        } else {
          setRecState("error");
          setTimeout(() => setRecState("idle"), 2000);
          return;
        }
      } catch {
        setRecState("error");
        setTimeout(() => setRecState("idle"), 2000);
        return;
      }

      setRecState("idle");
    };

    mediaRecRef.current = mr;
    mr.start();
    setRecState("recording");
  }, [language, onTranscript]);

  // ── Start / stop dispatcher ───────────────────────────────────────────────

  const toggle = useCallback(async () => {
    if (recState === "recording") {
      // Stop whatever is recording
      srRef.current?.stop();
      mediaRecRef.current?.stop();
      return;
    }
    if (recState !== "idle") return;

    // Try Web Speech first, fall back to MediaRecorder
    const usedSR = startWebSpeech();
    if (!usedSR) await startMediaRecorder();
  }, [recState, startWebSpeech, startMediaRecorder]);

  if (!available) return null;

  const isRecording = recState === "recording";
  const isProcessing = recState === "processing";
  const isError = recState === "error";

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <button
        type="button"
        onClick={toggle}
        disabled={disabled || isProcessing}
        title={isRecording ? "Zatrzymaj nagrywanie" : placeholder}
        aria-label={isRecording ? "Zatrzymaj nagrywanie modlitwy" : "Nagraj modlitwę głosem"}
        className={`flex h-9 w-9 items-center justify-center rounded-full border transition-all ${
          isRecording
            ? "animate-pulse border-[#ef4444]/60 bg-[#ef4444]/15 text-[#fca5a5]"
            : isError
            ? "border-[#ef4444]/30 bg-transparent text-[#fca5a5]/50"
            : "border-[#d4af37]/30 bg-[#0d0b1a] text-[#d4af37]/60 hover:border-[#d4af37]/60 hover:text-[#d4af37]"
        } disabled:cursor-wait disabled:opacity-40`}
      >
        {isProcessing ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : isRecording ? (
          <MicOff className="h-4 w-4" />
        ) : (
          <Mic className="h-4 w-4" />
        )}
      </button>

      {/* Live interim transcript */}
      {interim && (
        <span className="text-xs italic text-gray-500/60 animate-fade-in">
          {interim}
        </span>
      )}

      {isError && (
        <span className="text-xs text-[#fca5a5]/60">
          Nie udało się rozpoznać mowy
        </span>
      )}
    </div>
  );
}
