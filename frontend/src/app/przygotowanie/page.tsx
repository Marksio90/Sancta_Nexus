"use client";

import Link from "next/link";

const PROGRAMS = [
  {
    id: "spowiedz",
    href: "/spowiedz",
    icon: "✝",
    title: "Rachunek sumienia",
    subtitle: "Przygotowanie do Spowiedzi",
    description:
      "AI-prowadzony rachunek sumienia według 10 Przykazań i twojego stanu życia. Akt żalu i postanowienie poprawy.",
    ccc: "KKK §§ 1422–1498",
    color: "from-purple-900/60 to-purple-800/40",
    borderColor: "border-purple-700/50",
    duration: "30–60 min",
    badge: "Najważniejszy",
    badgeColor: "bg-purple-600",
  },
  {
    id: "rcia",
    href: "/rcia",
    icon: "🕊",
    title: "RCIA",
    subtitle: "Droga dorosłych do wiary",
    description:
      "14 sesji formacyjnych dla kandydatów do sakramentów inicjacji: Chrzest, Bierzmowanie, Eucharystia.",
    ccc: "KKK §§ 1212–1274",
    color: "from-blue-900/60 to-blue-800/40",
    borderColor: "border-blue-700/50",
    duration: "6–12 miesięcy",
    badge: "14 sesji",
    badgeColor: "bg-blue-600",
  },
  {
    id: "malzenstwo",
    href: "/malzenstwo",
    icon: "💍",
    title: "Przygotowanie do małżeństwa",
    subtitle: "Dla narzeczonych",
    description:
      "8 spotkań: Teologia Ciała, komunikacja, planowanie rodziny, modlitwa małżeńska. Amoris Laetitia.",
    ccc: "KKK §§ 1601–1658",
    color: "from-rose-900/60 to-rose-800/40",
    borderColor: "border-rose-700/50",
    duration: "2–3 miesiące",
    badge: "8 spotkań",
    badgeColor: "bg-rose-600",
  },
  {
    id: "bierzmowanie",
    href: "/bierzmowanie",
    icon: "🔥",
    title: "Przygotowanie do bierzmowania",
    subtitle: "Sakrament Ducha Świętego",
    description:
      "6 sesji: dary Ducha Świętego, świadectwo wiary, wybór patrona. AI-katechista.",
    ccc: "KKK §§ 1285–1321",
    color: "from-amber-900/60 to-amber-800/40",
    borderColor: "border-amber-700/50",
    duration: "6 tygodni",
    badge: "6 sesji",
    badgeColor: "bg-amber-600",
  },
];

export default function PrzygotowaniePage() {
  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      <div className="max-w-2xl mx-auto px-4 py-12 pb-24">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="text-5xl mb-4">⛪</div>
          <h1 className="text-3xl font-bold text-[#d4af37] mb-2">
            Przygotowanie Sakramentalne
          </h1>
          <p className="text-gray-400 text-sm leading-relaxed max-w-md mx-auto">
            Sakramenty to spotkania z żywym Bogiem. Każde przygotowanie
            prowadzi do głębszego przyjęcia Jego łaski.
          </p>
        </div>

        {/* Programs grid */}
        <div className="space-y-4">
          {PROGRAMS.map((p) => (
            <Link key={p.id} href={p.href}>
              <div
                className={`
                  relative rounded-2xl border ${p.borderColor}
                  bg-gradient-to-br ${p.color}
                  p-5 cursor-pointer
                  hover:border-opacity-80 hover:scale-[1.01]
                  transition-all duration-200
                `}
              >
                {/* Badge */}
                <span
                  className={`absolute top-4 right-4 text-xs px-2 py-0.5 rounded-full ${p.badgeColor} text-white font-medium`}
                >
                  {p.badge}
                </span>

                <div className="flex items-start gap-4">
                  <div className="text-3xl mt-0.5">{p.icon}</div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-lg font-semibold text-white mb-0.5">
                      {p.title}
                    </h2>
                    <p className="text-[#d4af37] text-xs mb-2">{p.subtitle}</p>
                    <p className="text-gray-300 text-sm leading-relaxed mb-3">
                      {p.description}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span>{p.ccc}</span>
                      <span>·</span>
                      <span>{p.duration}</span>
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Footer note */}
        <div className="mt-10 text-center text-xs text-gray-600 leading-relaxed">
          <p>
            Wszystkie programy oparte na Katechizmie Kościoła Katolickiego,
            <br />
            dokumentach Soboru Watykańskiego II i nauczaniu papieskim.
          </p>
        </div>
      </div>
    </main>
  );
}
