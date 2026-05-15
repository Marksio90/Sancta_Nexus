"use client";

import { useState, useRef, useEffect } from "react";

interface AudioPlayerProps {
  src: string;
  title?: string;
  autoPlay?: boolean;
  onEnded?: () => void;
}

export function AudioPlayer({ src, title, autoPlay = false, onEnded }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    const audio = new Audio(src);
    audioRef.current = audio;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setPlaying(false);
    setProgress(0);
    setError(false);

    audio.addEventListener("loadedmetadata", () => {
      setDuration(audio.duration);
      setLoading(false);
      if (autoPlay) audio.play().catch(() => {});
    });
    audio.addEventListener("timeupdate", () => {
      if (audio.duration > 0) setProgress(audio.currentTime / audio.duration);
    });
    audio.addEventListener("ended", () => {
      setPlaying(false);
      setProgress(1);
      onEnded?.();
    });
    audio.addEventListener("error", () => {
      setError(true);
      setLoading(false);
    });
    audio.addEventListener("play", () => setPlaying(true));
    audio.addEventListener("pause", () => setPlaying(false));

    return () => {
      audio.pause();
      audio.src = "";
    };
  }, [src, autoPlay, onEnded]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) { audio.pause(); } else { audio.play().catch(() => {}); }
  };

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    audio.currentTime = ratio * duration;
  };

  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  if (error) {
    return (
      <div className="rounded-xl bg-red-900/20 border border-red-700/30 p-3 text-xs text-red-400">
        Nie można załadować audio. Sprawdź połączenie.
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
      {title && (
        <div className="text-xs text-[#d4af37] mb-3 font-medium">🎵 {title}</div>
      )}
      <div className="flex items-center gap-3">
        {/* Play/Pause button */}
        <button
          onClick={togglePlay}
          disabled={loading}
          className="w-10 h-10 rounded-full bg-[#d4af37] text-black flex items-center justify-center flex-shrink-0 hover:bg-[#c9a227] transition-colors disabled:opacity-50"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
          ) : playing ? (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" />
            </svg>
          ) : (
            <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <polygon points="5,3 19,12 5,21" />
            </svg>
          )}
        </button>

        {/* Progress bar + time */}
        <div className="flex-1">
          <div
            className="h-1.5 bg-white/10 rounded-full cursor-pointer mb-1.5 relative"
            onClick={seek}
          >
            <div
              className="h-full bg-[#d4af37] rounded-full transition-all"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-gray-500">
            <span>{duration > 0 ? fmt(progress * duration) : "0:00"}</span>
            <span>{duration > 0 ? fmt(duration) : "—"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}


interface PremiumAudioButtonProps {
  mysteryType: string;
  mysteryNumber: number;
  isPremium: boolean;
}

/**
 * Przycisk do ładowania audio medytacji różańcowej.
 * Pobiera MP3 z backendu i pokazuje AudioPlayer.
 */
export function PremiumAudioButton({ mysteryType, mysteryNumber, isPremium }: PremiumAudioButtonProps) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAudio = async () => {
    if (!isPremium) return;
    setFetching(true);
    setError(null);

    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

    try {
      const res = await fetch("/api/v1/voice/meditate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          mystery_type: mysteryType,
          mystery_number: mysteryNumber,
          profile: "contemplative",
          speed: 0.85,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail ?? "Błąd pobierania audio.");
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (e: unknown) {
      setError((e as Error).message ?? "Błąd.");
    } finally {
      setFetching(false);
    }
  };

  if (!isPremium) {
    return (
      <div className="text-xs text-gray-600 flex items-center gap-2">
        <span>🔒</span>
        <span>Audio medytacje — <a href="/cennik" className="text-[#d4af37] hover:underline">plan Premium</a></span>
      </div>
    );
  }

  if (audioUrl) {
    return (
      <AudioPlayer
        src={audioUrl}
        title="Medytacja do tajemnicy"
        autoPlay
      />
    );
  }

  return (
    <div>
      <button
        onClick={loadAudio}
        disabled={fetching}
        className="w-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-[#d4af37]/30 rounded-xl py-3 text-sm text-gray-300 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {fetching ? (
          <>
            <div className="w-4 h-4 border-2 border-gray-500 border-t-[#d4af37] rounded-full animate-spin" />
            <span>Generuję medytację…</span>
          </>
        ) : (
          <>
            <span>🎵</span>
            <span>Słuchaj medytacji (AI)</span>
          </>
        )}
      </button>
      {error && <p className="text-xs text-red-400 mt-2 text-center">{error}</p>}
    </div>
  );
}
