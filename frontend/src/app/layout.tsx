import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/layout/header";

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
          href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-sacred-bg text-sacred-text antialiased">
        <Header />
        <main className="pt-16">{children}</main>
      </body>
    </html>
  );
}
