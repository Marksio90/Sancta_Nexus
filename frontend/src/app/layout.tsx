import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { ToastContainer } from "@/components/ui/toast";
import { LiturgicalSeasonProvider } from "@/components/providers/LiturgicalSeasonProvider";
import { ServiceWorkerProvider } from "@/components/providers/ServiceWorkerProvider";

export const metadata: Metadata = {
  title: "Sancta Nexus — AI Lectio Divina",
  description:
    "Platforma duchowego wzrostu łącząca starożytną tradycję Lectio Divina z nowoczesną sztuczną inteligencją. Odkryj głębię Pisma Świętego w sposób osobisty i transformujący.",
  keywords: [
    "Lectio Divina",
    "Biblia",
    "modlitwa",
    "duchowość",
    "AI",
    "kierownictwo duchowe",
  ],
  manifest: "/manifest.json",
  themeColor: "#0d0b1a",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Sancta Nexus",
  },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0d0b1a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pl">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700;900&family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link rel="apple-touch-icon" href="/icons/icon-192.svg" />
      </head>
      <LiturgicalSeasonProvider>
        <body className="min-h-screen bg-sacred-bg text-sacred-text antialiased">
          <ServiceWorkerProvider />
          <Header />
          <main className="pt-16">{children}</main>
          <ToastContainer />
        </body>
      </LiturgicalSeasonProvider>
    </html>
  );
}
