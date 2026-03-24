import Link from "next/link";
import {
  BookOpen,
  Search,
  MessageCircle,
  BarChart3,
  ArrowRight,
  Sparkles,
  Cross,
  ChevronRight,
  Church,
} from "lucide-react";
import { VerseShareButton } from "@/components/ui/verse-share-button";

/* ── Fallback verses (used when backend is offline) ─────────────────────── */
const FALLBACK_VERSES = [
  { text: "Bóg jest miłością", ref: "1 J 4,8" },
  { text: "Nie lękaj się, bo Ja jestem z tobą", ref: "Iz 41,10" },
  { text: "Pokój zostawiam wam, pokój mój daję wam", ref: "J 14,27" },
  { text: "Pan jest moim pasterzem, nie brak mi niczego", ref: "Ps 23,1" },
  { text: "Szukajcie, a znajdziecie", ref: "Mt 7,7" },
  { text: "Wszystko mogę w Tym, który mnie umacnia", ref: "Flp 4,13" },
  { text: "Miłujcie się wzajemnie, tak jak Ja was umiłowałem", ref: "J 15,12" },
  { text: "Z miłością wieczną umiłowałem cię", ref: "Jr 31,3" },
  { text: "Jeśli Bóg z nami, któż przeciwko nam?", ref: "Rz 8,31" },
  { text: "Błogosławieni czystego serca", ref: "Mt 5,8" },
  { text: "Moje jarzmo jest słodkie, a moje brzemię lekkie", ref: "Mt 11,30" },
  { text: "Kto we Mnie wierzy, ma życie wieczne", ref: "J 6,47" },
  { text: "W miłości nie ma lęku", ref: "1 J 4,18" },
  { text: "Radujcie się zawsze w Panu", ref: "Flp 4,4" },
  { text: "Słowo Twoje jest lampą dla moich kroków", ref: "Ps 119,105" },
  { text: "Miłosierdzie Jego jest wieczne", ref: "Ps 136,1" },
  { text: "Bóg jest dla nas ucieczką i mocą", ref: "Ps 46,2" },
  { text: "Trwajcie w miłości mojej", ref: "J 15,9" },
  { text: "Pan jest blisko wszystkich, którzy Go wzywają", ref: "Ps 145,18" },
  { text: "Jam jest zmartwychwstanie i życie", ref: "J 11,25" },
  { text: "Czuwajcie i módlcie się", ref: "Mt 26,41" },
  { text: "Przybliżcie się do Boga, a On zbliży się do was", ref: "Jk 4,8" },
  { text: "Módlcie się nieustannie", ref: "1 Tes 5,17" },
  { text: "Oto stoję u drzwi i kołaczę", ref: "Ap 3,20" },
  { text: "Ja jestem chlebem życia", ref: "J 6,35" },
  { text: "Miłość nigdy nie ustaje", ref: "1 Kor 13,8" },
  { text: "Miłuj Pana Boga swego całym sercem", ref: "Mt 22,37" },
  { text: "Miłujcie waszych nieprzyjaciół", ref: "Mt 5,44" },
  { text: "Gdzie jest skarb twój, tam będzie i serce twoje", ref: "Mt 6,21" },
];

interface Verse {
  text: string;
  ref: string;
}

