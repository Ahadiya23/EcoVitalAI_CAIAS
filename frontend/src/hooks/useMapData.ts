import { useQuery } from "@tanstack/react-query";
import apiClient from "../lib/apiClient";

export function useMapData(bbox: string) {
  return useQuery({
    queryKey: ["map", bbox],
    queryFn: async () => {
      const { data } = await apiClient.get("/api/map/heatmap", { params: { bbox } });
      return data as { heat: { lat: number; lng: number; intensity: number }[] };
    },
    enabled: Boolean(bbox)
  });
}
