"use client";

import { create } from "zustand";

export interface JourneyData {
  current_stage: string;
  stage_name_pl: string;
  stage_description: string;
  progress_percentage: number;
  milestones: string[];
  next_growth_area: string;
}

export interface PatternData {
  type: string;
  description: string;
  frequency?: string;
  related_scriptures?: string[];
}

export interface InsightsData {
  journey: JourneyData;
  patterns: PatternData[];
  entry_count: number;
  generated_at: string;
  disclaimer: string;
  ai_enabled: boolean;
}

interface InsightsState {
  data: InsightsData | null;
  loading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
}

const PATTERN_TYPE_LABELS: Record<string, string> = {
  recurring_theme: "Powtarzający się temat",
  cyclical_crisis: "Cyklyczny kryzys",
  grace_moment: "Moment łaski",
  growth_trajectory: "Trajektoria wzrostu",
  scripture_affinity: "Ulubione fragmenty Pisma",
  emotional_pattern: "Wzór emocjonalny",
};

export const PATTERN_LABELS = PATTERN_TYPE_LABELS;

export const useInsightsStore = create<InsightsState>((set) => ({
  data: null,
  loading: false,
  error: null,

  fetch: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch("/api/v1/journal/insights", {
        credentials: "include",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: InsightsData = await res.json();
      set({ data, loading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Błąd pobierania analizy", loading: false });
    }
  },
}));
