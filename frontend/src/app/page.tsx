"use client";

import Link from "next/link";
import {
  BookOpen,
  Search,
  MessageCircle,
  BarChart3,
  ArrowRight,
  Sparkles,
} from "lucide-react";

const features = [
  {
    icon: BookOpen,
    title: "Lectio Divina",
    description:
      "Przeżyj starożytną praktykę czytania Pisma Świętego prowadzoną przez AI, dostosowaną do Twojego stanu duchowego.",
    href: "/lectio-divina",
  },
  {
    icon: Search,
    title: "Interaktywna Biblia",
    description:
      "Zadaj pytanie i otrzymaj odpowiedź w czterech wymiarach: teologicznym, historycznym, psychologicznym i duchowym.",
    href: "/bible",
  },
  {
    icon: MessageCircle,
    title: "Kierownik Duchowy",
    description:
      "Rozmowa z AI kierownikiem duchowym w tradycji ignacjańskiej, karmelitańskiej, benedyktyńskiej lub franciszkańskiej.",
    href: "/spiritual-director",
  },
  {
    icon: BarChart3,
    title: "Panel Duchowy",
    description:
      "Śledź swoją podróż duchową, odkrywaj powtarzające się tematy i obserwuj swój wzrost w wierze.",
    href: "/dashboard",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative flex min-h-[85vh] flex-col items-center justify-center overflow-hidden px-4 text-center">
        {/* Background decorative elements */}
        <div className="pointer-events-none absolute inset-0">
          <div className="animate-sacred-pulse absolute left-1/2 top-1/4 h-96 w-96 -translate-x-1/2 rounded-full bg-[--color-gold]/5 blur-3xl" />
          <div className="animate-sacred-pulse absolute bottom-1/4 left-1/4 h-64 w-64 rounded-full bg-[--color-sacred-blue]/10 blur-3xl [animation-delay:2s]" />
          <div className="animate-sacred-pulse absolute bottom-1/3 right-1/4 h-72 w-72 rounded-full bg-[--color-candlelight]/5 blur-3xl [animation-delay:4s]" />
        </div>

        <div className="animate-fade-in relative z-10">
          {/* Brand symbol */}
          <div className="glow-gold mx-auto mb-8 flex h-20 w-20 items-center justify-center rounded-full border border-[--color-gold]/30 bg-[--color-sacred-surface]">
            <Sparkles className="h-10 w-10 text-[--color-gold]" />
          </div>

          <h1 className="font-heading mb-4 text-5xl tracking-wide text-[--color-gold] md:text-7xl">
            Sancta Nexus
          </h1>

          <p className="font-scripture mx-auto mb-6 max-w-2xl text-xl text-[--color-sacred-text-muted] md:text-2xl">
            &ldquo;Twoje Słowo jest lampą dla moich stóp i światłem na mojej
            ścieżce&rdquo;
          </p>

          <p className="mb-2 text-sm tracking-widest uppercase text-[--color-sacred-text-muted]/70">
            Psalm 119:105
          </p>

          <div className="sacred-divider mx-auto my-8 w-48" />

          <p className="mx-auto mb-10 max-w-lg text-lg text-[--color-sacred-text-muted]">
            Platforma duchowego wzrostu łącząca starożytną tradycję Lectio
            Divina z nowoczesną sztuczną inteligencją
          </p>

          <Link
            href="/lectio-divina"
            className="glow-gold group inline-flex items-center gap-3 rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-8 py-4 text-lg font-semibold text-[--color-gold] transition-all hover:border-[--color-gold]/60 hover:bg-[--color-gold]/20"
          >
            Rozpocznij Lectio Divina
            <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative px-4 py-24">
        <div className="sacred-divider mx-auto mb-16 w-64" />

        <h2 className="font-heading mb-4 text-center text-3xl text-[--color-gold] md:text-4xl">
          Odkryj Głębię Wiary
        </h2>
        <p className="mx-auto mb-16 max-w-xl text-center text-[--color-sacred-text-muted]">
          Cztery filary Twojej duchowej podróży, wspierane przez sztuczną
          inteligencję w służbie wiary
        </p>

        <div className="mx-auto grid max-w-6xl gap-6 md:grid-cols-2">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <Link
                key={feature.title}
                href={feature.href}
                className="group rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-8 transition-all hover:border-[--color-gold]/30 hover:bg-[--color-sacred-surface-light]"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg border border-[--color-gold]/20 bg-[--color-gold]/5">
                  <Icon className="h-6 w-6 text-[--color-gold]" />
                </div>
                <h3 className="font-heading mb-2 text-xl text-[--color-parchment]">
                  {feature.title}
                </h3>
                <p className="leading-relaxed text-[--color-sacred-text-muted]">
                  {feature.description}
                </p>
                <div className="mt-4 flex items-center gap-2 text-sm text-[--color-gold]/70 transition-colors group-hover:text-[--color-gold]">
                  Rozpocznij
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[--color-sacred-border] px-4 py-12 text-center">
        <p className="font-scripture text-[--color-sacred-text-muted]">
          &ldquo;Szukajcie, a znajdziecie&rdquo; — Mt 7:7
        </p>
        <p className="mt-4 text-sm text-[--color-sacred-text-muted]/50">
          Sancta Nexus &copy; {new Date().getFullYear()} &middot; Ad Maiorem
          Dei Gloriam
        </p>
      </footer>
    </div>
  );
}
