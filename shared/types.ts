export type Severity = "low" | "medium" | "high" | "critical";

export interface RiskPrediction {
  overall_score: number;
  component_scores: {
    asthma_risk: number;
    heat_risk: number;
    allergy_risk: number;
    cardiac_risk: number;
  };
  severity: Severity;
  confidence: number;
  anomaly_flag: boolean;
  explanation: string;
}

export interface EnvironmentalSnapshot {
  lat: number;
  lng: number;
  timestamp: string;
  climate: {
    temp_celsius: number;
    humidity_pct: number;
    wind_speed: number;
    weather_description: string;
    feels_like: number;
  };
  aqi: {
    aqi_score: number;
    pm25: number;
    pm10: number;
    o3: number;
    no2: number;
    dominant_pollutant: string;
  };
  uv: {
    uv_index: number;
    uv_max: number;
    uv_max_time: string;
    uv_risk_level: string;
  };
  pollen: {
    tree_pollen: number;
    grass_pollen: number;
    weed_pollen: number;
    risk_level: string;
  };
}
