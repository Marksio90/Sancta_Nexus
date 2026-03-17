"use client";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  text?: string;
}

const SIZE_MAP = {
  sm: "h-6 w-6",
  md: "h-10 w-10",
  lg: "h-16 w-16",
};

export function LoadingSpinner({ size = "md", text }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className={`relative ${SIZE_MAP[size]}`}>
        {/* Outer ring */}
        <div
          className="absolute inset-0 rounded-full border-2 border-[--color-gold]/20"
        />
        {/* Spinning arc */}
        <div
          className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-[--color-gold]"
          style={{ animationDuration: "1.5s" }}
        />
        {/* Inner glow dot */}
        <div className="absolute inset-2 rounded-full bg-[--color-gold]/10 animate-sacred-pulse" />
      </div>
      {text && (
        <p className="text-sm text-[--color-sacred-text-muted] animate-sacred-pulse">
          {text}
        </p>
      )}
    </div>
  );
}

/** Full-page centered loading overlay */
export function LoadingOverlay({ text = "Ładowanie..." }: { text?: string }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[--color-sacred-bg]/80 backdrop-blur-sm">
      <LoadingSpinner size="lg" text={text} />
    </div>
  );
}
