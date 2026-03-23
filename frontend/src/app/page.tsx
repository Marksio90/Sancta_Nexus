"use client";

import { useState, useEffect } from "react";
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
      "Przezywaj starozytna praktyke czytania Pisma Swietego prowadzona przez AI, dostosowana do Twojego stanu duchowego. Pelna Quadriga — 4 sensy Pisma, madrosc Ojcow Kosciola, unikalny fragment kazdego dnia.",
    href: "/lectio-divina",
    accent: "Ora et Lege",
  },
  {
    icon: Search,
    title: "Interaktywna Biblia",
    description:
      "Wyszukaj dowolne slowo, frase lub werset i otrzymaj wszystkie pasujace fragmenty z calego Pisma Swietego. Analizuj je w czterech wymiarach: teologicznym, historycznym, psychologicznym i duchowym.",
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
      "Sledz swoja podroz duchowa przez 8 filarow kerygmatycznych. Odkrywaj powtarzajace sie tematy i obserwuj swoj wzrost w wierze.",
    href: "/dashboard",
    accent: "Crescit cum Legente",
  },
];

const VERSES = [
  { text: "Bóg jest miłością", ref: "1 J 4,8" },
  { text: "Nie lękaj się, bo Ja jestem z tobą", ref: "Iz 41,10" },
  { text: "Pokój zostawiam wam, pokój mój daję wam", ref: "J 14,27" },
  { text: "Pan jest moim pasterzem, nie brak mi niczego", ref: "Ps 23,1" },
  { text: "Szukajcie, a znajdziecie", ref: "Mt 7,7" },
  { text: "Ufaj Panu z całego serca", ref: "Prz 3,5" },
  { text: "Miłujcie się wzajemnie, tak jak Ja was umiłowałem", ref: "J 15,12" },
  { text: "Z miłością wieczną umiłowałem cię", ref: "Jr 31,3" },
  { text: "Jeśli Bóg z nami, któż przeciwko nam?", ref: "Rz 8,31" },
  { text: "Błogosławieni czystego serca, albowiem oni Boga oglądać będą", ref: "Mt 5,8" },
  { text: "Moje jarzmo jest słodkie, a moje brzemię lekkie", ref: "Mt 11,30" },
  { text: "Wszystko mogę w Tym, który mnie umacnia", ref: "Flp 4,13" },
  { text: "Proście, a będzie wam dane", ref: "Mt 7,7" },
  { text: "Pan jest moją mocą i zbawieniem", ref: "Ps 118,14" },
  { text: "Przyjdźcie do Mnie wszyscy, którzy utrudzeni i obciążeni jesteście", ref: "Mt 11,28" },
  { text: "Łaska Pańska nade mną nie była daremna", ref: "1 Kor 15,10" },
  { text: "W miłości nie ma lęku", ref: "1 J 4,18" },
  { text: "Radujcie się zawsze w Panu", ref: "Flp 4,4" },
  { text: "Kto we Mnie wierzy, ma życie wieczne", ref: "J 6,47" },
  { text: "Niech miłość wasza będzie bez obłudy", ref: "Rz 12,9" },
  { text: "Słowo Twoje jest lampą dla moich kroków", ref: "Ps 119,105" },
  { text: "Miłosierdzie Jego jest wieczne", ref: "Ps 136,1" },
  { text: "Bóg jest dla nas ucieczką i mocą", ref: "Ps 46,2" },
  { text: "Choć chodzę ciemną doliną, zła się nie ulęknę", ref: "Ps 23,4" },
  { text: "Stworzył nas Bóg dla siebie i niespokojne jest serce nasze", ref: "Wyznania I,1" },
  { text: "Trwajcie w miłości mojej", ref: "J 15,9" },
  { text: "Pan jest blisko wszystkich, którzy Go wzywają", ref: "Ps 145,18" },
  { text: "Nawróćcie się do Mnie całym swym sercem", ref: "Jl 2,12" },
  { text: "Jam jest zmartwychwstanie i życie", ref: "J 11,25" },
  { text: "Czuwajcie i módlcie się", ref: "Mt 26,41" },
  { text: "Przybliżcie się do Boga, a On zbliży się do was", ref: "Jk 4,8" },
  { text: "Nikt nie może dwom panom służyć", ref: "Mt 6,24" },
  { text: "Módlcie się nieustannie", ref: "1 Tes 5,17" },
  { text: "Gdzie jest skarb twój, tam będzie i serce twoje", ref: "Mt 6,21" },
  { text: "Bądźcie doskonali, jak doskonały jest Ojciec wasz niebieski", ref: "Mt 5,48" },
  { text: "Kto nie kocha, nie zna Boga, bo Bóg jest miłością", ref: "1 J 4,8" },
  { text: "Oto stoję u drzwi i kołaczę", ref: "Ap 3,20" },
  { text: "Ja jestem chlebem życia", ref: "J 6,35" },
  { text: "Ty jesteś Piotr — Skała, i na tej Skale zbuduję mój Kościół", ref: "Mt 16,18" },
  { text: "Idźcie więc i nauczajcie wszystkie narody", ref: "Mt 28,19" },
  { text: "Pan jest sprawiedliwy we wszystkich swoich drogach", ref: "Ps 145,17" },
  { text: "Miłość nigdy nie ustaje", ref: "1 Kor 13,8" },
  { text: "Szczęśliwy człowiek, który pokłada nadzieję w Panu", ref: "Ps 84,13" },
  { text: "Uwielbiaj Pana, duszo moja", ref: "Ps 146,1" },
  { text: "Twarz swoją ukryłem przed tobą przez chwilę, lecz wieczną miłością zlituję się nad tobą", ref: "Iz 54,8" },
  { text: "Nieustannie śpiewam o łaskach Pana", ref: "Ps 89,2" },
  { text: "Kiedy pragnę, do Ciebie się garnie dusza moja", ref: "Ps 63,2" },
  { text: "Pana, Boga twego, będziesz miłował całym swoim sercem", ref: "Mt 22,37" },
  { text: "Miłujcie waszych nieprzyjaciół i módlcie się za tych, którzy was prześladują", ref: "Mt 5,44" },
  { text: "On sam nas ukochał i posłał Syna swojego jako ofiarę przebłagalną", ref: "1 J 4,10" },
];

