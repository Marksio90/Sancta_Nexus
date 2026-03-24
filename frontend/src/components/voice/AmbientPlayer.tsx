"use client";

/**
 * AmbientPlayer — sacred background audio generator.
 *
 * All audio is synthesised in-browser via the Web Audio API.
 * No external files required.  Profiles:
 *
 *   silence          - Complete silence (default)
 *   gregorian_drone  - Low monophonic drone (D2 ~73 Hz) + warm overtones
 *   organ_drone      - Soft organ-like pad (D2 + fifth + octave)
 *   monastic_bells   - Slow repeating bell pattern (D3 → A3 → F#3)
 *   nature           - Pink-noise filtered to sound like gentle rain
 *
 * State is persisted to localStorage so the user's preference survives
 * page navigation.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { Music2, Volume1, VolumeX } from "lucide-react";

type AmbientProfile =
  | "silence"
  | "gregorian_drone"
  | "organ_drone"
  | "monastic_bells"
  | "nature";

interface Profile {
  id: AmbientProfile;
  label: string;
  emoji: string;
}

const PROFILES: Profile[] = [
  { id: "silence", label: "Cisza", emoji: "🤫" },
  { id: "gregorian_drone", label: "Chorał", emoji: "🎵" },
  { id: "organ_drone", label: "Organy", emoji: "⛪" },
  { id: "monastic_bells", label: "Dzwony", emoji: "🔔" },
  { id: "nature", label: "Natura", emoji: "🌧️" },
];

const STORAGE_KEY_PROFILE = "sancta_ambient_profile";
const STORAGE_KEY_VOLUME = "sancta_ambient_volume";

// ── Web Audio helpers ─────────────────────────────────────────────────────────

function createDroneNodes(
  ctx: AudioContext,
  masterGain: GainNode,
  frequencies: number[],
  gainValues: number[],
): OscillatorNode[] {
  return frequencies.map((freq, i) => {
    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    gainNode.gain.value = gainValues[i] ?? 0.05;
    osc.connect(gainNode);
    gainNode.connect(masterGain);
    osc.start();
    return osc;
  });
}

function createNatureNodes(ctx: AudioContext, masterGain: GainNode): AudioBufferSourceNode {
  // Pink-ish noise: white noise through low-pass filter
  const bufferSize = ctx.sampleRate * 2;
  const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < bufferSize; i++) {
    const white = Math.random() * 2 - 1;
    b0 = 0.99886 * b0 + white * 0.0555179;
    b1 = 0.99332 * b1 + white * 0.0750759;
    b2 = 0.96900 * b2 + white * 0.1538520;
    b3 = 0.86650 * b3 + white * 0.3104856;
    b4 = 0.55000 * b4 + white * 0.5329522;
    b5 = -0.7616 * b5 - white * 0.0168980;
    data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.11;
    b6 = white * 0.115926;
  }

  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.loop = true;

  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = 800;
  filter.Q.value = 0.5;

  source.connect(filter);
  filter.connect(masterGain);
  source.start();
  return source;
}

let _bellTimeout: ReturnType<typeof setTimeout> | null = null;

function scheduleBells(ctx: AudioContext, masterGain: GainNode): () => void {
  const bellFreqs = [293.66, 440.0, 369.99]; // D4, A4, F#4
  let i = 0;
  let active = true;

  const ring = () => {
    if (!active) return;
    const freq = bellFreqs[i % bellFreqs.length];
    i++;

    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;

    const now = ctx.currentTime;
    gainNode.gain.setValueAtTime(0.0001, now);
    gainNode.gain.linearRampToValueAtTime(0.18, now + 0.01);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, now + 4.0);

    // Harmonic partial
    const osc2 = ctx.createOscillator();
    const g2 = ctx.createGain();
    osc2.type = "sine";
    osc2.frequency.value = freq * 2.756;
    g2.gain.setValueAtTime(0.0001, now);
    g2.gain.linearRampToValueAtTime(0.06, now + 0.01);
    g2.gain.exponentialRampToValueAtTime(0.0001, now + 2.5);
    osc2.connect(g2);
    g2.connect(masterGain);
    osc2.start(now);
    osc2.stop(now + 3.0);

    osc.connect(gainNode);
    gainNode.connect(masterGain);
    osc.start(now);
    osc.stop(now + 5.0);

    // Ring every 6–10 seconds
    const delay = 6000 + Math.random() * 4000;
    _bellTimeout = setTimeout(ring, delay);
  };

  ring();
  return () => { active = false; if (_bellTimeout) clearTimeout(_bellTimeout); };
}

// ── Component ─────────────────────────────────────────────────────────────────

interface AmbientPlayerProps {
  className?: string;
}

export function AmbientPlayer({ className = "" }: AmbientPlayerProps) {
  const [profile, setProfile] = useState<AmbientProfile>("silence");
  const [volume, setVolume] = useState(0.35);
  const [isOpen, setIsOpen] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  const ctxRef = useRef<AudioContext | null>(null);
  const masterGainRef = useRef<GainNode | null>(null);
  const stopCurrentRef = useRef<(() => void) | null>(null);

  // Restore preferences
  useEffect(() => {
    const savedProfile = localStorage.getItem(STORAGE_KEY_PROFILE) as AmbientProfile | null;
    const savedVolume = localStorage.getItem(STORAGE_KEY_VOLUME);
    if (savedProfile) setProfile(savedProfile);
    if (savedVolume) setVolume(parseFloat(savedVolume));
  }, []);

  // Update master gain when volume/mute changes
  useEffect(() => {
    if (masterGainRef.current) {
      masterGainRef.current.gain.setTargetAtTime(
        isMuted ? 0 : volume,
        masterGainRef.current.context.currentTime,
        0.1,
      );
    }
  }, [volume, isMuted]);

  const stopAudio = useCallback(() => {
    stopCurrentRef.current?.();
    stopCurrentRef.current = null;
  }, []);

  const startProfile = useCallback(
    (p: AmbientProfile) => {
      stopAudio();
      if (p === "silence") return;

      // Lazily create AudioContext on user interaction
      if (!ctxRef.current) {
        ctxRef.current = new AudioContext();
      }
      const ctx = ctxRef.current;
      if (ctx.state === "suspended") ctx.resume();

      const master = ctx.createGain();
      master.gain.value = isMuted ? 0 : volume;
      master.connect(ctx.destination);
      masterGainRef.current = master;

      let cleanup: (() => void) | null = null;

      if (p === "gregorian_drone") {
        // D2 fundamental + harmonics
        const oscs = createDroneNodes(
          ctx, master,
          [73.42, 146.83, 220.0, 293.66, 110.0],
          [0.12, 0.06, 0.03, 0.02, 0.04],
        );
        cleanup = () => oscs.forEach((o) => { try { o.stop(); } catch { /* already stopped */ } });
      } else if (p === "organ_drone") {
        // D2 + A2 (fifth) + D3 (octave)
        const oscs = createDroneNodes(
          ctx, master,
          [73.42, 110.0, 146.83, 184.99, 220.0],
          [0.10, 0.07, 0.05, 0.03, 0.025],
        );
        // Add slight vibrato via LFO
        const lfo = ctx.createOscillator();
        const lfoGain = ctx.createGain();
        lfo.frequency.value = 0.3;
        lfoGain.gain.value = 0.8;
        lfo.connect(lfoGain);
        oscs.forEach((o) => lfoGain.connect(o.frequency));
        lfo.start();
        cleanup = () => {
          oscs.forEach((o) => { try { o.stop(); } catch { /* already stopped */ } });
          try { lfo.stop(); } catch { /* already stopped */ }
        };
      } else if (p === "monastic_bells") {
        const stopBells = scheduleBells(ctx, master);
        cleanup = stopBells;
      } else if (p === "nature") {
        const source = createNatureNodes(ctx, master);
        cleanup = () => { try { source.stop(); } catch { /* already stopped */ } };
      }

      stopCurrentRef.current = () => {
        cleanup?.();
        master.disconnect();
      };
    },
    [volume, isMuted, stopAudio],
  );

  const handleProfileChange = useCallback(
    (p: AmbientProfile) => {
      setProfile(p);
      localStorage.setItem(STORAGE_KEY_PROFILE, p);
      startProfile(p);
      setIsOpen(false);
    },
    [startProfile],
  );

  const handleVolumeChange = useCallback((v: number) => {
    setVolume(v);
    localStorage.setItem(STORAGE_KEY_VOLUME, String(v));
  }, []);

  const toggleMute = useCallback(() => setIsMuted((m) => !m), []);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopAudio();
  }, [stopAudio]);

  const current = PROFILES.find((p) => p.id === profile)!;
  const isActive = profile !== "silence";

  return (
    <div className={`relative ${className}`}>
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        title="Podkład dźwiękowy"
        aria-label="Ustawienia podkładu muzycznego"
        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-all ${
          isActive && !isMuted
            ? "border-[--color-gold]/40 bg-[--color-gold]/10 text-[--color-gold]"
            : "border-[--color-sacred-border] bg-[--color-sacred-surface] text-[--color-sacred-text-muted]"
        } hover:border-[--color-gold]/40 hover:text-[--color-gold]`}
      >
        <Music2 className="h-3.5 w-3.5" />
        <span>{current.emoji} {current.label}</span>
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute right-0 top-10 z-50 w-52 animate-fade-in rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-3 shadow-lg">
          <p className="mb-2 text-[10px] uppercase tracking-widest text-[--color-sacred-text-muted]/40">
            Podkład modlitwy
          </p>

          {/* Profile list */}
          <div className="space-y-1">
            {PROFILES.map((p) => (
              <button
                key={p.id}
                onClick={() => handleProfileChange(p.id)}
                className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm transition-colors ${
                  profile === p.id
                    ? "bg-[--color-gold]/10 text-[--color-gold]"
                    : "text-[--color-sacred-text-muted] hover:bg-[--color-sacred-border]/30"
                }`}
              >
                <span>{p.emoji}</span>
                <span>{p.label}</span>
                {profile === p.id && isActive && !isMuted && (
                  <span className="ml-auto h-1.5 w-1.5 animate-pulse rounded-full bg-[--color-gold]" />
                )}
              </button>
            ))}
          </div>

          {/* Volume + mute */}
          {isActive && (
            <div className="mt-3 flex items-center gap-2 border-t border-[--color-sacred-border] pt-3">
              <button onClick={toggleMute} className="text-[--color-sacred-text-muted] hover:text-[--color-gold]">
                {isMuted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume1 className="h-3.5 w-3.5" />}
              </button>
              <input
                type="range"
                min={0.05}
                max={0.7}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={(e) => {
                  setIsMuted(false);
                  handleVolumeChange(parseFloat(e.target.value));
                }}
                className="flex-1 accent-[--color-gold]"
                aria-label="Głośność podkładu"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
