/**
 * English landing page — /en/
 *
 * Fully server-rendered for SEO. Targets English-speaking Catholic users
 * searching for "Lectio Divina app", "Catholic prayer app", "Ignatian examen".
 *
 * hreflang: pl → /, en → /en/ (set in root layout)
 */

import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Sancta Nexus — Catholic Prayer & Spiritual Formation App",
  description:
    "Lectio Divina, Rosary, Examination of Conscience, Divine Office, and an AI Reflection Assistant — the complete Catholic spiritual formation platform.",
  keywords: [
    "Lectio Divina app",
    "Catholic prayer app",
    "Ignatian examen",
    "Divine Office",
    "Catholic spiritual formation",
    "Rosary app",
    "AI reflection assistant",
    "Catholic app",
    "prayer journal",
  ],
  openGraph: {
    type: "website",
    title: "Sancta Nexus — Catholic Prayer & Spiritual Formation",
    description:
      "Your daily companion for Lectio Divina, Rosary, Examination of Conscience, Divine Office, and AI-assisted spiritual reflection.",
    url: "https://sanctanexus.pl/en",
    siteName: "Sancta Nexus",
    locale: "en_US",
  },
  alternates: {
    canonical: "https://sanctanexus.pl/en",
    languages: {
      pl: "https://sanctanexus.pl",
      en: "https://sanctanexus.pl/en",
    },
  },
};

const FEATURES = [
  {
    icon: "📖",
    title: "Lectio Divina",
    description:
      "A five-stage AI-guided Scripture meditation: Lectio → Meditatio → Oratio → Contemplatio → Actio. Powered by LangGraph, streamed in real-time.",
  },
  {
    icon: "🕊️",
    title: "Ignatian Examen",
    description:
      "Step-by-step Examination of Conscience following the Ignatian tradition. Reflect on gratitude, consolations, and tomorrow's resolution.",
  },
  {
    icon: "📿",
    title: "Rosary",
    description:
      "All four sets of mysteries with Scripture meditations and AI reflections. Communal Rosary synchronised in real-time.",
  },
  {
    icon: "🕐",
    title: "Divine Office",
    description:
      "Liturgy of the Hours — Lauds, Vespers, and Compline in the current liturgical season.",
  },
  {
    icon: "✍️",
    title: "Spiritual Journal",
    description:
      "Private prayer journal with AI-powered pattern discovery. Your data stays yours — encrypted and never used for training.",
  },
  {
    icon: "⛪",
    title: "Parish Groups",
    description:
      "Priests share an invite code; parishioners join with one tap. Shared prayer intentions and communal novenas.",
  },
] as const;

const JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      name: "Sancta Nexus",
      applicationCategory: "LifestyleApplication",
      operatingSystem: "Web, iOS, Android",
      description:
        "Catholic prayer and spiritual formation platform with AI-assisted Lectio Divina, Rosary, Ignatian Examen, and Divine Office.",
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "USD",
        description: "Free tier available",
      },
      inLanguage: ["pl", "en"],
      url: "https://sanctanexus.pl",
      author: {
        "@type": "Organization",
        name: "Sancta Nexus",
      },
    },
    {
      "@type": "FAQPage",
      mainEntity: [
        {
          "@type": "Question",
          name: "What is Lectio Divina?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Lectio Divina (Latin: divine reading) is an ancient Christian practice of slow, meditative reading of Scripture in four stages: Lectio (reading), Meditatio (meditation), Oratio (prayer), and Contemplatio (contemplation). Sancta Nexus adds a fifth stage, Actio (action), guided by an AI assistant.",
          },
        },
        {
          "@type": "Question",
          name: "Is Sancta Nexus a replacement for a priest or confessor?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "No. The AI Reflection Assistant helps you organise your thoughts and return to prayer. It does not replace a priest, confessor, spiritual director, or therapist. We make this explicit in every AI-generated response.",
          },
        },
        {
          "@type": "Question",
          name: "Is there a free version?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Yes. You can try one full Lectio Divina session without registering, or create a free account for ongoing access to core features including the Rosary, daily Scripture, and the Examen.",
          },
        },
      ],
    },
  ],
};

export default function EnglishLandingPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }}
      />

      <div className="mx-auto max-w-5xl px-4 py-16">
        {/* Language switcher */}
        <div className="mb-8 flex justify-end gap-3 text-sm">
          <Link href="/" className="text-gray-500 hover:text-amber-400 transition-colors">
            Polski
          </Link>
          <span className="text-amber-500 font-medium">English</span>
        </div>

        {/* Hero */}
        <div className="text-center mb-20">
          <p className="text-xs text-amber-500 uppercase tracking-widest mb-4 font-medium">
            Catholic Spiritual Formation Platform
          </p>
          <h1 className="font-cinzel text-5xl font-bold text-sacred-text mb-6 leading-tight md:text-6xl">
            Prayer and{" "}
            <span className="text-amber-400">Spiritual Formation</span>
          </h1>
          <p className="text-gray-400 text-lg leading-relaxed max-w-2xl mx-auto mb-8">
            Lectio Divina, Rosary, Examination of Conscience, Divine Office,
            and an AI Reflection Assistant — your complete Catholic companion.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/en/guest"
              className="rounded-xl bg-amber-600 px-8 py-4 font-semibold text-white hover:bg-amber-700 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              Try Lectio Divina Free
            </Link>
            <Link
              href="/auth/register"
              className="rounded-xl border border-white/10 px-8 py-4 font-semibold text-gray-300 hover:border-white/20 hover:text-white transition-colors"
            >
              Create Account
            </Link>
          </div>

          <p className="mt-4 text-xs text-gray-600">
            No credit card required · One free session without registration
          </p>
        </div>

        {/* Features */}
        <div className="mb-20">
          <h2 className="font-cinzel text-3xl font-bold text-sacred-text mb-10 text-center">
            Everything for your spiritual journey
          </h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="rounded-2xl border border-white/10 bg-white/5 px-6 py-6 hover:border-amber-500/20 transition-colors"
              >
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-cinzel text-lg font-semibold text-sacred-text mb-2">
                  {f.title}
                </h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Safety note */}
        <div className="mb-16 rounded-2xl border border-white/10 bg-white/5 px-8 py-6 text-center">
          <p className="text-sm text-gray-400 italic leading-relaxed">
            The AI Reflection Assistant helps you organise your thoughts and
            return to prayer. It does not replace a priest, confessor, spiritual
            director, or therapist.
          </p>
        </div>

        {/* Pricing teaser */}
        <div className="text-center mb-16">
          <h2 className="font-cinzel text-2xl font-bold text-sacred-text mb-4">
            Simple, transparent pricing
          </h2>
          <p className="text-gray-400 text-sm mb-6">
            Core features free forever. Premium unlocks unlimited AI sessions,
            voice prayer, and parish group tools.
          </p>
          <Link
            href="/cennik"
            className="text-amber-400 hover:underline text-sm"
          >
            View pricing →
          </Link>
        </div>

        {/* CTA */}
        <div className="text-center">
          <Link
            href="/auth/register"
            className="inline-block rounded-xl bg-amber-600 px-10 py-5 font-cinzel font-semibold text-white hover:bg-amber-700 transition-colors text-lg focus:outline-none focus:ring-2 focus:ring-amber-500 mb-3"
          >
            Start your spiritual journey
          </Link>
          <p className="text-xs text-gray-600">
            Free · No credit card · Cancel anytime
          </p>
        </div>
      </div>
    </>
  );
}
