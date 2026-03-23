/**
 * Sacred audio utilities using Web Audio API.
 * No external audio files required — tones are generated synthetically.
 */

let _ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!_ctx) {
    _ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
  }
  return _ctx;
}

/**
 * Play a church bell tone.
 * @param frequency Base frequency in Hz (default 440 = A4). A richer bell: 220 Hz.
 * @param duration  Duration in seconds.
 */
export function playBell(frequency = 220, duration = 3): void {
  const ctx = getCtx();
  if (!ctx) return;

  // Resume suspended context (required after user gesture on some browsers)
  if (ctx.state === "suspended") ctx.resume();

  const now = ctx.currentTime;

  // Main partial
  const createPartial = (freq: number, gain: number, decay: number) => {
    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(freq, now);

    gainNode.gain.setValueAtTime(gain, now);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, now + decay);

    osc.connect(gainNode);
    gainNode.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + decay);
  };

  // Church bell harmonic series (fundamental + overtones with detuning)
  createPartial(frequency, 0.4, duration);
  createPartial(frequency * 2.756, 0.2, duration * 0.7);
  createPartial(frequency * 5.404, 0.1, duration * 0.5);
  createPartial(frequency * 8.933, 0.05, duration * 0.3);
}

/**
 * Play a gentle prayer bell (higher, softer).
 */
export function playPrayerBell(): void {
  playBell(528, 4); // 528 Hz — "solfeggio frequency" often associated with spiritual tone
}

/**
 * Play a subtle tick sound (for breathing timer).
 */
export function playTick(): void {
  const ctx = getCtx();
  if (!ctx) return;
  if (ctx.state === "suspended") ctx.resume();

  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = "sine";
  osc.frequency.setValueAtTime(800, now);
  osc.frequency.exponentialRampToValueAtTime(400, now + 0.05);

  gain.gain.setValueAtTime(0.05, now);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.05);

  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(now);
  osc.stop(now + 0.05);
}

/**
 * Play a "silence bell" — very soft, fading long tone for entering silence.
 */
export function playSilenceBell(): void {
  playBell(174, 8); // Low, long, contemplative
}
