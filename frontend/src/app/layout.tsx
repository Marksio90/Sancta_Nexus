import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { ToastContainer } from "@/components/ui/toast";
import { LiturgicalSeasonProvider } from "@/components/providers/LiturgicalSeasonProvider";
import { ServiceWorkerProvider } from "@/components/providers/ServiceWorkerProvider";
import { BottomNav } from "@/components/mobile/BottomNav";
import { InstallPrompt } from "@/components/mobile/InstallPrompt";

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
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Sancta Nexus",
  },
  // iOS meta tags for proper native feel
  other: {
    "mobile-web-app-capable": "yes",
    "apple-mobile-web-app-capable": "yes",
    "apple-mobile-web-app-status-bar-style": "black-translucent",
    "apple-mobile-web-app-title": "Sancta Nexus",
    "msapplication-TileColor": "#0d0b1a",
    "msapplication-tap-highlight": "no",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  minimumScale: 1,
  viewportFit: "cover",           // iOS safe-area / notch support
  themeColor: "#0d0b1a",
  userScalable: false,            // prevent accidental zoom during prayer
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
        {/* Apple touch icons */}
        <link rel="apple-touch-icon" sizes="180x180" href="/icons/icon-192.svg" />
        <link rel="apple-touch-startup-image" href="/icons/icon-512.svg" />
        {/* Capacitor: prevent default touch behaviours that conflict with native */}
        <meta name="format-detection" content="telephone=no" />
      </head>
      <LiturgicalSeasonProvider>
        <body className="min-h-screen bg-sacred-bg text-sacred-text antialiased">
          {/* Service worker + offline pre-fetch + push subscription */}
          <ServiceWorkerProvider />

          <Header />

          {/* pb-16 on mobile to clear BottomNav */}
          <main className="pt-16 pb-16 md:pb-0">{children}</main>

          <ToastContainer />

          {/* Mobile-only bottom navigation */}
          <BottomNav />

          {/* PWA / native app install prompt */}
          <InstallPrompt />
        </body>
      </LiturgicalSeasonProvider>
    </html>
  );
}
