/** Lectio Divina stage identifiers */
export type LectioDivinaStage =
  | "welcome"
  | "lectio"
  | "meditatio"
  | "oratio"
  | "contemplatio"
  | "actio";

/** A single scripture passage with patristic enrichment */
export interface ScripturePassage {
  book: string;
  bookAbbrev?: string;
  chapter: number;
  startVerse: number;
  endVerse: number;
  text: string;
  translation: string;
  historicalContext?: string;
  patristicNote?: string;
  originalLanguageKey?: string;
  catechismRef?: string;
}

/** Reflective question with Quadriga layer */
export interface ReflectiveQuestion {
  text: string;
  layer: "literalis" | "allegoricus" | "moralis" | "anagogicus";
  scriptureEcho?: string;
}

/** Meditation / Quadriga reflection layers */
export interface ReflectionLayers {
  literalis: string;
  allegoricus: string;
  moralis: string;
  anagogicus: string;
}

/** Full meditation output */
export interface MeditationResult {
  questions: ReflectiveQuestion[];
  reflectionLayers: ReflectionLayers;
  patristicInsight?: string;
  keyWord?: string;
}

/** Prayer output with tradition */
export interface PrayerResult {
  prayerText: string;
  tradition: string;
  elements: string[];
  spiritualMovement?: "consolation" | "desolation" | "peace";
}

/** Contemplation guidance */
export interface ContemplationResult {
  guidanceText: string;
  sacredWord?: string;
  sacredWordMeaning?: string;
  breathingPattern: {
    inhaleSeconds: number;
    holdSeconds: number;
    exhaleSeconds: number;
    cycles: number;
  };
  jesusPrayerRhythm?: string;
  durationMinutes: number;
  ambientSuggestion: string;
  closingPrayer?: string;
}

/** Evening examen structure */
export interface EveningExamen {
  retrospection: string;
  divinePresence: string;
  resolution: string;
}

/** Action / micro-quest output */
export interface ActionResult {
  challengeText: string;
  scriptureAnchor?: string;
  difficulty: "easy" | "medium" | "hard" | "divine";
  category: string;
  virtueFocus?: string;
  eveningExamen: EveningExamen;
}

/** Lectio Divina session stored in the database */
export interface LectioDivinaSession {
  id: string;
  date: string;
  passage: ScripturePassage;
  emotion: string;
  meditationResponse: string;
  meditation?: MeditationResult;
  prayer?: PrayerResult;
  contemplation?: ContemplationResult;
  action?: ActionResult;
  generatedPrayer: string;
  challenge: string;
  completedStages: LectioDivinaStage[];
  tradition?: string;
  kerygmaticTheme?: string;
  createdAt: Date;
}

/** Bible analysis dimensions */
export type BibleDimension =
  | "teologiczny"
  | "historyczny"
  | "psychologiczny"
  | "duchowy";

/** Response from the Bible analysis API */
export interface BibleAnalysisResponse {
  passage: ScripturePassage;
  analyses: Record<BibleDimension, string>;
}

/** Spiritual direction tradition — 7 traditions */
export type SpiritualTradition =
  | "ignacjanska"
  | "karmelitanska"
  | "benedyktynska"
  | "franciszkanska"
  | "charyzmatyczna"
  | "dominikanska"
  | "maryjna";

/** Chat message in the spiritual director */
export interface ChatMessage {
  id: string;
  role: "user" | "director";
  content: string;
  timestamp: Date;
  tradition?: SpiritualTradition;
}

/** Dashboard session summary */
export interface SessionSummary {
  id: string;
  date: string;
  passage: string;
  emotion: string;
  keyInsight: string;
  tradition?: string;
  kerygmaticTheme?: string;
}

/** Recurring spiritual theme */
export interface SpiritualTheme {
  theme: string;
  count: number;
  trend: "up" | "down" | "stable";
}

/** Kerygmatic journey pillar */
export interface KerygmaticPillar {
  theme: string;
  label: string;
  progress: number;
  sessionsCount: number;
}

/** Spiritual journey stage */
export interface JourneyStage {
  name: string;
  description: string;
  progress: number;
}

/** User's spiritual profile / dashboard data */
export interface SpiritualProfile {
  prayerStreak: number;
  totalSessions: number;
  currentState: string;
  recentSessions: SessionSummary[];
  themes: SpiritualTheme[];
  journeyStages: JourneyStage[];
  kerygmaticPillars?: KerygmaticPillar[];
  traditionsExplored?: string[];
  canonCoverage?: number; // percentage of 73 books encountered
}
