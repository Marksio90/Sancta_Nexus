"use client";

/**
 * BottomNav — mobile-first bottom navigation bar.
 *
 * Visible only on small screens (hidden on md+).
 * Accounts for iOS safe-area (notch / home indicator) via env(safe-area-inset-bottom).
 *
 * 5 primary destinations matching Hallow's UX pattern:
 *   Home · Lectio · Director · Breviary · Bible
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, BookOpen, MessageCircle, Clock, Cross } from "lucide-react";
import { haptic } from "@/lib/haptics";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  activeIcon?: React.ReactNode;
  matchPrefix?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "Główna",
    icon: <Home className="h-5 w-5" />,
    matchPrefix: false,
  },
  {
    href: "/lectio-divina",
    label: "Lectio",
    icon: <BookOpen className="h-5 w-5" />,
    matchPrefix: true,
  },
  {
    href: "/spiritual-director",
    label: "Kierownik",
    icon: <MessageCircle className="h-5 w-5" />,
    matchPrefix: true,
  },
  {
    href: "/breviary",
    label: "Brewiarz",
    icon: <Clock className="h-5 w-5" />,
    matchPrefix: true,
  },
  {
    href: "/przygotowanie",
    label: "Sakramenty",
    icon: <Cross className="h-5 w-5" />,
    matchPrefix: true,
  },
];

export function BottomNav() {
  const pathname = usePathname();

  function isActive(item: NavItem): boolean {
    if (item.matchPrefix === false) return pathname === item.href;
    return pathname === item.href || pathname.startsWith(item.href + "/");
  }

  return (
    <nav
      className="
        fixed bottom-0 left-0 right-0 z-50
        block md:hidden
        border-t border-[--color-sacred-border]
        bg-[--color-sacred-bg]/95 backdrop-blur-md
      "
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      aria-label="Nawigacja mobilna"
    >
      <div className="flex items-center justify-around px-1 py-2">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => haptic.light()}
              aria-label={item.label}
              aria-current={active ? "page" : undefined}
              className={`
                flex min-w-0 flex-1 flex-col items-center gap-0.5 rounded-xl px-1 py-1.5
                transition-all duration-150
                ${
                  active
                    ? "text-[--color-gold]"
                    : "text-[--color-sacred-text-muted]/50 hover:text-[--color-sacred-text-muted]"
                }
              `}
            >
              {/* Active indicator dot */}
              <div className="relative">
                {item.activeIcon && active ? item.activeIcon : item.icon}
                {active && (
                  <span className="absolute -bottom-1 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-[--color-gold]" />
                )}
              </div>
              <span
                className={`truncate text-[10px] font-medium leading-none ${
                  active ? "text-[--color-gold]" : ""
                }`}
              >
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
