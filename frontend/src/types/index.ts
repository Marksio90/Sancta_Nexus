/** Lectio Divina stage identifiers */
export type LectioDivinaStage =
  | "welcome"
  | "lectio"
  | "meditatio"
  | "oratio"
  | "contemplatio"
  | "actio";

/** A single scripture passage */
export interface ScripturePassage {
  book: string;
  chapter: number;
  startVerse: number;
  endVerse: number;
  text: string;
  translation: string;
}

/** Lectio Divina session stored in the database */
export interface LectioDivinaSession {
  id: string;
  date: string;
  passage: ScripturePassage;
  emotion: string;
  meditationResponse: string;
  generatedPrayer: string;
  challenge: string;
  completedStages: LectioDivinaStage[];
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

/** Spiritual direction tradition */
export type SpiritualTradition =
  | "ignacjanska"
  | "karmelitanska"
  | "benedyktynska"
  | "franciszkanska";

/** Chat message in the spiritual director */
export interface ChatMessage {
  id: string;
  role: "user" | "director";
  content: string;
  timestamp: Date;
}

/** Dashboard session summary */
export interface SessionSummary {
  id: string;
  date: string;
  passage: string;
  emotion: string;
  keyInsight: string;
}

/** Recurring spiritual theme */
export interface SpiritualTheme {
  theme: string;
  count: number;
  trend: "up" | "down" | "stable";
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
}
