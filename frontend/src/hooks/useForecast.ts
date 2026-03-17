import { useQuery } from "@tanstack/react-query";
import apiClient from "../lib/apiClient";

export function useForecast(lat: number, lng: number, userId: string) {
  return useQuery({
    queryKey: ["forecast", lat, lng, userId],
    queryFn: async () => {
      const { data } = await apiClient.get("/api/risk/forecast", {
        params: { lat, lng, user_id: userId }
      });
      return data as { hourly_scores: number[]; worst_hour: number; best_hour: number; peak_risk: number };
    },
    enabled: Boolean(userId)
  });
}
