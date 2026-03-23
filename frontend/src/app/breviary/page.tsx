"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Sun, Sunset, Moon, BookOpen, Bell } from "lucide-react";
import { getLiturgicalInfo } from "@/lib/liturgical-season";
import { playPrayerBell } from "@/lib/audio";

type Hour = "lauds" | "vespers" | "compline";

interface HourData {
  id: Hour;
  name: string;
  latin: string;
  time: string;
  icon: React.ElementType;
  opening: string;
  psalmRef: string;
  psalmText: string;
  reading: string;
  readingRef: string;
  responsory: string;
  canticle: string;
  canticleRef: string;
  closing: string;
}

const HOURS: HourData[] = [
  {
    id: "lauds",
    name: "Jutrznia",
    latin: "Laudes",
    time: "Poranna modlitwa — o wschodzie słońca",
    icon: Sun,
    opening: "Boże, wejrzyj ku wspomożeniu memu. Panie, pospiesz ku ratunkowi memu.",
    psalmRef: "Ps 63,2-9",
    psalmText:
      "Boże, Ty Boże mój, szukam Cię\ni pragnie Ciebie moja dusza.\nCiało moje tęskni za Tobą,\njak ziemia zeschła, spragniona, bez wody.\n\nOglądałem Cię w świątyni,\npatrząc na Twoją potęgę i chwałę.\nTwoja łaska jest cenniejsza od życia,\nmoje wargi będą Cię sławiły.",
    reading: "Wielka jest Twoja miłość, która ocaliła mnie od przepaści zagłady.",
    readingRef: "Iz 38,17",
    responsory: "Usta moje będą głosiły chwałę Twoją. — Alleluja, alleluja.",
    canticle: "Błogosławiony Pan, Bóg Izraela, bo nawiedził i wyzwolił swój lud.",
    canticleRef: "Łk 1,68-79 (Benedictus)",
    closing: "Panie, rozkaż, aby Twoi aniołowie strzegli nas przez cały dzień. Prowadź nas dziś, byśmy żyli w zgodzie z Twoją wolą.",
  },
  {
    id: "vespers",
    name: "Nieszpory",
    latin: "Vesperae",
    time: "Wieczorna modlitwa — o zachodzie słońca",
    icon: Sunset,
    opening: "Boże, wejrzyj ku wspomożeniu memu. Panie, pospiesz ku ratunkowi memu.",
    psalmRef: "Ps 141,2-4",
    psalmText:
      "Niech moja modlitwa dotrze przed oblicze Twoje\njak kadzidło;\nniech moje wzniesione dłonie będą\njak ofiara wieczorna.\n\nPanie, postaw straż przy moich ustach,\nstrzeż bramy moich warg!\nNiech serce moje nie skłania się ku złemu\ni niech nie popełniam czynów bezbożnych.",
    reading: "Jak kadzidło niech wznosi się moja modlitwa ku Tobie.",
    readingRef: "Ps 141,2",
    responsory: "Niech Pan nas błogosławi i strzeże. — Niech swoje oblicze skieruje ku nam.",
    canticle: "Wielbi dusza moja Pana i raduje się duch mój w Bogu, moim Zbawcy.",
    canticleRef: "Łk 1,46-55 (Magnificat)",
    closing: "Chroń nas, Panie, gdy czuwamy, strzeż nas, kiedy śpimy, abyśmy czuwali z Chrystusem i spoczywali w pokoju.",
  },
  {
    id: "compline",
    name: "Kompleta",
    latin: "Completorium",
    time: "Modlitwa na zakończenie dnia — przed snem",
    icon: Moon,
    opening: "Boże, wejrzyj ku wspomożeniu memu. Panie, pospiesz ku ratunkowi memu.",
    psalmRef: "Ps 91,1-4",
    psalmText:
      "Kto przebywa w pieczy Najwyższego\ni mieszka w cieniu Wszechmocnego,\nmówi do Pana: «Ucieczko moja i twierdzo,\nmój Boże, któremu zaufałem».\n\nOn sam wyzwoli cię z sideł myśliwego\ni od słowa zatrutego.\nSwoim piórami cię okryje,\npod Jego skrzydłami znajdziesz schronienie.",
    reading: "Bądźcie trzeźwi i czuwajcie! Przeciwnik wasz, diabeł, jak lew ryczący krąży szukając kogo pożreć.",
    readingRef: "1 P 5,8",
    responsory: "W ręce Twoje, Panie, oddaję ducha mego. — Ty nas odkupiłeś, Panie, Boże wierny.",
    canticle: "Teraz, o Władco, pozwól odejść słudze Twemu w pokoju, według Twojego słowa. Bo moje oczy ujrzały Twoje zbawienie.",
    canticleRef: "Łk 2,29-32 (Nunc Dimittis)",
    closing: "Pokój wam wszystkim, którzy trwacie w Chrystusie. Niech Bóg miłości i pokoju będzie z wami. Dobranoc w Chrystusie.",
  },
];

