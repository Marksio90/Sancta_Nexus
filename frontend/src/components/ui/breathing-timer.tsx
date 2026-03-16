"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface BreathingTimerProps {
  durationMinutes?: number;
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

export function BreathingTimer({ durationMinutes = 3 }: BreathingTimerProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [phase, setPhase] = useState<BreathPhase>("inhale");
  const [timeRemaining, setTimeRemaining] = useState(durationMinutes * 60);
  const [isComplete, setIsComplete] = useState(false);
  const phaseTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  // Phase cycling
  useEffect(() => {
    if (!isRunning || isComplete) return;

    phaseTimeoutRef.current = setTimeout(
      cyclePhase,
      PHASE_DURATION_MS[phase],
    );

    return () => {
      if (phaseTimeoutRef.current) clearTimeout(phaseTimeoutRef.current);
    };
  }, [isRunning, isComplete, phase, cyclePhase]);

  // Countdown timer
  useEffect(() => {
    if (!isRunning || isComplete) return;

    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          setIsComplete(true);
          setIsRunning(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isRunning, isComplete]);

  const handleStart = () => {
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
      {/* Breathing circle */}
      <div className="relative flex h-64 w-64 items-center justify-center">
        {/* Outer glow ring */}
        <div
          className={`absolute inset-0 rounded-full border-2 border-[--color-gold]/20 transition-all duration-[4000ms] ease-in-out ${
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
                <p className="font-scripture mb-2 text-2xl text-[--color-gold]">
                  {PHASE_LABELS[phase]}
                </p>
                <p className="text-sm text-[--color-sacred-text-muted]">
                  {formatTime(timeRemaining)}
                </p>
              </>
            )}

            {isComplete && (
              <p className="font-scripture text-xl text-[--color-gold]">
                Amen
              </p>
            )}

            {!isRunning && !isComplete && (
              <p className="font-scripture text-lg text-[--color-sacred-text-muted]">
                {durationMinutes} min
              </p>
            )}
          </div>
        </div>

        {/* Inner pulsing dot */}
        {isRunning && (
          <div className="animate-breathe absolute h-4 w-4 rounded-full bg-[--color-candlelight]" />
        )}
      </div>

      {/* Controls */}
      <div className="mt-8 flex gap-4">
        {!isRunning && !isComplete && (
          <button
            onClick={handleStart}
            className="glow-gold rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-8 py-3 font-medium text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
          >
            Rozpocznij kontemplację
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

      {/* Instructions */}
      {!isRunning && !isComplete && (
        <p className="mt-6 max-w-sm text-center text-sm text-[--color-sacred-text-muted]/70">
          Usiądź wygodnie, zamknij oczy i oddychaj w rytm animacji. Pozwól, aby
          cisza napełniła Twoje serce Bożą obecnością.
        </p>
      )}
    </div>
  );
}
