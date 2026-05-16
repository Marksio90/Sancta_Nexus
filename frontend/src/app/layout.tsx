import type { Metadata, Viewport } from "next";
import { Cinzel, Crimson_Text, Inter } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { ToastContainer } from "@/components/ui/toast";
import { LiturgicalSeasonProvider } from "@/components/providers/LiturgicalSeasonProvider";
import { ServiceWorkerProvider } from "@/components/providers/ServiceWorkerProvider";
import { ErrorBoundary } from "@/components/providers/ErrorBoundary";
import { BottomNav } from "@/components/mobile/BottomNav";
import { InstallPrompt } from "@/components/mobile/InstallPrompt";

const cinzel = Cinzel({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "900"],
  variable: "--font-cinzel",
  display: "swap",
});

const crimsonText = Crimson_Text({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-crimson",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sancta Nexus — Modlitwa i formacja duchowa",
  description:
    "Katolicka platforma modlitwy i formacji duchowej. Lectio Divina, Różaniec, Rachunek Sumienia, Brewiarz i Asystent refleksji AI — zawsze pod ręką.",
  keywords: [
    "Lectio Divina", "Różaniec", "Rachunek Sumienia", "Brewiarz",
    "modlitwa katolicka", "formacja duchowa", "AI", "Catholic app",
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
    <html lang="pl" className={`${cinzel.variable} ${crimsonText.variable} ${inter.variable}`}>
      <head>
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
          <main className="pt-16 pb-16 md:pb-0">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>

          <ToastContainer />

          {/* Mobile-only bottom navigation */}
          <BottomNav />

          {/* PWA / native app install prompt */}
          <InstallPrompt />

          <Footer />
        </body>
      </LiturgicalSeasonProvider>
    </html>
  );
}
