/**
 * Individual novena page — SEO-optimized with structured data.
 *
 * Route: /nowenna/{novena-id}
 *
 * Static SEO content (title, description, JSON-LD) is generated server-side
 * via generateMetadata so Google indexes it without JS.  The interactive day
 * tracking portion is a client component rendered below the fold.
 */

import type { Metadata } from "next";
import { NovenaDetailClient } from "./NovenaDetailClient";

// ── Known novena IDs (match backend NOVENAS list) ──────────────────────────
// These are used for generateStaticParams so Next.js can SSG these pages.

const NOVENA_IDS = [
  "milosierdzie",
  "duch_swiety",
  "matka_boza",
  "sw_jozef",
  "sw_michal",
  "eucharystia",
  "sw_faustyna",
  "sw_jan_pawel",
];

// ── SEO metadata per novena ────────────────────────────────────────────────

const NOVENA_META: Record<
  string,
  { title: string; description: string; patron: string; scripture: string }
> = {
  milosierdzie: {
    title: "Nowenna do Miłosierdzia Bożego — 9 dni rozważań i modlitwy",
    description:
      "Nowenna podyktowana przez Jezusa Chrystusa świętej Faustynie. Polecamy Miłosierdziu Bożemu różne grupy dusz. Modlitwy, intencje i koronka na każdy dzień.",
    patron: "Jezus Miłosierny",
    scripture: "J 20,22-23",
  },
  duch_swiety: {
    title: "Nowenna do Ducha Świętego — 9 dni przed Zesłaniem",
    description:
      "Najstarsza nowenna Kościoła — naśladowanie uczniów modlących się przez 9 dni po Wniebowstąpieniu. Prośba o 7 darów Ducha Świętego.",
    patron: "Duch Święty",
    scripture: "J 14,16-17",
  },
  matka_boza: {
    title: "Nowenna do Matki Bożej Nieustającej Pomocy",
    description:
      "Modlitwa za wstawiennictwem Maryi Nieustającej Pomocy. 9 dni błagań, dziękczynienia i zawierzenia w trudnych chwilach życia.",
    patron: "Matka Boża Nieustającej Pomocy",
    scripture: "J 2,5",
  },
  sw_jozef: {
    title: "Nowenna do Świętego Józefa — patron rodzin i pracy",
    description:
      "Nowenna do opiekuna Świętej Rodziny. Prośba o pomoc w sprawach rodzinnych, zawodowych i o łaskę dobrej śmierci.",
    patron: "Święty Józef",
    scripture: "Mt 1,24",
  },
  sw_michal: {
    title: "Nowenna do Świętego Michała Archanioła",
    description:
      "9 dni modlitwy do Archanioła Michała — obrońcy Kościoła i przewodnika dusz. Prośba o ochronę i siłę do walki duchowej.",
    patron: "Święty Michał Archanioł",
    scripture: "Ap 12,7-9",
  },
  eucharystia: {
    title: "Nowenna eucharystyczna — adoracja i kontemplacja",
    description:
      "9 dni głębokiej adoracji eucharystycznej. Rozważania o Najświętszym Sakramencie, miłości Bożej i zjednoczeniu z Chrystusem.",
    patron: "Jezus Eucharystyczny",
    scripture: "J 6,51",
  },
  sw_faustyna: {
    title: "Nowenna do Świętej Faustyny Kowalskiej",
    description:
      "Modlitwa za wstawiennictwem Apostołki Bożego Miłosierdzia. 9 dni rozważań jej charyzmatów i przesłania.",
    patron: "Święta Faustyna Kowalska",
    scripture: "Łk 18,1",
  },
  sw_jan_pawel: {
    title: "Nowenna do Świętego Jana Pawła II",
    description:
      "9 dni modlitwy za wstawiennictwem patrona naszych czasów. Rozważania jego nauczania o rodzinie, godności i miłosierdziu.",
    patron: "Święty Jan Paweł II",
    scripture: "Flp 4,13",
  },
};

// ── generateStaticParams ───────────────────────────────────────────────────

export function generateStaticParams() {
  return NOVENA_IDS.map((id) => ({ id }));
}

// ── generateMetadata ───────────────────────────────────────────────────────

export async function generateMetadata({
  params,
}: {
  params: { id: string };
}): Promise<Metadata> {
  const meta = NOVENA_META[params.id];
  if (!meta) {
    return {
      title: "Nowenna | Sancta Nexus",
      description: "Modlitwa nowennowa — 9 dni ze Świętymi.",
    };
  }

  const canonicalUrl = `https://sanctanexus.pl/nowenna/${params.id}`;

  return {
    title: `${meta.title} | Sancta Nexus`,
    description: meta.description,
    keywords: [
      meta.patron,
      "nowenna",
      "modlitwa katolicka",
      "9 dni",
      meta.scripture,
      "Sancta Nexus",
    ],
    openGraph: {
      type: "article",
      title: meta.title,
      description: meta.description,
      url: canonicalUrl,
      siteName: "Sancta Nexus",
      locale: "pl_PL",
    },
    alternates: {
      canonical: canonicalUrl,
    },
    other: {
      "article:author": "Sancta Nexus",
      "article:section": "Nowenny",
    },
  };
}

// ── JSON-LD structured data (Prayer + Article) ─────────────────────────────

function NovenaJsonLd({ id }: { id: string }) {
  const meta = NOVENA_META[id];
  if (!meta) return null;

  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Article",
        headline: meta.title,
        description: meta.description,
        author: {
          "@type": "Organization",
          name: "Sancta Nexus",
          url: "https://sanctanexus.pl",
        },
        publisher: {
          "@type": "Organization",
          name: "Sancta Nexus",
          url: "https://sanctanexus.pl",
        },
        inLanguage: "pl",
        about: {
          "@type": "Thing",
          name: meta.patron,
        },
      },
      {
        "@type": "FAQPage",
        mainEntity: [
          {
            "@type": "Question",
            name: `Co to jest Nowenna do ${meta.patron}?`,
            acceptedAnswer: {
              "@type": "Answer",
              text: meta.description,
            },
          },
          {
            "@type": "Question",
            name: "Ile trwa nowenna?",
            acceptedAnswer: {
              "@type": "Answer",
              text:
                "Nowenna trwa 9 dni — stąd jej nazwa (łac. novem = dziewięć). Każdego dnia odmawiamy modlitwę i rozważamy wyznaczoną intencję.",
            },
          },
        ],
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}

// ── Page component ─────────────────────────────────────────────────────────

export default function NovenaPage({ params }: { params: { id: string } }) {
  const meta = NOVENA_META[params.id];

  return (
    <>
      <NovenaJsonLd id={params.id} />

      {/* SEO-visible above-the-fold content (server-rendered) */}
      <div className="mx-auto max-w-3xl px-4 py-10">
        {meta && (
          <div className="mb-8">
            <p className="text-xs text-amber-500 uppercase tracking-wider mb-2 font-medium">
              Nowenna · {meta.patron}
            </p>
            <h1 className="font-cinzel text-3xl font-bold text-sacred-text mb-3 leading-tight">
              {meta.title.replace(" | Sancta Nexus", "")}
            </h1>
            <p className="text-gray-400 text-sm leading-relaxed mb-2">
              {meta.description}
            </p>
            <p className="text-xs text-gray-600 italic">
              Fragment Pisma: {meta.scripture}
            </p>
          </div>
        )}

        {/* Interactive client component — day tracker, prayer text, etc. */}
        <NovenaDetailClient novenaId={params.id} />
      </div>
    </>
  );
}