/** Fetch daily verse on the server — no client-side flash. */
async function fetchDailyVerse(): Promise<Verse> {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${API_BASE}/api/v1/bible/random-verse`, {
      next: { revalidate: 3600 }, // refresh hourly
    });
    if (res.ok) {
      const data: Verse = await res.json();
      if (data.text && data.ref) return data;
    }
  } catch {
    /* backend offline — use fallback */
  }
  // Deterministic fallback based on day of year so it's consistent per day
  const dayOfYear = Math.floor(
    (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000
  );
  return FALLBACK_VERSES[dayOfYear % FALLBACK_VERSES.length];
}

const features = [
  {
    icon: BookOpen,
    title: "Lectio Divina",
    latin: "Ora et Lege",
    description:
      "Przeżywaj starożytną praktykę czytania Pisma Świętego prowadzoną przez AI. Pełna Quadriga — cztery sensy Pisma, mądrość Ojców Kościoła, unikalny fragment na każde spotkanie.",
    href: "/lectio-divina",
    color: "from-amber-900/20 to-amber-800/5",
    border: "hover:border-amber-600/40",
  },
  {
    icon: Search,
    title: "Interaktywna Biblia",
    latin: "Quaere et Invenies",
    description:
      "Wpisz jedno słowo, zdanie lub werset — przeszukamy całe 73 księgi katolickiego kanonu i zwrócimy najważniejsze fragmenty. Każdy analizowany teologicznie, historycznie, psychologicznie i duchowo.",
    href: "/bible",
    color: "from-blue-900/20 to-blue-800/5",
    border: "hover:border-blue-600/40",
  },
  {
    icon: MessageCircle,
    title: "Kierownik Duchowy",
    latin: "Contemplata Aliis Tradere",
    description:
      "Rozmowa z AI kierownikiem duchowym w siedmiu tradycjach: ignacjańskiej, karmelitańskiej, benedyktyńskiej, franciszkańskiej, charyzmatycznej, dominikańskiej i maryjnej.",
    href: "/spiritual-director",
    color: "from-purple-900/20 to-purple-800/5",
    border: "hover:border-purple-600/40",
  },
  {
    icon: BarChart3,
    title: "Panel Duchowy",
    latin: "Crescit cum Legente",
    description:
      "Śledź swoją podróż przez osiem filarów kerygmatycznych. Odkrywaj powtarzające się tematy i obserwuj wzrost w wierze — dzień po dniu, krok po kroku.",
    href: "/dashboard",
    color: "from-emerald-900/20 to-emerald-800/5",
    border: "hover:border-emerald-600/40",
  },
  {
    icon: Church,
    title: "Przygotowanie Sakramentalne",
    latin: "Via Sacramentalis",
    description:
      "Rachunek sumienia z AI-kierownikiem duchowym, program RCIA dla dorosłych, przygotowanie do małżeństwa (Teologia Ciała) i bierzmowania z 7 darami Ducha Świętego.",
    href: "/przygotowanie",
    color: "from-rose-900/20 to-rose-800/5",
    border: "hover:border-rose-600/40",
  },
];

export default async function HomePage() {
  const verse = await fetchDailyVerse();

  return (
    <div className="min-h-screen">

      {/* ── HERO ──────────────────────────────────────────────────────────── */}
      <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 text-center">

        {/* Ambient glows */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="animate-sacred-pulse absolute left-1/2 top-1/4 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-[--color-gold]/4 blur-[120px]" />
          <div className="animate-sacred-pulse absolute bottom-1/3 left-1/4 h-80 w-80 rounded-full bg-[--color-sacred-blue]/8 blur-[80px] [animation-delay:2s]" />
          <div className="animate-sacred-pulse absolute bottom-1/4 right-1/4 h-64 w-64 rounded-full bg-[--color-candlelight]/6 blur-[60px] [animation-delay:4s]" />
          <div
            className="absolute inset-0 opacity-[0.015]"
            style={{
              backgroundImage:
                "radial-gradient(circle, var(--color-gold) 1px, transparent 1px)",
              backgroundSize: "48px 48px",
            }}
          />
        </div>

        <div className="animate-fade-in relative z-10 max-w-3xl">

          {/* Brand mark */}
          <div className="glow-gold mx-auto mb-10 flex h-24 w-24 items-center justify-center rounded-full border border-[--color-gold]/25 bg-[--color-sacred-surface]/80 backdrop-blur-sm">
            <Sparkles className="h-12 w-12 text-[--color-gold]" />
          </div>

          {/* Title */}
          <p className="mb-2 text-xs tracking-[0.4em] uppercase text-[--color-gold]/40">
            Platforma duchowego wzrostu
          </p>
          <h1 className="font-heading mb-6 text-6xl tracking-wide text-[--color-gold] md:text-8xl">
            Sancta Nexus
          </h1>

          {/* Divider */}
          <div className="sacred-divider mx-auto mb-10 w-40" />

          {/* Daily verse — server-rendered, no flash */}
          <div className="mb-10">
            <p className="font-scripture mx-auto mb-3 max-w-2xl text-2xl leading-relaxed text-[--color-sacred-text-muted] md:text-3xl">
              &ldquo;{verse.text}&rdquo;
            </p>
            <p className="text-sm tracking-[0.3em] uppercase text-[--color-gold]/50">
              — {verse.ref}
            </p>
            <div className="mt-3 flex justify-center">
              <VerseShareButton text={verse.text} ref_={verse.ref} />
            </div>
          </div>

          {/* Subtitle */}
          <p className="mx-auto mb-12 max-w-xl text-lg leading-relaxed text-[--color-sacred-text-muted]/70">
            Łącząca starożytną tradycję Lectio Divina z mocą sztucznej
            inteligencji — w służbie wiary, zakorzeniona w Piśmie Świętym
            i nauczaniu Kościoła
          </p>

          {/* Primary CTA */}
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/lectio-divina"
              className="glow-gold group inline-flex items-center gap-3 rounded-xl border border-[--color-gold]/40 bg-[--color-gold]/10 px-10 py-4 text-lg font-semibold text-[--color-gold] backdrop-blur-sm transition-all duration-300 hover:border-[--color-gold]/70 hover:bg-[--color-gold]/20 hover:shadow-[0_0_40px_rgba(212,175,55,0.15)]"
            >
              Rozpocznij Lectio Divina
              <ArrowRight className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
            <Link
              href="/bible"
              className="inline-flex items-center gap-2 rounded-xl border border-[--color-sacred-border] px-8 py-4 text-base text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/30 hover:text-[--color-parchment]"
            >
              <Search className="h-4 w-4" />
              Szukaj w Piśmie Świętym
            </Link>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-[--color-sacred-text-muted]/30">
          <p className="text-xs tracking-widest uppercase">Odkryj</p>
          <ChevronRight className="h-4 w-4 rotate-90 animate-bounce" />
        </div>
      </section>

      {/* ── QUOTE BREAK ────────────────────────────────────────────────────── */}
      <section className="relative px-6 py-20">
        <div className="mx-auto max-w-4xl text-center">
          <div className="sacred-divider-cross mx-auto mb-10 w-64">
            <Cross className="h-4 w-4 text-[--color-gold]" />
          </div>
          <p className="font-scripture text-xl leading-relaxed text-[--color-sacred-text-muted]">
            &ldquo;Pismo Święte rośnie z tym, kto je czyta&rdquo;
          </p>
          <p className="mt-3 text-xs tracking-[0.3em] uppercase text-[--color-sacred-text-muted]/40">
            Święty Grzegorz Wielki · Moralia in Iob
          </p>
        </div>
      </section>

      {/* ── FEATURES ───────────────────────────────────────────────────────── */}
      <section className="relative px-6 pb-32 pt-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-16 text-center">
            <p className="mb-3 text-xs tracking-[0.4em] uppercase text-[--color-gold]/40">
              Cztery filary
            </p>
            <h2 className="font-heading text-4xl text-[--color-gold] md:text-5xl">
              Odkryj Głębię Wiary
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-[--color-sacred-text-muted]/70">
              Każde narzędzie zaprojektowane tak, by prowadzić Cię głębiej —
              w Słowo, w modlitwę, w spotkanie z Bogiem
            </p>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <Link
                  key={feature.title}
                  href={feature.href}
                  className={`group relative overflow-hidden rounded-2xl border border-[--color-sacred-border] bg-gradient-to-br ${feature.color} p-8 transition-all duration-300 ${feature.border} hover:shadow-[0_8px_40px_rgba(0,0,0,0.3)]`}
                >
                  <div className="absolute inset-0 rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100 bg-[--color-gold]/[0.02]" />
                  <div className="relative z-10">
                    <div className="mb-5 flex items-start justify-between">
                      <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-[--color-gold]/20 bg-[--color-gold]/8">
                        <Icon className="h-7 w-7 text-[--color-gold]" />
                      </div>
                      <span className="font-scripture text-xs italic text-[--color-gold]/25 transition-colors group-hover:text-[--color-gold]/40">
                        {feature.latin}
                      </span>
                    </div>
                    <h3 className="font-heading mb-3 text-2xl text-[--color-parchment]">
                      {feature.title}
                    </h3>
                    <p className="leading-relaxed text-[--color-sacred-text-muted]/80">
                      {feature.description}
                    </p>
                    <div className="mt-6 flex items-center gap-2 text-sm font-medium text-[--color-gold]/60 transition-all duration-300 group-hover:gap-3 group-hover:text-[--color-gold]">
                      Wejdź
                      <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────────────────────── */}
      <footer className="border-t border-[--color-sacred-border] px-6 py-16 text-center">
        <div className="sacred-divider mx-auto mb-8 w-32" />
        <p className="font-scripture text-lg text-[--color-sacred-text-muted]/60">
          &ldquo;Szukajcie, a znajdziecie — kołaczcie, a otworzą wam&rdquo;
        </p>
        <p className="mt-2 text-xs text-[--color-sacred-text-muted]/30">Mt 7,7</p>
        <p className="mt-8 text-sm text-[--color-sacred-text-muted]/40">
          Sancta Nexus &copy; {new Date().getFullYear()} &middot; Ad Maiorem Dei Gloriam
        </p>
        <p className="mt-2 text-xs text-[--color-sacred-text-muted]/20">
          73 księgi &middot; 7 tradycji duchowych &middot; 8 filarów kerygmatycznych
        </p>
      </footer>
    </div>
  );
}
