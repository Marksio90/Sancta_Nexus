"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { playPrayerBell, playSilenceBell, playTick } from "@/lib/audio";
import { Bell, BellOff } from "lucide-react";

interface BreathingTimerProps {
  durationMinutes?: number;
  sacredWord?: string;
  sacredWordMeaning?: string;
  jesusPrayerRhythm?: string;
  closingPrayer?: string;
}

type BreathPhase = "inhale" | "hold" | "exhale";

const PHASE_DURATION_MS = {
  inhale: 4000,
  hold: 2000,
  exhale: 4000,
} as const;

const PHASE_LABELS: Record<BreathPhase, string> = {
  inhale: "Wdech...",
  hold: "Zatrzymaj...",
  exhale: "Wydech...",
};

const PHASE_LATIN: Record<BreathPhase, string> = {
  inhale: "Inspira",
  hold: "Tene",
  exhale: "Expira",
};

export function BreathingTimer({
  durationMinutes = 3,
  sacredWord,
  sacredWordMeaning,
  jesusPrayerRhythm,
  closingPrayer,
}: BreathingTimerProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [phase, setPhase] = useState<BreathPhase>("inhale");
  const [timeRemaining, setTimeRemaining] = useState(durationMinutes * 60);
  const [isComplete, setIsComplete] = useState(false);
  const [showJesusPrayer, setShowJesusPrayer] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const phaseTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevPhaseRef = useRef<BreathPhase | null>(null);

  const totalSeconds = durationMinutes * 60;

  const cyclePhase = useCallback(() => {
    setPhase((current) => {
      const next: Record<BreathPhase, BreathPhase> = {
        inhale: "hold",
        hold: "exhale",
        exhale: "inhale",
      };
      return next[current];
    });
  }, []);

  useEffect(() => {
    if (!isRunning || isComplete) return;
    // Play tick when phase changes
    if (soundEnabled && prevPhaseRef.current !== phase) {
      playTick();
      prevPhaseRef.current = phase;
    }
    phaseTimeoutRef.current = setTimeout(cyclePhase, PHASE_DURATION_MS[phase]);
    return () => {
      if (phaseTimeoutRef.current) clearTimeout(phaseTimeoutRef.current);
    };
  }, [isRunning, isComplete, phase, cyclePhase, soundEnabled]);

  useEffect(() => {
    if (!isRunning || isComplete) return;
    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          setIsComplete(true);
          setIsRunning(false);
          if (soundEnabled) playSilenceBell();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [isRunning, isComplete]);

  const handleStart = () => {
    if (soundEnabled) playPrayerBell();
    prevPhaseRef.current = null;
    setIsRunning(true);
    setPhase("inhale");
    setTimeRemaining(totalSeconds);
    setIsComplete(false);
  };

  const handleReset = () => {
    setIsRunning(false);
    setPhase("inhale");
    setTimeRemaining(totalSeconds);
    setIsComplete(false);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const circleScale =
    phase === "inhale" ? "scale-110" : phase === "exhale" ? "scale-90" : "scale-100";

  return (
    <div className="flex flex-col items-center">
      {/* Sacred word display */}
      {sacredWord && isRunning && !isComplete && (
        <div className="mb-8 text-center">
          <p className="animate-word-pulse font-heading text-2xl tracking-[0.2em] text-[--color-gold]">
            {sacredWord}
          </p>
          {sacredWordMeaning && (
            <p className="mt-1 text-xs text-[--color-sacred-text-muted]/50">
              {sacredWordMeaning}
            </p>
          )}
        </div>
      )}

      {/* Breathing circle */}
      <div className="relative flex h-64 w-64 items-center justify-center">
        {/* Outer sacred geometry ring */}
        <div
          className={`absolute inset-0 rounded-full border border-[--color-gold]/10 transition-all duration-[4000ms] ease-in-out ${
            isRunning ? circleScale : ""
          }`}
        />

        {/* Middle ring */}
        <div
          className={`absolute inset-4 rounded-full border border-[--color-gold]/15 transition-all duration-[4000ms] ease-in-out ${
            isRunning ? circleScale : ""
          }`}
        />

        {/* Main circle */}
        <div
          className={`glow-candle flex h-48 w-48 items-center justify-center rounded-full border border-[--color-gold]/30 bg-[--color-gold]/5 transition-all duration-[4000ms] ease-in-out ${
            isRunning ? circleScale : ""
          }`}
        >
          <div className="text-center">
            {isRunning && !isComplete && (
              <>
                <p className="font-scripture mb-1 text-2xl text-[--color-gold]">
                  {PHASE_LABELS[phase]}
                </p>
                <p className="mb-2 text-xs italic text-[--color-gold]/40">
                  {PHASE_LATIN[phase]}
                </p>
                <p className="text-sm text-[--color-sacred-text-muted]">
                  {formatTime(timeRemaining)}
                </p>
              </>
            )}

            {isComplete && (
              <div className="animate-fade-in">
                <p className="font-scripture text-xl text-[--color-gold]">
                  Amen
                </p>
                {closingPrayer && (
                  <p className="mt-2 max-w-[10rem] text-xs text-[--color-sacred-text-muted]">
                    {closingPrayer}
                  </p>
                )}
              </div>
            )}

            {!isRunning && !isComplete && (
              <div>
                <p className="font-scripture text-lg text-[--color-sacred-text-muted]">
                  {durationMinutes} min
                </p>
                <p className="mt-1 text-xs text-[--color-sacred-text-muted]/50">
                  Contemplatio
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Inner pulsing light */}
        {isRunning && (
          <div className="animate-breathe absolute h-4 w-4 rounded-full bg-[--color-candlelight]" />
        )}
      </div>

      {/* Jesus Prayer rhythm toggle */}
      {jesusPrayerRhythm && isRunning && (
        <button
          onClick={() => setShowJesusPrayer(!showJesusPrayer)}
          className="mt-4 text-xs text-[--color-sacred-text-muted]/60 transition-colors hover:text-[--color-gold]/70"
        >
          {showJesusPrayer ? "Ukryj Modlitwe Jezusowa" : "Modlitwa Jezusowa"}
        </button>
      )}
      {showJesusPrayer && isRunning && (
        <p className="animate-fade-in mt-2 max-w-xs text-center font-scripture text-sm text-[--color-gold]/60">
          {jesusPrayerRhythm}
        </p>
      )}

      {/* Controls */}
      <div className="mt-8 flex gap-4">
        {!isRunning && !isComplete && (
          <button
            onClick={handleStart}
            className="glow-gold rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-8 py-3 font-medium text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
          >
            Rozpocznij kontemplacje
          </button>
        )}

        {isRunning && (
          <button
            onClick={() => setIsRunning(false)}
            className="rounded-lg border border-[--color-sacred-border] px-6 py-3 text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/30 hover:text-[--color-gold]"
          >
            Pauza
          </button>
        )}

        {!isRunning && timeRemaining < totalSeconds && !isComplete && (
          <button
            onClick={() => setIsRunning(true)}
            className="rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-6 py-3 text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
          >
            Kontynuuj
          </button>
        )}

        {(isComplete || (!isRunning && timeRemaining < totalSeconds)) && (
          <button
            onClick={handleReset}
            className="rounded-lg border border-[--color-sacred-border] px-6 py-3 text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/30 hover:text-[--color-gold]"
          >
            Od nowa
          </button>
        )}
      </div>

      {/* Sound toggle */}
      <button
        onClick={() => setSoundEnabled((v) => !v)}
        className="mt-4 flex items-center gap-1.5 text-xs text-[--color-sacred-text-muted]/40 transition-colors hover:text-[--color-gold]/60"
        title={soundEnabled ? "Wycisz dźwięki" : "Włącz dźwięki"}
      >
        {soundEnabled ? <Bell className="h-3.5 w-3.5" /> : <BellOff className="h-3.5 w-3.5" />}
        {soundEnabled ? "Dźwięk: włączony" : "Dźwięk: wyciszony"}
      </button>

      {/* Instructions */}
      {!isRunning && !isComplete && (
        <p className="mt-6 max-w-sm text-center text-sm text-[--color-sacred-text-muted]/70">
          Usiadz wygodnie, zamknij oczy i oddychaj w rytm animacji. Pozwol, aby
          cisza napelnila Twoje serce Boza obecnoscia.
          {sacredWord && (
            <span className="mt-2 block text-[--color-gold]/50">
              Slowo swiete: &ldquo;{sacredWord}&rdquo;
            </span>
          )}
        </p>
      )}
    </div>
  );
}
