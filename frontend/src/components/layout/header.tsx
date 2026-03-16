"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Sparkles } from "lucide-react";

const NAV_LINKS = [
  { href: "/lectio-divina", label: "Lectio Divina" },
  { href: "/bible", label: "Biblia" },
  { href: "/spiritual-director", label: "Kierownik Duchowy" },
  { href: "/dashboard", label: "Dashboard" },
];

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  return (
    <header className="fixed top-0 z-50 w-full border-b border-[--color-sacred-border] bg-[--color-sacred-bg]/90 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        {/* Brand */}
        <Link
          href="/"
          className="flex items-center gap-2 text-[--color-gold] transition-opacity hover:opacity-80"
        >
          <Sparkles className="h-6 w-6" />
          <span className="font-heading text-xl tracking-wide">
            Sancta Nexus
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-[--color-gold]/10 text-[--color-gold]"
                    : "text-[--color-sacred-text-muted] hover:bg-[--color-sacred-surface] hover:text-[--color-parchment]"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="rounded-lg p-2 text-[--color-sacred-text-muted] transition-colors hover:text-[--color-gold] md:hidden"
          aria-label={mobileMenuOpen ? "Zamknij menu" : "Otwórz menu"}
        >
          {mobileMenuOpen ? (
            <X className="h-6 w-6" />
          ) : (
            <Menu className="h-6 w-6" />
          )}
        </button>
      </nav>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="border-t border-[--color-sacred-border] bg-[--color-sacred-bg] px-4 py-4 md:hidden">
          <div className="flex flex-col gap-1">
            {NAV_LINKS.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`rounded-lg px-4 py-3 text-sm font-medium transition-all ${
                    isActive
                      ? "bg-[--color-gold]/10 text-[--color-gold]"
                      : "text-[--color-sacred-text-muted] hover:bg-[--color-sacred-surface] hover:text-[--color-parchment]"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
}
