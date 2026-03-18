import { useQuery } from "@tanstack/react-query";
import apiClient from "../lib/apiClient";

export function useRiskScore(lat: number, lng: number, userId: string) {
  return useQuery({
    queryKey: ["risk", lat, lng, userId],
    queryFn: async () => {
      const { data } = await apiClient.get("/api/risk/current", {
        params: { lat, lng, user_id: userId }
      });
      return data as {
        overall_score: number;
        severity: "low" | "medium" | "high" | "critical";
        component_scores: Record<string, number>;
        explanation: string;
        risk_reasons?: string[];
        prevention_tips?: string[];
        user_context?: {
          age?: number;
          conditions?: string[];
        };
      };
    },
    enabled: Boolean(userId)
  });
}
