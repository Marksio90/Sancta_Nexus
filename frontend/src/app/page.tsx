import Link from "next/link";
import {
  BookOpen,
  Search,
  MessageCircle,
  BarChart3,
  ArrowRight,
  ChevronRight,
  Church,
  Users,
  BookMarked,
  Flame,
  Heart,
  Star,
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
  { text: "Przyjdźcie do Mnie wszyscy, którzy utrudzeni jesteście", ref: "Mt 11,28" },
  { text: "Łaską jesteście zbawieni przez wiarę", ref: "Ef 2,8" },
  { text: "Radość w Panu jest waszą ostoją", ref: "Ne 8,10" },
  { text: "Nikt nie przychodzi do Ojca inaczej jak tylko przeze Mnie", ref: "J 14,6" },
  { text: "Żywe bowiem jest słowo Boże, skuteczne", ref: "Hbr 4,12" },
  { text: "Na początku było Słowo, a Słowo było u Boga", ref: "J 1,1" },
  { text: "Jestem pewien, że nic nas nie zdoła odłączyć od miłości Boga", ref: "Rz 8,38" },
  { text: "Stworzył więc Bóg człowieka na swój obraz", ref: "Rdz 1,27" },
  { text: "Moc bowiem w słabości się doskonali", ref: "2 Kor 12,9" },
  { text: "Zaufaj Panu całym swoim sercem", ref: "Prz 3,5" },
  { text: "Pan, Pan, Bóg miłosierny i łagodny", ref: "Wj 34,6" },
  { text: "Boję się tylko Pana, Boga mego — Jego jedynego się boję", ref: "Pwt 6,4" },
  { text: "Skosztujcie i zobaczcie, jak dobry jest Pan", ref: "Ps 34,9" },
  { text: "Z głębokości wołam do Ciebie, Panie", ref: "Ps 130,1" },
  { text: "Łaski Pana nie wyczerpują się, współczucie Jego nie ustaje", ref: "Lm 3,22" },
  { text: "On jest obrazem Boga niewidzialnego", ref: "Kol 1,15" },
  { text: "Dusze sprawiedliwych są w ręku Boga", ref: "Mdr 3,1" },
  { text: "Znam plany, jakie zamyślam co do was — plany pomyślności", ref: "Jr 29,11" },
  { text: "Ja jestem Alfa i Omega, Pierwszy i Ostatni", ref: "Ap 22,13" },
  { text: "Przyjdź, Panie Jezu!", ref: "Ap 22,20" },
];

interface Verse {
  text: string;
  ref: string;
}

