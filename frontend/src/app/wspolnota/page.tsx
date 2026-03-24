"use client";

import Link from "next/link";

const FEATURES = [
  {
    id: "intencje",
    href: "/intencje",
    icon: "🙏",
    title: "Intencje modlitewne",
    subtitle: "Publicznie i prywatnie",
    description:
      "Dziel się intencjami z wspólnotą. Módl się za innych kliknięciem. Oznaczaj odpowiedzi na modlitwy.",
    color: "from-violet-900/60 to-violet-800/30",
    border: "border-violet-700/50",
    badge: "Wspólnota",
    badgeColor: "bg-violet-700",
  },
  {
    id: "grupy",
    href: "/grupy",
    icon: "👥",
    title: "Grupy modlitewne",
    subtitle: "Parafia i online",
    description:
      "Dołącz do parafialnych grup różańcowych, adoracyjnych, rodzinnych. Twórz własne grupy modlitewne.",
    color: "from-emerald-900/60 to-emerald-800/30",
    border: "border-emerald-700/50",
    badge: "Parafia",
    badgeColor: "bg-emerald-700",
  },
  {
    id: "rozaniec",
    href: "/rozaniec",
    icon: "📿",
    title: "Różaniec wspólnotowy",
    subtitle: "4 zestawy tajemnic + medytacja AI",
    description:
      "Wszystkie 20 tajemnic z tekstem Pisma, owocami i medytacją duchową. Sesje wspólnotowe.",
    color: "from-blue-900/60 to-blue-800/30",
    border: "border-blue-700/50",
    badge: "Codziennie",
    badgeColor: "bg-blue-700",
  },
  {
    id: "nowenna",
    href: "/nowenna",
    icon: "🕯",
    title: "Nowenny z trackingiem",
    subtitle: "8 nowenn · 9 dni · postęp",
    description:
      "Biblioteka 8 nowenn (Miłosierdzie Boże, Duch Święty, MBNP…) z medytacją AI i codziennym śledzeniem.",
    color: "from-amber-900/60 to-amber-800/30",
    border: "border-amber-700/50",
    badge: "8 nowenn",
    badgeColor: "bg-amber-700",
  },
];

export default function WspolnotaPage() {
  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      <div className="max-w-2xl mx-auto px-4 py-12 pb-24">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="text-5xl mb-4">👥</div>
          <h1 className="text-3xl font-bold text-[#d4af37] mb-2">
            Wspólnota
          </h1>
          <p className="text-gray-400 text-sm leading-relaxed max-w-md mx-auto">
            «Gdzie dwóch lub trzech zbiera się w imię moje, tam jestem pośród
            nich» (Mt 18,20)
          </p>
        </div>

        {/* Feature cards */}
        <div className="space-y-4">
          {FEATURES.map((f) => (
            <Link key={f.id} href={f.href}>
              <div
                className={`
                  relative rounded-2xl border ${f.border}
                  bg-gradient-to-br ${f.color}
                  p-5 cursor-pointer
                  hover:scale-[1.01] transition-all duration-200
                `}
              >
                <span
                  className={`absolute top-4 right-4 text-xs px-2 py-0.5 rounded-full ${f.badgeColor} text-white font-medium`}
                >
                  {f.badge}
                </span>

                <div className="flex items-start gap-4">
                  <div className="text-3xl mt-0.5">{f.icon}</div>
                  <div className="flex-1 min-w-0 pr-16">
                    <h2 className="text-lg font-semibold text-white mb-0.5">
                      {f.title}
                    </h2>
                    <p className="text-[#d4af37] text-xs mb-2">{f.subtitle}</p>
                    <p className="text-gray-300 text-sm leading-relaxed">
                      {f.description}
                    </p>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>

        <div className="mt-10 text-center text-xs text-gray-600">
          «Miłujcie się wzajemnie, tak jak Ja was umiłowałem» — J 15,12
        </div>
      </div>
    </main>
  );
}