function getCurrentHour(): Hour {
  const h = new Date().getHours();
  if (h >= 4 && h < 12) return "lauds";
  if (h >= 12 && h < 20) return "vespers";
  return "compline";
}

export default function BreviaryPage() {
  const [activeHour, setActiveHour] = useState<Hour>(getCurrentHour());
  const [seasonInfo, setSeasonInfo] = useState(() => getLiturgicalInfo());
  const [step, setStep] = useState(0);

  const hourData = HOURS.find((h) => h.id === activeHour)!;
  const Icon = hourData.icon;

  const STEPS = [
    { label: "Otwarcie", content: hourData.opening },
    { label: "Psalm", content: `${hourData.psalmRef}\n\n${hourData.psalmText}` },
    { label: "Czytanie", content: `„${hourData.reading}"\n— ${hourData.readingRef}` },
    { label: "Responsorium", content: hourData.responsory },
    { label: "Kantyk", content: `${hourData.canticleRef}\n\n„${hourData.canticle}…"` },
    { label: "Zakończenie", content: hourData.closing },
  ];

  const handleBell = () => playPrayerBell();

  const handleHourChange = (h: Hour) => {
    setActiveHour(h);
    setStep(0);
    playPrayerBell();
  };

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-3xl">

        {/* Back */}
        <Link href="/" className="mb-8 inline-flex items-center gap-2 text-sm text-[--color-sacred-text-muted] transition-colors hover:text-[--color-gold]">
          <ArrowLeft className="h-4 w-4" />
          Strona główna
        </Link>

        {/* Header */}
        <div className="mb-8 text-center">
          <p className="mb-2 text-xs tracking-[0.4em] uppercase text-[--color-gold]/40">
            {seasonInfo.label} · {seasonInfo.latin}
          </p>
          <h1 className="font-heading mb-2 text-4xl text-[--color-gold] md:text-5xl">
            Brewiarz
          </h1>
          <p className="text-sm text-[--color-sacred-text-muted]/60">
            Liturgia Godzin — codzienna modlitwa Kościoła
          </p>
          <div className="sacred-divider mx-auto mt-6 w-40" />
        </div>

        {/* Hour selector */}
        <div className="mb-8 grid grid-cols-3 gap-3">
          {HOURS.map((h) => {
            const HIcon = h.icon;
            const isActive = h.id === activeHour;
            return (
              <button
                key={h.id}
                onClick={() => handleHourChange(h.id)}
                className={`flex flex-col items-center gap-2 rounded-2xl border p-4 text-center transition-all ${
                  isActive
                    ? "border-[--color-gold]/50 bg-[--color-gold]/10 text-[--color-gold]"
                    : "border-[--color-sacred-border] bg-[--color-sacred-surface] text-[--color-sacred-text-muted] hover:border-[--color-gold]/30"
                }`}
              >
                <HIcon className="h-6 w-6" />
                <div>
                  <p className="font-heading text-sm font-bold">{h.name}</p>
                  <p className="text-xs italic opacity-60">{h.latin}</p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Time label */}
        <p className="mb-6 text-center text-xs text-[--color-sacred-text-muted]/50">
          <Icon className="mr-1 inline h-3.5 w-3.5" />
          {hourData.time}
        </p>

        {/* Current step */}
        <div className="relative rounded-2xl border border-[--color-gold]/20 bg-[--color-sacred-surface] p-8">
          {/* Corner ornaments */}
          <div className="pointer-events-none absolute left-3 top-3 text-2xl text-[--color-gold]/10">❧</div>
          <div className="pointer-events-none absolute bottom-3 right-3 rotate-180 text-2xl text-[--color-gold]/10">❧</div>

          {/* Step indicator */}
          <div className="mb-6 flex items-center justify-between">
            <span className="rounded-full border border-[--color-gold]/30 bg-[--color-gold]/10 px-3 py-1 text-xs font-medium text-[--color-gold]">
              {STEPS[step].label}
            </span>
            <span className="text-xs text-[--color-sacred-text-muted]/40">
              {step + 1} / {STEPS.length}
            </span>
          </div>

          <div className="sacred-divider mb-6" />

          {/* Content */}
          <div className="min-h-[200px] space-y-3">
            {STEPS[step].content.split("\n").map((line, i) => (
              <p
                key={i}
                className={`leading-relaxed ${
                  line === ""
                    ? "mt-2"
                    : line.startsWith("„") || line.startsWith("—")
                    ? "font-scripture text-lg italic text-[--color-parchment]"
                    : "font-scripture text-base text-[--color-sacred-text-muted]"
                }`}
              >
                {line || "\u00A0"}
              </p>
            ))}
          </div>

          <div className="sacred-divider mt-6" />

          {/* Navigation */}
          <div className="mt-6 flex items-center justify-between">
            <button
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              className="rounded-lg border border-[--color-sacred-border] px-5 py-2.5 text-sm text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/30 hover:text-[--color-gold] disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ← Wstecz
            </button>

            {/* Bell */}
            <button
              onClick={handleBell}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-[--color-gold]/20 bg-[--color-gold]/5 text-[--color-gold]/60 transition-all hover:bg-[--color-gold]/15 hover:text-[--color-gold]"
              title="Zabiję dzwon"
            >
              <Bell className="h-4 w-4" />
            </button>

            {step < STEPS.length - 1 ? (
              <button
                onClick={() => setStep((s) => s + 1)}
                className="rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-5 py-2.5 text-sm text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
              >
                Dalej →
              </button>
            ) : (
              <button
                onClick={() => { setStep(0); playPrayerBell(); }}
                className="rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-5 py-2.5 text-sm text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
              >
                Od początku ✝
              </button>
            )}
          </div>
        </div>

        {/* Step dots */}
        <div className="mt-4 flex justify-center gap-2">
          {STEPS.map((_, i) => (
            <button
              key={i}
              onClick={() => setStep(i)}
              className={`h-1.5 rounded-full transition-all ${
                i === step ? "w-6 bg-[--color-gold]" : "w-1.5 bg-[--color-sacred-border]"
              }`}
            />
          ))}
        </div>

        {/* Intro note */}
        <div className="mt-8 rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface] p-5 text-center">
          <p className="text-xs text-[--color-sacred-text-muted]/50 leading-relaxed">
            <BookOpen className="mr-1.5 inline h-3.5 w-3.5" />
            Liturgia Godzin to oficjalna modlitwa Kościoła, uświęcająca każdą porę dnia.
            Jutrznia — rano, Nieszpory — wieczorem, Kompleta — przed snem.
          </p>
        </div>

        {/* Links */}
        <div className="mt-6 flex justify-center gap-4">
          <Link href="/dashboard" className="text-sm text-[--color-sacred-text-muted]/50 transition-colors hover:text-[--color-gold]">
            Panel Duchowy
          </Link>
          <span className="text-[--color-sacred-border]">·</span>
          <Link href="/lectio-divina" className="text-sm text-[--color-sacred-text-muted]/50 transition-colors hover:text-[--color-gold]">
            Lectio Divina
          </Link>
        </div>
      </div>
    </div>
  );
}
