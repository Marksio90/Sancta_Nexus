/**
 * Liturgical season calculation (Roman Rite).
 * Mirrors the Python implementation in backend/app/services/scripture/liturgical_calendar.py
 */

export type LiturgicalSeason =
  | "advent"
  | "christmas"
  | "lent"
  | "easter"
  | "ordinary";

export interface LiturgicalInfo {
  season: LiturgicalSeason;
  /** Liturgical color as hex */
  color: string;
  /** Human-readable season name (Polish) */
  label: string;
  /** Latin name */
  latin: string;
}

/** Anonymous Gregorian algorithm for Easter Sunday. */
function easterDate(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31); // 1-based
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day);
}

/** First Sunday of Advent (4th Sunday before Dec 25). */
function adventStart(year: number): Date {
  const christmas = new Date(year, 11, 25); // Dec 25
  // JS: 0=Sun, 1=Mon ... 6=Sat
  const dayOfWeek = christmas.getDay(); // 0=Sun
  // Days back to nearest Sunday on or before Christmas
  const daysToSunday = dayOfWeek; // Sun=0 means 0 days back
  const fourthSundayBefore = new Date(christmas);
  fourthSundayBefore.setDate(christmas.getDate() - daysToSunday - 21);
  return fourthSundayBefore;
}

/** Returns day-only Date (ignores time) for comparison. */
function dayOnly(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

export function getLiturgicalInfo(today: Date = new Date()): LiturgicalInfo {
  const year = today.getFullYear();
  const todayMs = dayOnly(today);

  // Easter and derived dates
  const easter = easterDate(year);
  const easterMs = dayOnly(easter);

  // Ash Wednesday = 46 days before Easter
  const ashWednesday = new Date(easter);
  ashWednesday.setDate(easter.getDate() - 46);
  const ashMs = dayOnly(ashWednesday);

  // Pentecost = 49 days after Easter
  const pentecost = new Date(easter);
  pentecost.setDate(easter.getDate() + 49);
  const pentecostMs = dayOnly(pentecost);

  // Advent for current year
  const advent = adventStart(year);
  const adventMs = dayOnly(advent);

  // Dec 25
  const christmasMs = dayOnly(new Date(year, 11, 25));

  // Baptism of the Lord ≈ Sunday after Jan 6 (approx Jan 13 for simplicity)
  const baptismMs = dayOnly(new Date(year, 0, 13));

  // Previous Advent (year-1) and Pentecost to handle Jan–early Feb
  const adventPrevMs = dayOnly(adventStart(year - 1));
  const christmasPrevMs = dayOnly(new Date(year - 1, 11, 25));
  const baptismPrevMs = dayOnly(new Date(year, 0, 13)); // same year Jan

  // ── Determine season ──────────────────────────────────────────────────────

  // Advent (current year): adventStart ≤ today < Dec 25
  if (todayMs >= adventMs && todayMs < christmasMs) {
    return { season: "advent", color: "#7b1fa2", label: "Adwent", latin: "Adventus" };
  }

  // Christmas: Dec 25 – Baptism of Lord (~Jan 13)
  const christmasEndMs = todayMs <= baptismMs && todayMs >= christmasMs
    ? baptismMs
    : dayOnly(new Date(year, 0, 13));

  if (
    todayMs >= christmasMs ||
    (todayMs >= christmasPrevMs && todayMs < baptismMs && todayMs < adventMs)
  ) {
    // Dec 25 of any year through ~Jan 13 next year
    if (todayMs >= christmasMs || todayMs < baptismMs) {
      return { season: "christmas", color: "#ffffff", label: "Boże Narodzenie", latin: "Nativitas" };
    }
  }

  // Lent: Ash Wednesday – Holy Thursday (eve of Easter)
  const holyThursdayMs = easterMs - 3 * 86400000;
  if (todayMs >= ashMs && todayMs < easterMs) {
    return { season: "lent", color: "#6a1b9a", label: "Wielki Post", latin: "Quadragesima" };
  }

  // Easter: Easter Sunday – Pentecost
  if (todayMs >= easterMs && todayMs <= pentecostMs) {
    return { season: "easter", color: "#D4AF37", label: "Wielkanoc", latin: "Paschalis" };
  }

  // Everything else = Ordinary Time
  return { season: "ordinary", color: "#4caf50", label: "Zwykły", latin: "Per Annum" };
}
