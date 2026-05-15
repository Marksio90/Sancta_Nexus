import Link from "next/link";

export function Footer() {
  return (
    <footer className="hidden md:block border-t border-white/10 bg-sacred-bg/80 text-xs text-sacred-text/40 py-4">
      <div className="max-w-5xl mx-auto px-6 flex flex-wrap items-center justify-between gap-2">
        <span>© {new Date().getFullYear()} Sancta Nexus</span>
        <div className="flex gap-4">
          <Link href="/polityka-prywatnosci" className="hover:text-sacred-gold transition-colors">
            Polityka prywatności
          </Link>
          <Link href="/regulamin" className="hover:text-sacred-gold transition-colors">
            Regulamin
          </Link>
          <a
            href="mailto:kontakt@sanctanexus.org"
            className="hover:text-sacred-gold transition-colors"
          >
            Kontakt
          </a>
        </div>
      </div>
    </footer>
  );
}
