"use client";

import {
  ArrowLeft,
  Flame,
  Calendar,
  TrendingUp,
  BookOpen,
  Heart,
  Lock,
  Sprout,
} from "lucide-react";
import Link from "next/link";

const JOURNEY_STAGES = [
  {
    name: "Oczyszczenie",
    description: "Via Purgativa",
    progress: 0,
  },
  {
    name: "Oświecenie",
    description: "Via Illuminativa",
    progress: 0,
  },
  {
    name: "Zjednoczenie",
    description: "Via Unitiva",
    progress: 0,
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
            Twoja duchowa podróż dopiero się zaczyna — każdy krok zapisze się tutaj
          </p>
        </div>

        {/* Top stats row */}
        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          {/* Prayer streak */}
          <div className="rounded-xl border border-sacred-border bg-sacred-surface p-6 text-center">
            <Flame className="mx-auto mb-2 h-8 w-8 text-sacred-text-muted/30" />
            <p className="text-4xl font-bold text-parchment">0</p>
            <p className="mt-1 text-sm text-sacred-text-muted">
              Dni modlitwy z rzędu
            </p>
            <p className="mt-2 text-xs text-sacred-text-muted/50">
              Zacznij pierwszą sesję, aby zapalić ogień
            </p>
          </div>

          {/* Total sessions */}
          <div className="rounded-xl border border-sacred-border bg-sacred-surface p-6 text-center">
            <BookOpen className="mx-auto mb-2 h-8 w-8 text-sacred-text-muted/30" />
            <p className="text-4xl font-bold text-parchment">0</p>
            <p className="mt-1 text-sm text-sacred-text-muted">
              Sesje Lectio Divina
            </p>
            <p className="mt-2 text-xs text-sacred-text-muted/50">
              Pierwsze Słowo czeka na Ciebie
            </p>
          </div>

          {/* Spiritual state */}
          <div className="rounded-xl border border-sacred-border bg-sacred-surface p-6 text-center">
            <Heart className="mx-auto mb-2 h-8 w-8 text-sacred-text-muted/30" />
            <p className="text-lg font-semibold text-parchment">
              Oczekujący
            </p>
            <p className="mt-1 text-sm text-sacred-text-muted">
              Aktualny stan ducha
            </p>
            <p className="mt-2 text-xs text-sacred-text-muted/50">
              Gotowy na spotkanie z Bogiem
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Recent sessions — empty state */}
          <div className="rounded-xl border border-sacred-border bg-sacred-surface p-6">
            <h2 className="font-heading mb-4 flex items-center gap-2 text-xl text-gold">
              <Calendar className="h-5 w-5" />
              Ostatnie sesje
            </h2>
            <div className="flex flex-col items-center py-10 text-center">
              <BookOpen className="mb-4 h-12 w-12 text-sacred-text-muted/20" />
              <p className="mb-2 text-sm font-medium text-parchment/60">
                Twoja historia duchowa jest jeszcze czystą kartą
              </p>
              <p className="mb-6 text-xs leading-relaxed text-sacred-text-muted/50">
                Rozpocznij pierwszą modlitwę, aby ją zapisać
              </p>
              <Link
                href="/lectio-divina"
                className="rounded-lg border border-gold/30 bg-gold/10 px-4 py-2 text-sm text-gold transition-all hover:bg-gold/20"
              >
                Zacznij Lectio Divina
              </Link>
            </div>
          </div>

          {/* Recurring themes — empty state */}
          <div className="rounded-xl border border-sacred-border bg-sacred-surface p-6">
            <h2 className="font-heading mb-4 flex items-center gap-2 text-xl text-gold">
              <TrendingUp className="h-5 w-5" />
              Powtarzające się tematy
            </h2>
            <div className="flex flex-col items-center py-10 text-center">
              <div className="relative mb-4">
                <Sprout className="h-12 w-12 text-sacred-text-muted/20" />
                <Lock className="absolute -bottom-1 -right-1 h-5 w-5 text-sacred-text-muted/30" />
              </div>
              <p className="mb-2 text-sm font-medium text-parchment/60">
                Tematy pojawią się po pierwszych sesjach
              </p>
              <p className="text-xs leading-relaxed text-sacred-text-muted/50">
                Pozwól Słowu zapuścić korzenie — wzorce ukażą się z czasem
              </p>
            </div>
          </div>
        </div>

        {/* Journey progress */}
        <div className="mt-6 rounded-xl border border-sacred-border bg-sacred-surface p-6">
          <h2 className="font-heading mb-2 text-xl text-gold">
            Droga Duchowa
          </h2>
          <p className="mb-6 text-sm text-sacred-text-muted/60">
            Postęp będzie wzrastać wraz z każdą sesją modlitwy i Lectio Divina
          </p>
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
                <p className="mt-2 text-sm text-sacred-text-muted/50">
                  Początek drogi
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
            Rozpocznij pierwszą sesję Lectio Divina
          </Link>
        </div>
      </div>
    </div>
  );
}
