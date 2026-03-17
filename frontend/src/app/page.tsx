"use client";

import Link from "next/link";
import {
  BookOpen,
  Search,
  MessageCircle,
  BarChart3,
  ArrowRight,
  Sparkles,
  Cross,
} from "lucide-react";

const features = [
  {
    icon: BookOpen,
    title: "Lectio Divina",
    description:
      "Przezywaj starozytna praktyke czytania Pisma Swietego prowadzona przez AI, dostosowana do Twojego stanu duchowego. Pelna Quadriga — 4 sensy Pisma, madrość Ojcow Kosciola, unikalny fragment kazdego dnia.",
    href: "/lectio-divina",
    accent: "Ora et Lege",
  },
  {
    icon: Search,
    title: "Interaktywna Biblia",
    description:
      "Zadaj pytanie i otrzymaj odpowiedz w czterech wymiarach: teologicznym, historycznym, psychologicznym i duchowym. 73 ksiegi katolickiego kanonu z kontekstem patrystycznym.",
    href: "/bible",
    accent: "Quaere et Invenies",
  },
  {
    icon: MessageCircle,
    title: "Kierownik Duchowy",
    description:
      "Rozmowa z AI kierownikiem duchowym w 7 tradycjach: ignacjanskiej, karmelitanskiej, benedyktynskiej, franciszkanskiej, charyzmatycznej, dominikanskiej i maryjnej.",
    href: "/spiritual-director",
    accent: "Contemplata Aliis Tradere",
  },
  {
    icon: BarChart3,
    title: "Panel Duchowy",
    description:
      "Sledz swoja podroż duchowa przez 8 filarow kerygmatycznych. Odkrywaj powtarzajace sie tematy i obserwuj swoj wzrost w wierze.",
    href: "/dashboard",
    accent: "Crescit cum Legente",
  },
];

/* Daily Scripture verses — rotated by day of year */
const DAILY_VERSES = [
  { text: "Bog jest miloscia", ref: "1 J 4,8" },
  { text: "Nie lekaj sie, bo Ja jestem z toba", ref: "Iz 41,10" },
  { text: "Pokoj zostawiam wam, pokoj moj daje wam", ref: "J 14,27" },
  { text: "Pan jest moim pasterzem, nie brak mi niczego", ref: "Ps 23,1" },
  { text: "Szukajcie, a znajdziecie", ref: "Mt 7,7" },
  { text: "Ja jestem droga, prawda i zyciem", ref: "J 14,6" },
  { text: "Ufaj Panu z calego serca", ref: "Prz 3,5" },
  { text: "Wieksze jest Swiatlo w was niz ciemnosc na swiecie", ref: "1 J 4,4" },
  { text: "Z miloscia wieczna umilowalam cie", ref: "Jr 31,3" },
  { text: "Jesli Bog z nami, ktoz przeciwko nam?", ref: "Rz 8,31" },
  { text: "Blogoslawieni czystego serca, albowiem oni Boga ogladac beda", ref: "Mt 5,8" },
  { text: "Moje jarzmo jest slodkie, a moje brzemie lekkie", ref: "Mt 11,30" },
];

function getDailyVerse() {
  const dayOfYear = Math.floor(
    (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000
  );
  return DAILY_VERSES[dayOfYear % DAILY_VERSES.length];
}

export default function HomePage() {
  const dailyVerse = getDailyVerse();

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
            &ldquo;{dailyVerse.text}&rdquo;
          </p>

          <p className="mb-2 text-sm tracking-widest uppercase text-[--color-sacred-text-muted]/70">
            {dailyVerse.ref}
          </p>

          <div className="sacred-divider mx-auto my-8 w-48" />

          <p className="mx-auto mb-10 max-w-lg text-lg text-[--color-sacred-text-muted]">
            Platforma duchowego wzrostu laczaca starozytna tradycje Lectio
            Divina z 47 agentami AI — w sluzbie wiary, zakorzeniona w Pismie
            Swietym i nauczaniu Kosciola
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

      {/* Kerygmatic pillars section */}
      <section className="relative px-4 py-16">
        <div className="mx-auto max-w-4xl text-center">
          <div className="sacred-divider-cross mx-auto mb-10 w-64">
            <Cross className="h-4 w-4 text-[--color-gold]" />
          </div>
          <p className="font-scripture text-[--color-sacred-text-muted]">
            &ldquo;Pismo Swiete rosnie z tym, kto je czyta&rdquo;
          </p>
          <p className="mt-1 text-xs tracking-widest uppercase text-[--color-sacred-text-muted]/50">
            Sw. Grzegorz Wielki
          </p>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative px-4 py-24">
        <div className="sacred-divider mx-auto mb-16 w-64" />

        <h2 className="font-heading mb-4 text-center text-3xl text-[--color-gold] md:text-4xl">
          Odkryj Glebie Wiary
        </h2>
        <p className="mx-auto mb-16 max-w-xl text-center text-[--color-sacred-text-muted]">
          Cztery filary Twojej duchowej podrozy, wspierane przez sztuczna
          inteligencje w sluzbie wiary
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
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-[--color-gold]/20 bg-[--color-gold]/5">
                    <Icon className="h-6 w-6 text-[--color-gold]" />
                  </div>
                  <span className="font-scripture text-xs text-[--color-gold]/30">
                    {feature.accent}
                  </span>
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
        <p className="mt-2 text-xs text-[--color-sacred-text-muted]/30">
          73 ksiegi &middot; 47 agentow &middot; 7 tradycji &middot; 8 filarow kerygmatycznych
        </p>
      </footer>
    </div>
  );
}