async function fetchDailyVerse(): Promise<Verse> {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${API_BASE}/api/v1/bible/random-verse`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data: Verse = await res.json();
      if (data.text && data.ref) return data;
    }
  } catch {
    /* backend offline */
  }
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
    tagline: "Słuchaj, jak Bóg mówi do ciebie",
    description:
      "Starożytna praktyka modlitewna czytania Pisma. Cztery sensy Słowa — Quadriga — prowadzą przez tekst ku spotkaniu z Bogiem. Mądrość Ojców Kościoła na każde spotkanie.",
    href: "/lectio-divina",
    accent: "amber",
  },
  {
    icon: Search,
    title: "Interaktywna Biblia",
    latin: "Quaere et Invenies",
    tagline: "Cały katolicki kanon — 73 księgi",
    description:
      "Przeszukaj całe Pismo Święte jednym słowem lub zdaniem. Każdy fragment analizowany teologicznie, historycznie, psychologicznie i duchowo przez AI zakorzenioną w Tradycji.",
    href: "/bible",
    accent: "blue",
  },
  {
    icon: MessageCircle,
    title: "Asystent refleksji",
    latin: "Contemplata et Meditata",
    tagline: "Porządkuj myśli, wracaj do modlitwy",
    description:
      "Podziel się owocami modlitwy. Asystent pomaga je ułożyć i odkryć, co Bóg mówi przez doświadczenie. Nie zastępuje kapłana ani kierownika duchowego.",
    href: "/asystent-refleksji",
    accent: "purple",
  },
  {
    icon: BookMarked,
    title: "Dziennik duchowy",
    latin: "Cor ad Cor Loquitur",
    tagline: "Twój sekretny pamiętnik wiary",
    description:
      "Prywatny dziennik refleksji i owoców modlitwy. Tylko Ty widzisz swoje wpisy — przechowywane lokalnie, bez dostępu serwera. Eksportuj lub usuń kiedy chcesz.",
    href: "/dziennik",
    accent: "violet",
  },
  {
    icon: Flame,
    title: "Rachunek Sumienia",
    latin: "Cor Contritum et Humiliatum",
    tagline: "Ignacjański Examen wieczorny",
    description:
      "Pięć kroków ignacjańskich: Wdzięczność · Prośba o światło · Przegląd dnia · Skrucha · Postanowienie. Modlitwa, która prowadzi do sakramentu pojednania.",
    href: "/rachunek-sumienia",
    accent: "orange",
  },
  {
    icon: BarChart3,
    title: "Panel Duchowy",
    latin: "Crescit cum Legente",
    tagline: "Twoja podróż w wierze dzień po dniu",
    description:
      "Śledź wzrost przez osiem filarów kerygmatycznych. Odkrywaj powtarzające się tematy, obserwuj jak Bóg działa w Twoim życiu — cierpliwie, krok po kroku.",
    href: "/dzisiaj",
    accent: "emerald",
  },
  {
    icon: Church,
    title: "Przygotowanie Sakramentalne",
    latin: "Via Sacramentalis",
    tagline: "Sakramenty — bramy łaski",
    description:
      "Rachunek sumienia z AI-kierownikiem, RCIA dla dorosłych, Teologia Ciała dla małżeństw, bierzmowanie z 7 darami Ducha. Każda droga prowadzi do Chrystusa.",
    href: "/przygotowanie",
    accent: "rose",
  },
  {
    icon: Users,
    title: "Wspólnota",
    latin: "Ubi Caritas et Amor",
    tagline: "Kościół to my — razem",
    description:
      "Intencje modlitewne, grupy parafialne, Różaniec wspólnotowy z medytacją nad 20 tajemnicami i 8 nowennami. Modlić się razem to uobecniać Kościół.",
    href: "/wspolnota",
    accent: "teal",
  },
];

const accentClasses: Record<string, { bg: string; border: string; glow: string }> = {
  amber:  { bg: "from-amber-900/25 to-amber-950/10",  border: "hover:border-amber-600/50",  glow: "group-hover:shadow-[0_0_60px_rgba(217,119,6,0.08)]"  },
  blue:   { bg: "from-blue-900/25 to-blue-950/10",    border: "hover:border-blue-600/50",    glow: "group-hover:shadow-[0_0_60px_rgba(37,99,235,0.08)]"   },
  purple: { bg: "from-purple-900/25 to-purple-950/10",border: "hover:border-purple-600/50", glow: "group-hover:shadow-[0_0_60px_rgba(147,51,234,0.08)]"  },
  violet: { bg: "from-violet-900/25 to-violet-950/10",border: "hover:border-violet-600/50", glow: "group-hover:shadow-[0_0_60px_rgba(124,58,237,0.08)]"  },
  orange: { bg: "from-orange-900/25 to-orange-950/10",border: "hover:border-orange-600/50", glow: "group-hover:shadow-[0_0_60px_rgba(234,88,12,0.08)]"   },
  emerald:{ bg: "from-emerald-900/25 to-emerald-950/10",border:"hover:border-emerald-600/50",glow:"group-hover:shadow-[0_0_60px_rgba(5,150,105,0.08)]"   },
  rose:   { bg: "from-rose-900/25 to-rose-950/10",    border: "hover:border-rose-600/50",    glow: "group-hover:shadow-[0_0_60px_rgba(225,29,72,0.08)]"   },
  teal:   { bg: "from-teal-900/25 to-teal-950/10",    border: "hover:border-teal-600/50",    glow: "group-hover:shadow-[0_0_60px_rgba(20,184,166,0.08)]"  },
};

export default async function HomePage() {
  const verse = await fetchDailyVerse();

  return (
    <div className="min-h-screen">

      {/* ── HERO ──────────────────────────────────────────────────────────── */}
      <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 text-center">

        {/* Sacred light background */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          {/* Central radiance */}
          <div className="absolute left-1/2 top-0 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/4 rounded-full bg-[--color-gold]/3 blur-[180px]" />
          {/* Side glows */}
          <div className="animate-sacred-pulse absolute left-1/4 top-1/3 h-[400px] w-[400px] rounded-full bg-[--color-candlelight]/5 blur-[100px] [animation-delay:1s]" />
          <div className="animate-sacred-pulse absolute right-1/4 top-1/3 h-[400px] w-[400px] rounded-full bg-[--color-sacred-blue]/6 blur-[100px] [animation-delay:3s]" />
          {/* Bottom warmth */}
          <div className="animate-sacred-pulse absolute bottom-0 left-1/2 h-[300px] w-[600px] -translate-x-1/2 rounded-full bg-[--color-gold]/4 blur-[80px] [animation-delay:2s]" />
          {/* Subtle grid */}
          <div
            className="absolute inset-0 opacity-[0.012]"
            style={{
              backgroundImage: "radial-gradient(circle, var(--color-gold) 1px, transparent 1px)",
              backgroundSize: "56px 56px",
            }}
          />
        </div>

        <div className="animate-fade-in relative z-10 max-w-4xl">

          {/* IHS monogram / sacred mark */}
          <div className="mx-auto mb-12 flex flex-col items-center gap-3">
            <div className="glow-gold flex h-20 w-20 items-center justify-center rounded-full border border-[--color-gold]/30 bg-[--color-sacred-surface]/60 backdrop-blur-sm">
              <span className="font-heading text-2xl tracking-widest text-[--color-gold]">IHS</span>
            </div>
            <div className="h-px w-16 bg-gradient-to-r from-transparent via-[--color-gold]/40 to-transparent" />
          </div>

          {/* Title */}
          <p className="mb-3 text-[10px] tracking-[0.5em] uppercase text-[--color-gold]/35">
            Platforma duchowego wzrostu
          </p>
          <h1 className="font-heading mb-4 text-7xl tracking-wide text-[--color-gold] md:text-9xl">
            Sancta Nexus
          </h1>
          <p className="font-scripture mb-10 text-base italic tracking-[0.2em] text-[--color-gold]/30">
            Ad Maiorem Dei Gloriam
          </p>

          {/* Sacred divider */}
          <div className="mx-auto mb-12 flex items-center gap-4">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-[--color-gold]/25" />
            <Star className="h-3 w-3 fill-[--color-gold]/30 text-[--color-gold]/30" />
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-[--color-gold]/25" />
          </div>

          {/* Daily verse */}
          <div className="mb-12 rounded-2xl border border-[--color-gold]/10 bg-[--color-sacred-surface]/40 px-8 py-8 backdrop-blur-sm">
            <p className="mb-2 text-[10px] tracking-[0.4em] uppercase text-[--color-gold]/30">
              Słowo na dziś
            </p>
            <p className="font-scripture mx-auto mb-4 max-w-2xl text-2xl leading-relaxed text-[--color-sacred-text-muted] md:text-3xl">
              &ldquo;{verse.text}&rdquo;
            </p>
            <p className="text-sm tracking-[0.25em] uppercase text-[--color-gold]/45">
              — {verse.ref}
            </p>
            <div className="mt-4 flex justify-center">
              <VerseShareButton text={verse.text} ref_={verse.ref} />
            </div>
          </div>

          {/* Subtitle */}
          <p className="mx-auto mb-14 max-w-2xl text-lg leading-relaxed text-[--color-sacred-text-muted]/65">
            Łącząca tysiącletnią tradycję modlitwy Kościoła z mocą sztucznej inteligencji —
            w służbie wiary, zakorzeniona w Piśmie Świętym, Tradycji i Magisterium
          </p>

          {/* CTAs */}
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/lectio-divina"
              className="glow-gold group inline-flex items-center gap-3 rounded-xl border border-[--color-gold]/40 bg-[--color-gold]/10 px-10 py-4 text-base font-semibold text-[--color-gold] backdrop-blur-sm transition-all duration-300 hover:border-[--color-gold]/70 hover:bg-[--color-gold]/18 hover:shadow-[0_0_50px_rgba(212,175,55,0.12)]"
            >
              <BookOpen className="h-5 w-5" />
              Rozpocznij Lectio Divina
              <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
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

        {/* Scroll hint */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-[--color-sacred-text-muted]/20 pointer-events-none">
          <ChevronRight className="h-4 w-4 rotate-90 animate-bounce" />
        </div>
      </section>

      {/* ── SAINT QUOTE ────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden px-6 py-24">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/2 top-1/2 h-[400px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[--color-gold]/2 blur-[120px]" />
        </div>
        <div className="relative mx-auto max-w-3xl text-center">
          <div className="mb-8 flex items-center justify-center gap-6">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-[--color-gold]/20" />
            <Heart className="h-4 w-4 fill-[--color-gold]/20 text-[--color-gold]/30" />
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-[--color-gold]/20" />
          </div>
          <p className="font-scripture text-2xl leading-relaxed text-[--color-sacred-text-muted]/80 md:text-3xl">
            &ldquo;Pismo Święte rośnie z tym, kto je czyta&rdquo;
          </p>
          <p className="mt-4 text-xs tracking-[0.35em] uppercase text-[--color-sacred-text-muted]/35">
            Święty Grzegorz Wielki · Moralia in Iob
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-8 text-xs text-[--color-sacred-text-muted]/30">
            <span>73 Księgi · Kanon katolicki</span>
            <span className="text-[--color-gold]/20">·</span>
            <span>Biblia Tysiąclecia BT5</span>
            <span className="text-[--color-gold]/20">·</span>
            <span>7 tradycji duchowych</span>
            <span className="text-[--color-gold]/20">·</span>
            <span>8 filarów kerygmatycznych</span>
          </div>
        </div>
      </section>

      {/* ── FEATURES ───────────────────────────────────────────────────────── */}
      <section className="relative px-6 pb-32 pt-8">
        <div className="mx-auto max-w-6xl">

          {/* Section header */}
          <div className="mb-20 text-center">
            <p className="mb-3 text-[10px] tracking-[0.5em] uppercase text-[--color-gold]/35">
              Osiem kaplic
            </p>
            <h2 className="font-heading text-5xl text-[--color-gold] md:text-6xl">
              Drogi do Boga
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-[--color-sacred-text-muted]/60">
              Każde narzędzie to zaproszenie — głębiej w Słowo, głębiej w modlitwę,
              bliżej Tego, który jest Drogą, Prawdą i Życiem
            </p>
          </div>

          {/* Feature grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
            {features.map((feature) => {
              const Icon = feature.icon;
              const accent = accentClasses[feature.accent] ?? accentClasses.amber;
              return (
                <Link
                  key={feature.title}
                  href={feature.href}
                  className={`group relative overflow-hidden rounded-2xl border border-[--color-sacred-border] bg-gradient-to-br ${accent.bg} p-8 transition-all duration-500 ${accent.border} ${accent.glow} hover:shadow-[0_12px_50px_rgba(0,0,0,0.35)]`}
                >
                  {/* Hover overlay */}
                  <div className="absolute inset-0 rounded-2xl bg-[--color-gold]/[0.015] opacity-0 transition-opacity duration-500 group-hover:opacity-100" />

                  <div className="relative z-10">
                    {/* Top row: icon + latin */}
                    <div className="mb-6 flex items-start justify-between">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-[--color-gold]/20 bg-[--color-gold]/8 transition-all duration-300 group-hover:border-[--color-gold]/35 group-hover:bg-[--color-gold]/12">
                        <Icon className="h-6 w-6 text-[--color-gold]" />
                      </div>
                      <span className="font-scripture text-[11px] italic text-[--color-gold]/20 transition-colors group-hover:text-[--color-gold]/40">
                        {feature.latin}
                      </span>
                    </div>

                    {/* Title */}
                    <h3 className="font-heading mb-1 text-2xl text-[--color-parchment]">
                      {feature.title}
                    </h3>

                    {/* Tagline */}
                    <p className="mb-3 text-[11px] tracking-[0.2em] uppercase text-[--color-gold]/35">
                      {feature.tagline}
                    </p>

                    {/* Description */}
                    <p className="text-sm leading-relaxed text-[--color-sacred-text-muted]/70">
                      {feature.description}
                    </p>

                    {/* CTA */}
                    <div className="mt-6 flex items-center gap-2 text-sm font-medium text-[--color-gold]/50 transition-all duration-300 group-hover:gap-3 group-hover:text-[--color-gold]">
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

      {/* ── CLOSING PRAYER ─────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-t border-[--color-sacred-border] px-6 py-20">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute bottom-0 left-1/2 h-[300px] w-[600px] -translate-x-1/2 rounded-full bg-[--color-gold]/3 blur-[100px]" />
        </div>
        <div className="relative mx-auto max-w-2xl text-center">
          <div className="mb-8 flex items-center justify-center gap-4">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-[--color-gold]/15" />
            <span className="font-heading text-xs tracking-[0.4em] text-[--color-gold]/25">✦</span>
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-[--color-gold]/15" />
          </div>
          <p className="font-scripture text-xl leading-relaxed text-[--color-sacred-text-muted]/50">
            &ldquo;Szukajcie, a znajdziecie — kołaczcie, a otworzą wam&rdquo;
          </p>
          <p className="mt-2 text-xs text-[--color-sacred-text-muted]/25">Mt 7,7</p>
        </div>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────────────────────── */}
      <footer className="border-t border-[--color-sacred-border] px-6 py-12 text-center">
        <p className="text-sm text-[--color-sacred-text-muted]/35">
          Sancta Nexus &copy; {new Date().getFullYear()} &middot; Ad Maiorem Dei Gloriam
        </p>
        <p className="mt-1 text-xs text-[--color-sacred-text-muted]/20">
          73 księgi · 7 tradycji duchowych · 8 filarów kerygmatycznych
        </p>
        <div className="mt-5 flex justify-center gap-6 text-xs text-[--color-sacred-text-muted]/25">
          <Link href="/polityka-prywatnosci" className="hover:text-[--color-gold]/60 transition-colors">
            Polityka prywatności
          </Link>
          <Link href="/regulamin" className="hover:text-[--color-gold]/60 transition-colors">
            Regulamin
          </Link>
          <Link href="/cennik" className="hover:text-[--color-gold]/60 transition-colors">
            Premium
          </Link>
        </div>
        <p className="mt-6 text-[10px] tracking-[0.3em] uppercase text-[--color-sacred-text-muted]/15">
          Asystent refleksji · Nie zastępuje kapłana, spowiednika ani terapeuty
        </p>
      </footer>
    </div>
  );
}
