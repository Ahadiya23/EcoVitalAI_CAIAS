import { create } from "zustand";

type Severity = "low" | "medium" | "high" | "critical";

interface RiskState {
  overall_score: number;
  severity: Severity;
}

interface AppState {
  user: { id: string; email?: string } | null;
  profile: Record<string, unknown> | null;
  currentRisk: RiskState | null;
  isDemo: boolean;
  demoCity: "delhi" | "bangalore" | "mumbai" | null;
  setUser: (user: AppState["user"]) => void;
  setProfile: (profile: AppState["profile"]) => void;
  setCurrentRisk: (risk: RiskState) => void;
  setDemo: (city: AppState["demoCity"]) => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  profile: null,
  currentRisk: null,
  isDemo: false,
  demoCity: null,
  setUser: (user) => set({ user }),
  setProfile: (profile) => set({ profile }),
  setCurrentRisk: (currentRisk) => set({ currentRisk }),
  setDemo: (city) => set({ isDemo: !!city, demoCity: city })
}));
