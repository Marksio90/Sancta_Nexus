"use client";

import {
  ArrowLeft,
  Flame,
  Calendar,
  TrendingUp,
  BookOpen,
  Heart,
  Sprout,
  Star,
  ArrowRight,
  ScrollText,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";
import { useProgressStore } from "@/stores/progress";
import { useNotesStore } from "@/stores/notes";

const ENCOURAGEMENTS = [
  { text: "Każda droga zaczyna się od pierwszego kroku. Twój dopiero przed Tobą.", ref: "Ps 37,23" },
  { text: "Pan czeka na Ciebie z otwartymi ramionami — tak jak ojciec czekał na syna.", ref: "Łk 15,20" },
  { text: "Kto szuka, ten znajdzie. Czas zacząć szukać.", ref: "Mt 7,7" },
  { text: "Słowo Twoje jest lampą dla moich kroków i światłem na mojej ścieżce.", ref: "Ps 119,105" },
  { text: "Trwajcie w miłości mojej — a radość wasza będzie pełna.", ref: "J 15,9.11" },
];

const JOURNEY_STAGES = [
  { name: "Oczyszczenie", latin: "Via Purgativa", description: "Odwracanie się od grzechu, oczyszczenie serca", icon: "✦", key: "purgativa" as const },
  { name: "Oświecenie", latin: "Via Illuminativa", description: "Wzrost w cnocie, poznanie prawd wiary", icon: "✦✦", key: "illuminativa" as const },
  { name: "Zjednoczenie", latin: "Via Unitiva", description: "Zjednoczenie woli z Wolą Bożą, kontemplacja", icon: "✦✦✦", key: "unitiva" as const },
];

const SPIRITUAL_STATES = [
  "Oczekujący", "Szukający", "Modlący się", "Kontemplujący", "Napełniony",
];

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("pl-PL", {
    day: "numeric", month: "long", year: "numeric",
  });
}

