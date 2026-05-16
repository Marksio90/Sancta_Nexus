/**
 * Lightweight i18n utility for Sancta Nexus.
 *
 * Does NOT require next-intl or i18next — uses plain TypeScript with
 * dot-notation key lookup and interpolation.
 *
 * Usage:
 *   import { useTranslation } from "@/lib/i18n";
 *   const { t } = useTranslation("en");
 *   t("home.hero.title")   // → "Prayer and Spiritual Formation"
 *   t("common.appName")    // → "Sancta Nexus"
 *
 * For server components, use getTranslation(locale) directly.
 */

export type Locale = "pl" | "en";

export const SUPPORTED_LOCALES: Locale[] = ["pl", "en"];
export const DEFAULT_LOCALE: Locale = "pl";

type TranslationDict = Record<string, unknown>;

// Translations are imported statically so no dynamic require is needed.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const MESSAGES: Record<Locale, TranslationDict> = {
  pl: require("../../messages/pl.json") as TranslationDict,
  en: require("../../messages/en.json") as TranslationDict,
};

function deepGet(obj: TranslationDict, path: string): string | undefined {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current == null || typeof current !== "object") return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === "string" ? current : undefined;
}

function interpolate(template: string, vars: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => vars[key] ?? `{${key}}`);
}

export function getTranslation(locale: Locale) {
  const messages = MESSAGES[locale] ?? MESSAGES[DEFAULT_LOCALE];

  function t(key: string, vars?: Record<string, string>): string {
    const value =
      deepGet(messages, key) ??
      deepGet(MESSAGES[DEFAULT_LOCALE], key) ??
      key;
    return vars ? interpolate(value, vars) : value;
  }

  return { t, locale };
}

/**
 * Detect locale from Accept-Language header value.
 * Returns the best matching supported locale or DEFAULT_LOCALE.
 */
export function detectLocale(acceptLanguage: string | null): Locale {
  if (!acceptLanguage) return DEFAULT_LOCALE;
  const langs = acceptLanguage
    .split(",")
    .map((s) => s.split(";")[0].trim().toLowerCase().slice(0, 2));
  for (const lang of langs) {
    if (SUPPORTED_LOCALES.includes(lang as Locale)) return lang as Locale;
  }
  return DEFAULT_LOCALE;
}

/**
 * React hook for client components (reads locale from path or localStorage).
 */
export function useTranslation(locale: Locale = DEFAULT_LOCALE) {
  return getTranslation(locale);
}
