"use client";

/**
 * VoicePlayer — sacred Text-to-Speech player.
 *
 * Fetches MP3 audio from POST /api/v1/voice/tts and plays it via HTMLAudioElement.
 * Falls back gracefully (hides itself) when the TTS endpoint is unreachable.
 *
 * Props
 * -----
 * text         - Text to synthesise (max 4096 chars)
 * profile      - Voice profile: narrator_male | narrator_female | contemplative | sacred
 * label        - Accessible label / tooltip shown on the play button
 * autoPlay     - Start playing immediately when mounted (default: false)
 * speed        - Playback speed for generation 0.25-1.5 (default: 0.9)
 * className    - Extra CSS classes on the root element
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { Play, Pause, Square, Volume2, Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type VoiceProfileId =
  | "narrator_male"
  | "narrator_female"
  | "contemplative"
  | "sacred";

interface VoicePlayerProps {
  text: string;
  profile?: VoiceProfileId;
  label?: string;
  autoPlay?: boolean;
  speed?: number;
  className?: string;
}

type PlayerState = "idle" | "loading" | "playing" | "paused" | "error";

export function VoicePlayer({
  text,
  profile = "narrator_male",
  label = "Odsłuchaj",
  autoPlay = false,
  speed = 0.9,
  className = "",
}: VoicePlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const [state, setState] = useState<PlayerState>("idle");
  const [progress, setProgress] = useState(0); // 0–100
  const [available, setAvailable] = useState(true);

  // Clean up blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
      audioRef.current?.pause();
    };
  }, []);

  const fetchAudio = useCallback(async (): Promise<string | null> => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/voice/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, profile, speed }),
      });
      if (!res.ok) {
        if (res.status === 503) setAvailable(false);
        return null;
      }
      const blob = await res.blob();
      return URL.createObjectURL(blob);
    } catch {
      setAvailable(false);
      return null;
    }
  }, [text, profile, speed]);

  const play = useCallback(async () => {
    // Resume if already loaded and paused
    if (audioRef.current && state === "paused") {
      audioRef.current.play();
      setState("playing");
      return;
    }

    setState("loading");
    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);

    const url = await fetchAudio();
    if (!url) {
      setState("error");
      return;
    }

    blobUrlRef.current = url;
    const audio = new Audio(url);
    audioRef.current = audio;

    audio.addEventListener("timeupdate", () => {
      if (audio.duration) {
        setProgress((audio.currentTime / audio.duration) * 100);
      }
    });
    audio.addEventListener("ended", () => {
      setState("idle");
      setProgress(0);
    });
    audio.addEventListener("error", () => setState("error"));

    audio.play();
    setState("playing");
  }, [state, fetchAudio]);

  const pause = useCallback(() => {
    audioRef.current?.pause();
    setState("paused");
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setState("idle");
    setProgress(0);
  }, []);

  useEffect(() => {
    if (autoPlay) play();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Hide gracefully when unavailable
  if (!available) return null;

  const isLoading = state === "loading";
  const isPlaying = state === "playing";
  const isPaused = state === "paused";

  return (
    <div
      className={`flex items-center gap-2 ${className}`}
      role="group"
      aria-label={`Odtwarzacz głosowy: ${label}`}
    >
      {/* Play / Pause button */}
      <button
        onClick={isPlaying ? pause : play}
        disabled={isLoading}
        title={isPlaying ? "Wstrzymaj" : label}
        aria-label={isPlaying ? "Wstrzymaj odtwarzanie" : label}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-[--color-gold]/30 bg-[--color-sacred-surface] text-[--color-gold] transition-all hover:border-[--color-gold]/60 hover:bg-[--color-gold]/10 disabled:cursor-wait disabled:opacity-50"
      >
        {isLoading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : isPlaying ? (
          <Pause className="h-3.5 w-3.5" />
        ) : (
          <Volume2 className="h-3.5 w-3.5" />
        )}
      </button>

      {/* Progress bar — only visible while loading/playing/paused */}
      {(isLoading || isPlaying || isPaused) && (
        <>
          <div
            className="relative h-1 flex-1 overflow-hidden rounded-full bg-[--color-sacred-border]"
            role="progressbar"
            aria-valuenow={Math.round(progress)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-[--color-gold]/60 transition-all duration-100"
              style={{ width: `${isLoading ? 0 : progress}%` }}
            />
          </div>

          {/* Stop button */}
          <button
            onClick={stop}
            title="Zatrzymaj"
            aria-label="Zatrzymaj odtwarzanie"
            className="flex h-6 w-6 items-center justify-center rounded text-[--color-sacred-text-muted] transition-colors hover:text-[--color-gold]"
          >
            <Square className="h-3 w-3" />
          </button>
        </>
      )}

      {/* Idle play label */}
      {state === "idle" && (
        <button
          onClick={play}
          className="text-xs text-[--color-sacred-text-muted]/60 transition-colors hover:text-[--color-gold]/70"
        >
          {label}
        </button>
      )}

      {state === "error" && (
        <span className="text-xs text-[--color-sacred-red-light]/60">
          Głos niedostępny
        </span>
      )}
    </div>
  );
}
