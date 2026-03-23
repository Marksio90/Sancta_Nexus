"use client";

import { useEffect } from "react";
import { getLiturgicalInfo } from "@/lib/liturgical-season";

/**
 * Sets data-season on <html> so CSS liturgical accent variables activate.
 * Must wrap <body> inside RootLayout so it runs client-side.
 */
export function LiturgicalSeasonProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    const info = getLiturgicalInfo();
    document.documentElement.setAttribute("data-season", info.season);
    // Also expose as CSS var for any direct usage
    document.documentElement.style.setProperty(
      "--color-liturgical-accent",
      info.color
    );
  }, []);

  return <>{children}</>;
}
