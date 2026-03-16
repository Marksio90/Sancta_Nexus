"use client";

import { ArrowLeft, Flame, Calendar, TrendingUp, BookOpen, Heart } from "lucide-react";
import Link from "next/link";

/* ── Mock data ── */
const MOCK_STREAK = 7;

const MOCK_SESSIONS = [
  {
    id: "1",
    date: "2026-03-16",
    passage: "J 15:4-5",
    emotion: "Spokój z lekkim niepokojem",
    keyInsight: "Trwanie w Chrystusie wymaga codziennego wyboru",
  },
  {
    id: "2",
    date: "2026-03-15",
    passage: "Ps 23:1-6",
    emotion: "Wdzięczność",
    keyInsight: "Pan jest moim pasterzem — mogę zaufać Jego prowadzeniu",
  },
  {
    id: "3",
    date: "2026-03-14",
    passage: "Mt 6:25-34",
    emotion: "Lęk o przyszłość",
    keyInsight: "Nie martwić się o jutro — każdy dzień ma dość swojej biedy",
  },
  {
    id: "4",
    date: "2026-03-13",
    passage: "Rz 8:28-39",
    emotion: "Nadzieja",
    keyInsight: "Nic nie może odłączyć mnie od miłości Bożej",
  },
];

const MOCK_THEMES = [
  { theme: "Zaufanie Bogu", count: 12, trend: "up" as const },
  { theme: "Pokój wewnętrzny", count: 8, trend: "up" as const },
  { theme: "Lęk i niepokój", count: 6, trend: "down" as const },
  { theme: "Miłość bliźniego", count: 5, trend: "stable" as const },
  { theme: "Wdzięczność", count: 4, trend: "up" as const },
];

const JOURNEY_STAGES = [
  {
    name: "Oczyszczenie",
    description: "Via Purgativa",
    progress: 85,
  },
  {
    name: "Oświecenie",
    description: "Via Illuminativa",
    progress: 40,
  },
  {
    name: "Zjednoczenie",
    description: "Via Unitiva",
    progress: 10,
  },
];

export default function DashboardPage() {
  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-2 text-sm text-sacred-text-muted transition-colors hover:text-gold"
        >
          <ArrowLeft className="h-4 w-4" />
          Powrót
        </Link>

        <div className="mb-10">
          <h1 className="font-heading mb-3 text-3xl text-gold md:text-4xl">
            Panel Duchowy
          </h1>
          <p className="text-sacred-text-muted">
            Przegląd Twojej duchowej podróży i wzrostu w wierze
          </p>
        </div>

        {/* Top stats row */}
        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          {/* Prayer streak */}
          <div className="glow-candle rounded-xl border border-gold/20 bg-sacred-surface p-6 text-center">
            <Flame className="mx-auto mb-2 h-8 w-8 text-candlelight animate-flicker" />
            <p className="text-4xl font-bold text-gold">{MOCK_STREAK}</p>
            <p className="mt-1 text-sm text-sacred-text-muted">
              Dni modlitwy z rzędu
            </p>
          </div>

          {/* Total sessions */}
          <div className="rounded-xl border border-sacred-border bg-sacred-surface p-6 text-center">
            <BookOpen className="mx-auto mb-2 h-8 w-8 text-gold/70" />
            <p className="text-4xl font-bold text-parchment">
              {MOCK_SESSIONS.length}
            </p>
            <p className="mt-1 text-sm text-sacred-text-muted">
              Sesje Lectio Divina
            </p>
          </div>

          {/* Spiritual state */}
          <div className="rounded-xl border border-sacred-border bg-sacred-surface p-6 text-center">
            <Heart className="mx-auto mb-2 h-8 w-8 text-sacred-red-light" />
            <p className="text-lg font-semibold text-parchment">
              Pocieszenie duchowe
            </p>
            <p className="mt-1 text-sm text-sacred-text-muted">
              Aktualny stan ducha
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Recent sessions */}
          <div className="rounded-xl border border-sacred-border bg-sacred-surface p-6">
            <h2 className="font-heading mb-4 flex items-center gap-2 text-xl text-gold">
              <Calendar className="h-5 w-5" />
              Ostatnie sesje
            </h2>
            <div className="space-y-3">
              {MOCK_SESSIONS.map((session) => (
                <div
                  key={session.id}
                  className="rounded-lg border border-sacred-border bg-sacred-bg p-4 transition-colors hover:border-gold/20"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="font-medium text-parchment">
                      {session.passage}
                    </span>
                    <span className="text-xs text-sacred-text-muted">
                      {session.date}
                    </span>
                  </div>
                  <p className="mb-1 text-sm text-sacred-text-muted">
                    Stan: {session.emotion}
                  </p>
                  <p className="font-scripture text-sm text-gold-light">
                    {session.keyInsight}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Recurring themes */}
          <div className="rounded-xl border border-sacred-border bg-sacred-surface p-6">
            <h2 className="font-heading mb-4 flex items-center gap-2 text-xl text-gold">
              <TrendingUp className="h-5 w-5" />
              Powtarzające się tematy
            </h2>
            <div className="space-y-3">
              {MOCK_THEMES.map((item) => (
                <div
                  key={item.theme}
                  className="flex items-center justify-between rounded-lg border border-sacred-border bg-sacred-bg p-4"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-parchment">{item.theme}</span>
                    <span className="text-xs text-sacred-text-muted">
                      ({item.count}x)
                    </span>
                  </div>
                  <span
                    className={`text-sm ${
                      item.trend === "up"
                        ? "text-green-400"
                        : item.trend === "down"
                          ? "text-sacred-red-light"
                          : "text-sacred-text-muted"
                    }`}
                  >
                    {item.trend === "up"
                      ? "↑"
                      : item.trend === "down"
                        ? "↓"
                        : "→"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Journey progress */}
        <div className="mt-6 rounded-xl border border-sacred-border bg-sacred-surface p-6">
          <h2 className="font-heading mb-6 text-xl text-gold">
            Droga Duchowa
          </h2>
          <div className="grid gap-6 md:grid-cols-3">
            {JOURNEY_STAGES.map((stage) => (
              <div key={stage.name} className="text-center">
                <h3 className="font-heading mb-1 text-lg text-parchment">
                  {stage.name}
                </h3>
                <p className="mb-3 text-xs tracking-widest text-sacred-text-muted uppercase">
                  {stage.description}
                </p>
                <div className="mx-auto h-2 w-full overflow-hidden rounded-full bg-sacred-bg">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-gold-dark to-gold transition-all duration-1000"
                    style={{ width: `${stage.progress}%` }}
                  />
                </div>
                <p className="mt-2 text-sm text-sacred-text-muted">
                  {stage.progress}%
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="mt-8 text-center">
          <Link
            href="/lectio-divina"
            className="inline-flex items-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-6 py-3 text-gold transition-all hover:bg-gold/20"
          >
            <BookOpen className="h-5 w-5" />
            Rozpocznij nową sesję Lectio Divina
          </Link>
        </div>
      </div>
    </div>
  );
}
