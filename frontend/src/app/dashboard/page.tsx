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
} from "lucide-react";
import Link from "next/link";

const JOURNEY_STAGES = [
  {
    name: "Oczyszczenie",
    latin: "Via Purgativa",
    description: "Odwracanie się od grzechu, oczyszczenie serca",
    icon: "✦",
    progress: 0,
  },
  {
    name: "Oświecenie",
    latin: "Via Illuminativa",
    description: "Wzrost w cnocie, poznanie prawd wiary",
    icon: "✦✦",
    progress: 0,
  },
  {
    name: "Zjednoczenie",
    latin: "Via Unitiva",
    description: "Zjednoczenie woli z Wolą Bożą, kontemplacja",
    icon: "✦✦✦",
    progress: 0,
  },
];

const ENCOURAGEMENTS = [
  {
    text: "Każda droga zaczyna się od pierwszego kroku. Twój dopiero przed Tobą.",
    ref: "Ps 37,23",
  },
  {
    text: "Pan czeka na Ciebie z otwartymi ramionami — tak jak ojciec czekał na syna.",
    ref: "Łk 15,20",
  },
  {
    text: "Kto szuka, ten znajdzie. Czas zacząć szukać.",
    ref: "Mt 7,7",
  },
];

const encouragement =
  ENCOURAGEMENTS[Math.floor(Math.random() * ENCOURAGEMENTS.length)];

export default function DashboardPage() {
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
            Twoja duchowa podróż zaczyna się tutaj — każde spotkanie ze Słowem
            zostanie tutaj zapisane
          </p>
        </div>

        {/* ── Stats row ── */}
        <div className="mb-8 grid gap-4 sm:grid-cols-3">

          {/* Prayer streak */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-[--color-sacred-border] bg-[--color-sacred-bg]">
              <Flame className="h-6 w-6 text-[--color-sacred-text-muted]/30" />
            </div>
            <p className="text-5xl font-bold text-[--color-parchment]/60">0</p>
            <p className="mt-1.5 text-sm font-medium text-[--color-sacred-text-muted]">
              Dni modlitwy z rzędu
            </p>
            <p className="mt-2 text-xs leading-relaxed text-[--color-sacred-text-muted]/40">
              Pierwsze dni rozpalą ogień
            </p>
          </div>

          {/* Sessions */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-[--color-sacred-border] bg-[--color-sacred-bg]">
              <BookOpen className="h-6 w-6 text-[--color-sacred-text-muted]/30" />
            </div>
            <p className="text-5xl font-bold text-[--color-parchment]/60">0</p>
            <p className="mt-1.5 text-sm font-medium text-[--color-sacred-text-muted]">
              Sesje Lectio Divina
            </p>
            <p className="mt-2 text-xs leading-relaxed text-[--color-sacred-text-muted]/40">
              Słowo czeka na pierwsze spotkanie
            </p>
          </div>

          {/* Spiritual state */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-[--color-sacred-border] bg-[--color-sacred-bg]">
              <Heart className="h-6 w-6 text-[--color-sacred-text-muted]/30" />
            </div>
            <p className="text-lg font-semibold text-[--color-parchment]/70">
              Oczekujący
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

          {/* Recent sessions — empty */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6">
            <h2 className="font-heading mb-5 flex items-center gap-2 text-xl text-gold">
              <Calendar className="h-5 w-5" />
              Ostatnie sesje
            </h2>

            <div className="flex flex-col items-center py-10 text-center">
              {/* Decorative "open book" visual */}
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
          </div>

          {/* Themes — empty */}
          <div className="rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-6">
            <h2 className="font-heading mb-5 flex items-center gap-2 text-xl text-gold">
              <TrendingUp className="h-5 w-5" />
              Powtarzające się tematy
            </h2>

            <div className="flex flex-col items-center py-10 text-center">
              {/* Seed visual */}
              <div className="relative mb-5">
                <div className="flex h-20 w-20 items-center justify-center rounded-full border border-[--color-sacred-border] bg-[--color-sacred-bg]">
                  <Sprout className="h-9 w-9 text-[--color-sacred-text-muted]/15" />
                </div>
              </div>

              <p className="mb-1 text-sm font-medium text-[--color-parchment]/50">
                Tematy pojawią się po pierwszych sesjach
              </p>
              <p className="mb-6 max-w-[220px] text-xs leading-relaxed text-[--color-sacred-text-muted]/40">
                Pozwól Słowu zapuścić korzenie — wzorce ukażą się z czasem
              </p>

              {/* Preview of how themes will look */}
              <div className="w-full space-y-2 opacity-20 select-none pointer-events-none">
                {["Zaufanie", "Miłość", "Modlitwa"].map((t, i) => (
                  <div
                    key={t}
                    className="flex items-center justify-between rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-bg] px-4 py-2.5"
                  >
                    <span className="text-sm text-[--color-parchment]">{t}</span>
                    <div className="flex items-center gap-2">
                      <div
                        className="h-1.5 rounded-full bg-[--color-gold]"
                        style={{ width: `${(3 - i) * 20}px` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── Journey progress ── */}
        <div className="mt-6 rounded-2xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-7">
          <div className="mb-6 flex items-start justify-between">
            <div>
              <h2 className="font-heading text-2xl text-gold">
                Droga Duchowa
              </h2>
              <p className="mt-1 text-sm text-[--color-sacred-text-muted]/50">
                Trzy etapy mistycznej tradycji Kościoła
              </p>
            </div>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            {JOURNEY_STAGES.map((stage, idx) => (
              <div key={stage.name} className="relative">
                {/* Connector line (not on last) */}
                {idx < JOURNEY_STAGES.length - 1 && (
                  <div className="absolute right-0 top-6 hidden h-px w-full translate-x-1/2 bg-[--color-sacred-border] md:block" />
                )}

                <div className="text-center">
                  {/* Stage indicator */}
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-[--color-sacred-border] bg-[--color-sacred-bg]">
                    <span className="text-[10px] text-[--color-sacred-text-muted]/30">
                      {stage.icon}
                    </span>
                  </div>

                  <h3 className="font-heading mb-0.5 text-lg text-[--color-parchment]/70">
                    {stage.name}
                  </h3>
                  <p className="mb-1 text-xs tracking-widest uppercase text-[--color-sacred-text-muted]/40">
                    {stage.latin}
                  </p>
                  <p className="mb-4 text-xs leading-relaxed text-[--color-sacred-text-muted]/30">
                    {stage.description}
                  </p>

                  {/* Progress bar */}
                  <div className="mx-auto h-1.5 w-full overflow-hidden rounded-full bg-[--color-sacred-bg]">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-[--color-gold-dark] to-[--color-gold] transition-all duration-1000"
                      style={{ width: `${stage.progress}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-[--color-sacred-text-muted]/25">
                    Początek drogi
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

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
            Rozpocznij pierwszą sesję Lectio Divina
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/bible"
            className="inline-flex items-center gap-2 rounded-xl border border-[--color-sacred-border] px-6 py-3.5 text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/20 hover:text-[--color-parchment]"
          >
            Otwórz Biblię
          </Link>
        </div>
      </div>
    </div>
  );
}