export default function HomePage() {
  const [verse, setVerse] = useState<{ text: string; ref: string } | null>(null);

  useEffect(() => {
    const idx = Math.floor(Math.random() * VERSES.length);
    setVerse(VERSES[idx]);
  }, []);

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

          {verse ? (
            <>
              <p className="font-scripture mx-auto mb-6 max-w-2xl text-xl text-[--color-sacred-text-muted] md:text-2xl">
                &ldquo;{verse.text}&rdquo;
              </p>
              <p className="mb-2 text-sm tracking-widest uppercase text-[--color-sacred-text-muted]/70">
                {verse.ref}
              </p>
            </>
          ) : (
            <div className="mb-8 animate-pulse">
              <div className="mx-auto mb-4 h-6 w-80 rounded-full bg-[--color-sacred-surface-light]" />
              <div className="mx-auto h-4 w-24 rounded-full bg-[--color-sacred-surface-light]" />
            </div>
          )}

          <div className="sacred-divider mx-auto my-8 w-48" />

          <p className="mx-auto mb-10 max-w-lg text-lg text-[--color-sacred-text-muted]">
            Platforma duchowego wzrostu łącząca starożytną tradycję Lectio
            Divina z mocą sztucznej inteligencji — w służbie wiary, zakorzeniona
            w Piśmie Świętym i nauczaniu Kościoła
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
            &ldquo;Pismo Święte rośnie z tym, kto je czyta&rdquo;
          </p>
          <p className="mt-1 text-xs tracking-widest uppercase text-[--color-sacred-text-muted]/50">
            Św. Grzegorz Wielki
          </p>
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
          73 księgi &middot; 7 tradycji &middot; 8 filarów kerygmatycznych
        </p>
      </footer>
    </div>
  );
}
