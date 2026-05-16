/**
 * English guest Lectio Divina page — /en/guest
 *
 * Wraps the Polish guest page with English metadata and UI strings.
 * The backend pipeline output (scripture, meditation, prayer) is in Polish
 * by default; full EN translation of AI output is a future roadmap item.
 */

import type { Metadata } from "next";
import { GuestPageEn } from "./GuestPageEn";

export const metadata: Metadata = {
  title: "Free Lectio Divina Session — Sancta Nexus",
  description:
    "Try one free Lectio Divina session without registration. Enter how you feel and receive AI-guided Scripture meditation in under 30 seconds.",
  alternates: {
    canonical: "https://sanctanexus.pl/en/guest",
    languages: {
      pl: "https://sanctanexus.pl/guest",
      en: "https://sanctanexus.pl/en/guest",
    },
  },
};

export default function EnglishGuestPage() {
  return <GuestPageEn />;
}
