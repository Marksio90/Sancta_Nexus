/**
 * Haptic feedback for sacred interactions.
 *
 * Priority:
 *   1. Capacitor Haptics plugin (native iOS / Android — full fidelity)
 *   2. Web Vibration API (Android Chrome, no iOS support)
 *   3. Silent fallback (desktop)
 *
 * Usage:
 *   haptic.light()       — subtle tap (button presses, stage transitions)
 *   haptic.medium()      — bell ring, prayer start/end
 *   haptic.success()     — Lectio Divina session complete
 *   haptic.prayerBell()  — three pulses, like a monastery bell
 */

// ── Capacitor Haptics (dynamic import to avoid SSR errors) ────────────────────

type ImpactStyle = "Heavy" | "Medium" | "Light";
type NotificationType = "Success" | "Warning" | "Error";

async function capacitorImpact(style: ImpactStyle): Promise<boolean> {
  try {
    const { Haptics, ImpactStyle: IS } =
      await import("@capacitor/haptics");
    await Haptics.impact({ style: IS[style] });
    return true;
  } catch {
    return false;
  }
}

async function capacitorNotification(type: NotificationType): Promise<boolean> {
  try {
    const { Haptics, NotificationType: NT } =
      await import("@capacitor/haptics");
    await Haptics.notification({ type: NT[type] });
    return true;
  } catch {
    return false;
  }
}

async function capacitorVibrate(duration: number): Promise<boolean> {
  try {
    const { Haptics } = await import("@capacitor/haptics");
    await Haptics.vibrate({ duration });
    return true;
  } catch {
    return false;
  }
}

// ── Web Vibration API ─────────────────────────────────────────────────────────

function webVibrate(pattern: number | number[]): boolean {
  if (typeof navigator === "undefined" || !navigator.vibrate) return false;
  navigator.vibrate(pattern);
  return true;
}

// ── Media Session API — background audio continuity ──────────────────────────

export interface MediaSessionTrack {
  title: string;
  artist: string;
  album: string;
  artwork?: { src: string; sizes: string; type: string }[];
}

export function setMediaSession(
  track: MediaSessionTrack,
  callbacks?: {
    onPlay?: () => void;
    onPause?: () => void;
    onStop?: () => void;
  },
): void {
  if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return;

  navigator.mediaSession.metadata = new MediaMetadata({
    title: track.title,
    artist: track.artist,
    album: track.album,
    artwork: track.artwork ?? [
      { src: "/icons/icon-192.svg", sizes: "192x192", type: "image/svg+xml" },
      { src: "/icons/icon-512.svg", sizes: "512x512", type: "image/svg+xml" },
    ],
  });

  if (callbacks?.onPlay) {
    navigator.mediaSession.setActionHandler("play", callbacks.onPlay);
  }
  if (callbacks?.onPause) {
    navigator.mediaSession.setActionHandler("pause", callbacks.onPause);
  }
  if (callbacks?.onStop) {
    navigator.mediaSession.setActionHandler("stop", callbacks.onStop);
  }
}

export function clearMediaSession(): void {
  if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return;
  navigator.mediaSession.metadata = null;
  for (const action of ["play", "pause", "stop"] as const) {
    try {
      navigator.mediaSession.setActionHandler(action, null);
    } catch {
      // Some browsers throw if the action was never set
    }
  }
}

export function setMediaSessionPlaybackState(
  state: "playing" | "paused" | "none",
): void {
  if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return;
  navigator.mediaSession.playbackState = state;
}

// ── Public haptic helpers ─────────────────────────────────────────────────────

export const haptic = {
  /** Subtle feedback — button presses, text input */
  async light(): Promise<void> {
    if (await capacitorImpact("Light")) return;
    webVibrate(10);
  },

  /** Medium feedback — stage transitions, selections */
  async medium(): Promise<void> {
    if (await capacitorImpact("Medium")) return;
    webVibrate(20);
  },

  /** Heavy feedback — prayer start */
  async heavy(): Promise<void> {
    if (await capacitorImpact("Heavy")) return;
    webVibrate(40);
  },

  /** Success — session complete, Amen */
  async success(): Promise<void> {
    if (await capacitorNotification("Success")) return;
    webVibrate([30, 50, 30]);
  },

  /**
   * Prayer bell — three gentle pulses like a monastery bell.
   * Used at the start of Contemplatio.
   */
  async prayerBell(): Promise<void> {
    const done = await capacitorVibrate(40);
    if (done) {
      setTimeout(() => capacitorVibrate(40), 300);
      setTimeout(() => capacitorVibrate(40), 600);
      return;
    }
    webVibrate([40, 260, 40, 260, 40]);
  },

  /**
   * Breathing prompt — inhale / exhale rhythm.
   * Called at each breath cycle in BreathingTimer.
   */
  async breath(phase: "inhale" | "exhale"): Promise<void> {
    if (phase === "inhale") {
      if (await capacitorImpact("Light")) return;
      webVibrate(15);
    } else {
      if (await capacitorImpact("Light")) return;
      webVibrate(8);
    }
  },
};
