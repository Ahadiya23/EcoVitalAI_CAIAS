import { useQuery } from "@tanstack/react-query";
import apiClient from "../lib/apiClient";

export interface LocationAqi {
  aqi: number;
  category: string;
  dominant_pollutant: string;
  pm25: number;
  pm10: number;
  o3: number;
  no2: number;
  recommendation: string;
}

export function useLocationAqi(lat: number, lng: number) {
  return useQuery({
    queryKey: ["location-aqi", lat, lng],
    queryFn: async () => {
      const { data } = await apiClient.get("/api/location/aqi", { params: { lat, lng } });
      return data as LocationAqi;
    },
    enabled: Number.isFinite(lat) && Number.isFinite(lng),
  });
}
