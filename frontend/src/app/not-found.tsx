import Link from "next/link";
import { BookOpen, Search, Home } from "lucide-react";

const SUGGESTIONS = [
  { href: "/lectio-divina", label: "Lectio Divina", Icon: BookOpen },
  { href: "/bible", label: "Szukaj w Biblii", Icon: Search },
  { href: "/breviary", label: "Brewiarz", Icon: BookOpen },
];

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-6 text-center">
      <div className="max-w-lg">
        {/* Cross ornament */}
        <div className="mx-auto mb-8 flex h-24 w-24 items-center justify-center rounded-full border border-[--color-gold]/20 bg-[--color-gold]/5">
          <span className="font-heading text-4xl text-[--color-gold]/40">404</span>
        </div>

        <p className="mb-2 text-xs tracking-[0.4em] uppercase text-[--color-gold]/40">
          Nie znaleziono strony
        </p>
        <h1 className="font-heading mb-4 text-3xl text-[--color-gold]">
          Ta ścieżka nie istnieje
        </h1>

        <div className="sacred-divider mx-auto mb-6 w-32" />

        <p className="mb-10 leading-relaxed text-[--color-sacred-text-muted]/70">
          Strona, której szukasz, nie istnieje lub została przeniesiona.
          Może jedna z poniższych dróg Cię poprowadzi?
        </p>

        {/* Quick links */}
        <div className="mb-10 grid gap-3 sm:grid-cols-3">
          {SUGGESTIONS.map(({ href, label, Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex flex-col items-center gap-2 rounded-xl border border-[--color-sacred-border] bg-[--color-sacred-surface] px-4 py-5 text-sm text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/30 hover:text-[--color-gold]"
            >
              <Icon className="h-5 w-5" />
              {label}
            </Link>
          ))}
        </div>

        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-xl border border-[--color-gold]/40 bg-[--color-gold]/10 px-8 py-3 text-sm font-medium text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
        >
          <Home className="h-4 w-4" />
          Wróć na stronę główną
        </Link>

        <p className="mt-10 font-scripture text-sm italic text-[--color-sacred-text-muted]/30">
          &ldquo;Szukajcie, a znajdziecie&rdquo; — Mt 7,7
        </p>
      </div>
    </div>
  );
}
