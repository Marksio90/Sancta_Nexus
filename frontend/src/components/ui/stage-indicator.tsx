"use client";

interface StageIndicatorProps {
  stages: string[];
  currentStage: number;
}

export function StageIndicator({ stages, currentStage }: StageIndicatorProps) {
  return (
    <div className="w-full">
      {/* Progress bar */}
      <div className="relative mb-4 h-1 w-full overflow-hidden rounded-full bg-[--color-sacred-border]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[--color-gold-dark] to-[--color-gold] transition-all duration-500 ease-out"
          style={{
            width: `${((currentStage + 1) / stages.length) * 100}%`,
          }}
        />
      </div>

      {/* Stage labels */}
      <div className="flex justify-between">
        {stages.map((stage, index) => {
          const isCompleted = index < currentStage;
          const isCurrent = index === currentStage;
          const isFuture = index > currentStage;

          return (
            <div
              key={stage}
              className="flex flex-col items-center gap-2"
            >
              {/* Dot */}
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-all ${
                  isCompleted
                    ? "border-[--color-gold] bg-[--color-gold] text-[--color-sacred-bg]"
                    : isCurrent
                      ? "glow-gold border-[--color-gold] bg-[--color-gold]/20 text-[--color-gold]"
                      : "border-[--color-sacred-border] bg-[--color-sacred-surface] text-[--color-sacred-text-muted]"
                }`}
              >
                {isCompleted ? (
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={3}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M4.5 12.75l6 6 9-13.5"
                    />
                  </svg>
                ) : (
                  index + 1
                )}
              </div>

              {/* Label */}
              <span
                className={`text-center text-xs font-medium transition-colors ${
                  isCurrent
                    ? "text-[--color-gold]"
                    : isFuture
                      ? "text-[--color-sacred-text-muted]/50"
                      : "text-[--color-sacred-text-muted]"
                } hidden sm:block`}
              >
                {stage}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
