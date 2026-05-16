/**
 * Next.js middleware for locale detection and i18n routing.
 *
 * Routes:
 *   /en/*   → English version (served at /en/)
 *   /*      → Polish (default locale, no prefix)
 *
 * The middleware does NOT redirect for the default locale (pl).
 * English users who visit / see Polish — they can navigate to /en/
 * via the language switcher. Auto-redirect based on Accept-Language
 * is intentionally disabled to avoid SEO canonicalization issues.
 */

import { NextRequest, NextResponse } from "next/server";
import { type Locale, SUPPORTED_LOCALES } from "@/lib/i18n";

const PUBLIC_FILE = /\.(.*)$/;

function getPathnameLocale(pathname: string): Locale | null {
  const segment = pathname.split("/")[1];
  if (SUPPORTED_LOCALES.includes(segment as Locale) && segment !== "pl") {
    return segment as Locale;
  }
  return null;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip static files, API routes, and Next.js internals
  if (
    PUBLIC_FILE.test(pathname) ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname === "/favicon.ico" ||
    pathname === "/manifest.json" ||
    pathname === "/robots.txt" ||
    pathname === "/sitemap.xml"
  ) {
    return NextResponse.next();
  }

  // Locale is embedded in path (/en/...) — just pass through
  const locale = getPathnameLocale(pathname);
  if (locale) {
    const response = NextResponse.next();
    response.headers.set("x-locale", locale);
    return response;
  }

  // Default locale (pl) — no redirect, just mark the header
  const response = NextResponse.next();
  response.headers.set("x-locale", "pl");
  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|icons|manifest.json).*)",
  ],
};