export default function DashboardPage() {
  const {
    loadFromStorage,
    prayerStreak,
    totalSessions,
    sessions,
    themes,
    journeyProgress,
  } = useProgressStore();

  const { loadFromStorage: loadNotes, getAllNotes, deleteNote } = useNotesStore();

  useEffect(() => {
    loadFromStorage();
    loadNotes();
  }, [loadFromStorage, loadNotes]);

  const savedNotes = getAllNotes();

  const encouragement =
    ENCOURAGEMENTS[(totalSessions + new Date().getDay()) % ENCOURAGEMENTS.length];

  const spiritualState =
    SPIRITUAL_STATES[Math.min(Math.floor(totalSessions / 5), SPIRITUAL_STATES.length - 1)];

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-5xl">

        {/* Back */}
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-2 text-sm text-sacred-text-muted transition-colors hover:text-gold"
        >
          <ArrowLeft className="h-4 w-4" />
          Strona główna
        </Link>

        {/* Header */}
        <div className="mb-10">
          <h1 className="font-heading mb-2 text-4xl text-gold md:text-5xl">
            Panel Duchowy
          </h1>
          <p className="text-[--color-sacred-text-muted]/70">
            Twoja duchowa podróż — każde spotkanie ze Słowem zapisane lokalnie
          </p>
        </div>

        {/* ── Stats row ── */}
        <div className="mb-8 grid gap-4 sm:grid-cols-3">

          {/* Prayer streak */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6 text-center">
            <div className={`mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border ${prayerStreak > 0 ? "border-amber-500/40 bg-amber-500/10" : "border-[--color-sacred-border] bg-[--color-sacred-bg]"}`}>
              <Flame className={`h-6 w-6 ${prayerStreak > 0 ? "text-amber-400" : "text-[--color-sacred-text-muted]/30"}`} />
            </div>
            <p className={`text-5xl font-bold ${prayerStreak > 0 ? "text-[--color-gold]" : "text-[--color-parchment]/60"}`}>
              {prayerStreak}
            </p>
            <p className="mt-1.5 text-sm font-medium text-[--color-sacred-text-muted]">
              Dni modlitwy z rzędu
            </p>
            <p className="mt-2 text-xs leading-relaxed text-[--color-sacred-text-muted]/40">
              {prayerStreak > 0 ? "Brawo! Kontynuuj" : "Pierwsze dni rozpalą ogień"}
            </p>
          </div>

          {/* Sessions */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6 text-center">
            <div className={`mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border ${totalSessions > 0 ? "border-blue-500/40 bg-blue-500/10" : "border-[--color-sacred-border] bg-[--color-sacred-bg]"}`}>
              <BookOpen className={`h-6 w-6 ${totalSessions > 0 ? "text-blue-400" : "text-[--color-sacred-text-muted]/30"}`} />
            </div>
            <p className={`text-5xl font-bold ${totalSessions > 0 ? "text-[--color-gold]" : "text-[--color-parchment]/60"}`}>
              {totalSessions}
            </p>
            <p className="mt-1.5 text-sm font-medium text-[--color-sacred-text-muted]">
              Sesje Lectio Divina
            </p>
            <p className="mt-2 text-xs leading-relaxed text-[--color-sacred-text-muted]/40">
              {totalSessions > 0 ? `Ostatnia: ${formatDate(sessions[0].date)}` : "Słowo czeka na pierwsze spotkanie"}
            </p>
          </div>

          {/* Spiritual state */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-[--color-sacred-border] bg-[--color-sacred-bg]">
              <Heart className={`h-6 w-6 ${totalSessions > 0 ? "text-rose-400" : "text-[--color-sacred-text-muted]/30"}`} />
            </div>
            <p className="text-lg font-semibold text-[--color-parchment]/70">
              {spiritualState}
            </p>
            <p className="mt-1.5 text-sm font-medium text-[--color-sacred-text-muted]">
              Stan ducha
            </p>
            <p className="mt-2 text-xs leading-relaxed text-[--color-sacred-text-muted]/40">
              Gotowy na spotkanie z Bogiem
            </p>
          </div>
        </div>

        {/* ── Sessions + Themes ── */}
        <div className="grid gap-6 lg:grid-cols-2">

          {/* Recent sessions */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6">
            <h2 className="font-heading mb-5 flex items-center gap-2 text-xl text-gold">
              <Calendar className="h-5 w-5" />
              Ostatnie sesje
            </h2>

            {sessions.length === 0 ? (
              <div className="flex flex-col items-center py-10 text-center">
                <div className="relative mb-5">
                  <div className="flex h-20 w-20 items-center justify-center rounded-full border border-[--color-sacred-border] bg-[--color-sacred-bg]">
                    <BookOpen className="h-9 w-9 text-[--color-sacred-text-muted]/15" />
                  </div>
                  <div className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full border border-[--color-sacred-border] bg-[--color-sacred-surface]">
                    <Star className="h-3.5 w-3.5 text-[--color-gold]/30" />
                  </div>
                </div>
                <p className="mb-1 text-sm font-medium text-[--color-parchment]/50">
                  Twoja historia jest jeszcze czystą kartą
                </p>
                <p className="mb-6 max-w-[200px] text-xs leading-relaxed text-[--color-sacred-text-muted]/40">
                  Każde spotkanie ze Słowem zostanie tutaj zapisane
                </p>
                <Link
                  href="/lectio-divina"
                  className="inline-flex items-center gap-2 rounded-xl border border-[--color-gold]/30 bg-[--color-gold]/8 px-5 py-2.5 text-sm font-medium text-[--color-gold] transition-all hover:bg-[--color-gold]/15"
                >
                  <BookOpen className="h-4 w-4" />
                  Zacznij Lectio Divina
                </Link>
              </div>
            ) : (
              <ul className="space-y-3">
                {sessions.slice(0, 6).map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center justify-between rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-bg] px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-[--color-parchment]">
                        {s.passageRef || "Lectio Divina"}
                      </p>
                      <p className="text-xs text-[--color-sacred-text-muted]/50">
                        {formatDate(s.date)} · {s.emotion}
                      </p>
                    </div>
                    <span className="text-xs text-[--color-gold]/50">
                      {s.durationMinutes} min
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Themes */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6">
            <h2 className="font-heading mb-5 flex items-center gap-2 text-xl text-gold">
              <TrendingUp className="h-5 w-5" />
              Powtarzające się tematy
            </h2>

            {themes.length === 0 ? (
              <div className="flex flex-col items-center py-10 text-center">
                <div className="relative mb-5">
                  <div className="flex h-20 w-20 items-center justify-center rounded-full border border-[--color-sacred-border] bg-[--color-sacred-bg]">
                    <Sprout className="h-9 w-9 text-[--color-sacred-text-muted]/15" />
                  </div>
                </div>
                <p className="mb-1 text-sm font-medium text-[--color-parchment]/50">
                  Tematy pojawią się po pierwszych sesjach
                </p>
                <p className="max-w-[220px] text-xs leading-relaxed text-[--color-sacred-text-muted]/40">
                  Pozwól Słowu zapuścić korzenie — wzorce ukażą się z czasem
                </p>
                <div className="mt-6 w-full space-y-2 opacity-20 select-none pointer-events-none">
                  {["Zaufanie", "Miłość", "Modlitwa"].map((t, i) => (
                    <div key={t} className="flex items-center justify-between rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-bg] px-4 py-2.5">
                      <span className="text-sm text-[--color-parchment]">{t}</span>
                      <div className="h-1.5 rounded-full bg-[--color-gold]" style={{ width: `${(3 - i) * 20}px` }} />
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <ul className="space-y-2">
                {themes.map((t) => (
                  <li key={t.name} className="flex items-center justify-between rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-bg] px-4 py-2.5">
                    <span className="text-sm text-[--color-parchment]">{t.name}</span>
                    <div className="flex items-center gap-2">
                      <div
                        className="h-1.5 rounded-full bg-[--color-gold] transition-all"
                        style={{ width: `${Math.min(t.count * 10, 60)}px` }}
                      />
                      <span className="text-xs text-[--color-gold]/50">{t.count}×</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* ── Journey progress ── */}
        <div className="mt-6 rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-7">
          <div className="mb-6">
            <h2 className="font-heading text-2xl text-gold">Droga Duchowa</h2>
            <p className="mt-1 text-sm text-[--color-sacred-text-muted]/50">
              Trzy etapy mistycznej tradycji Kościoła
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            {JOURNEY_STAGES.map((stage, idx) => {
              const progress = journeyProgress[stage.key];
              return (
                <div key={stage.name} className="relative">
                  {idx < JOURNEY_STAGES.length - 1 && (
                    <div className="absolute right-0 top-6 hidden h-px w-full translate-x-1/2 bg-[--color-sacred-border] md:block" />
                  )}
                  <div className="text-center">
                    <div className={`mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border ${progress > 0 ? "border-[--color-gold]/40 bg-[--color-gold]/10" : "border-[--color-sacred-border] bg-[--color-sacred-bg]"}`}>
                      <span className={`text-[10px] ${progress > 0 ? "text-[--color-gold]" : "text-[--color-sacred-text-muted]/30"}`}>
                        {stage.icon}
                      </span>
                    </div>
                    <h3 className="font-heading mb-0.5 text-lg text-[--color-parchment]/70">{stage.name}</h3>
                    <p className="mb-1 text-xs tracking-widest uppercase text-[--color-sacred-text-muted]/40">{stage.latin}</p>
                    <p className="mb-4 text-xs leading-relaxed text-[--color-sacred-text-muted]/30">{stage.description}</p>
                    <div className="mx-auto h-1.5 w-full overflow-hidden rounded-full bg-[--color-sacred-bg]">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-[--color-gold-dark] to-[--color-gold] transition-all duration-1000"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-[--color-sacred-text-muted]/25">
                      {progress > 0 ? `${progress}%` : "Początek drogi"}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Saved reflections (getAllNotes) ── */}
        {savedNotes.length > 0 && (
          <div className="mt-6 rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6">
            <h2 className="font-heading mb-5 flex items-center gap-2 text-xl text-gold">
              <ScrollText className="h-5 w-5" />
              Moje refleksje
              <span className="ml-auto text-sm font-normal text-[--color-gold]/40">
                {savedNotes.length} {savedNotes.length === 1 ? "notatka" : "notatek"}
              </span>
            </h2>
            <ul className="space-y-3">
              {savedNotes.map((note) => (
                <li
                  key={note.ref}
                  className="rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-bg] p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs font-semibold text-[--color-gold]/70">{note.ref}</p>
                    <button
                      onClick={() => deleteNote(note.ref)}
                      className="shrink-0 rounded p-1 text-[--color-sacred-text-muted]/30 transition-colors hover:text-[--color-sacred-red-light]/60"
                      title="Usuń notatkę"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <p className="font-scripture mt-2 line-clamp-3 text-sm leading-relaxed text-[--color-sacred-text-muted]">
                    {note.text}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ── Encouragement block ── */}
        <div className="mt-6 rounded-2xl border border-[--color-gold]/10 bg-gradient-to-br from-[--color-gold]/5 to-transparent p-7 text-center">
          <p className="font-scripture text-lg leading-relaxed text-[--color-sacred-text-muted]/70">
            &ldquo;{encouragement.text}&rdquo;
          </p>
          <p className="mt-2 text-xs tracking-widest uppercase text-[--color-gold]/30">
            {encouragement.ref}
          </p>
        </div>

        {/* ── CTA ── */}
        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/lectio-divina"
            className="inline-flex items-center gap-2 rounded-xl border border-[--color-gold]/40 bg-[--color-gold]/10 px-8 py-3.5 font-semibold text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
          >
            <BookOpen className="h-5 w-5" />
            Rozpocznij sesję Lectio Divina
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/breviary"
            className="inline-flex items-center gap-2 rounded-xl border border-[--color-sacred-border] px-6 py-3.5 text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/20 hover:text-[--color-parchment]"
          >
            Brewarz / Liturgia Godzin
          </Link>
        </div>
      </div>
    </div>
  );
}
