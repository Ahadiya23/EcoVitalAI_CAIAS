import { useCallback, useEffect, useMemo } from "react";
import { Area, AreaChart, Line, LineChart, RadialBar, RadialBarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DemoBanner } from "../components/DemoBanner";
import { ImpactBanner } from "../components/ImpactBanner";
import { ShareCard } from "../components/ShareCard";
import { useForecast } from "../hooks/useForecast";
import { useRiskScore } from "../hooks/useRiskScore";
import { useWebSocket } from "../hooks/useWebSocket";
import { useAppStore } from "../store/useAppStore";

function severityColor(score: number) {
  if (score >= 80) return "#dc2626";
  if (score >= 60) return "#f97316";
  if (score >= 30) return "#f59e0b";
  return "#16a34a";
}

export function DashboardPage() {
  const user = useAppStore((s) => s.user);
  const demoCity = useAppStore((s) => s.demoCity);
  const isDemo = useAppStore((s) => s.isDemo);
  const setCurrentRisk = useAppStore((s) => s.setCurrentRisk);
  const demoCoordinates = demoCity === "delhi" ? [28.6139, 77.209] : demoCity === "mumbai" ? [19.076, 72.8777] : [12.9716, 77.5946];
  const lat = demoCoordinates[0];
  const lng = demoCoordinates[1];
  const userId = user?.id ?? "demo-user";

  const risk = useRiskScore(lat, lng, userId);
  const forecast = useForecast(lat, lng, userId);

  const onSocketMessage = useCallback((message: any) => setCurrentRisk(message), [setCurrentRisk]);
  useWebSocket<any>(`ws://localhost:8000/ws/risk-feed/${userId}`, onSocketMessage);
  useEffect(() => {
    if (risk.data) setCurrentRisk({ overall_score: risk.data.overall_score, severity: risk.data.severity });
  }, [risk.data, setCurrentRisk]);

  const forecastData = useMemo(
    () => (forecast.data?.hourly_scores ?? []).map((value, i) => ({ hour: `${String(i).padStart(2, "0")}:00`, value })),
    [forecast.data]
  );
  const score = risk.data?.overall_score ?? 0;
  const color = severityColor(score);

  return (
    <div className="space-y-4">
      {isDemo && demoCity && <DemoBanner city={demoCity} />}
      <div className="grid gap-4 md:grid-cols-12">
        <section className="rounded-xl border bg-white p-4 md:col-span-3 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-sm font-semibold">Current Risk</h2>
          <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={score}>
            <ResponsiveContainer width="100%" height={220}>
              <RadialBarChart data={[{ name: "risk", value: score, fill: color }]} innerRadius="70%" outerRadius="100%" startAngle={180} endAngle={0}>
                <RadialBar minAngle={15} clockWise dataKey="value" />
                <Tooltip />
              </RadialBarChart>
            </ResponsiveContainer>
          </div>
          <div className={`text-center text-4xl font-bold ${score >= 80 ? "animate-pulse" : ""}`}>{Math.round(score)}</div>
          <p className="text-center capitalize">{risk.data?.severity ?? "low"}</p>
          <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
            {Object.entries(risk.data?.component_scores ?? {}).map(([k, v]) => (
              <div key={k} className="rounded border p-2">
                <p>{k}</p>
                <p>{Math.round(v * 100)}%</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border bg-white p-4 md:col-span-6 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-sm font-semibold">24H Forecast</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={forecastData}>
              <XAxis dataKey="hour" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke={color} strokeWidth={3} dot />
            </LineChart>
          </ResponsiveContainer>
          <h3 className="mt-4 text-sm font-semibold">7-Day Trend</h3>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={forecastData}>
              <XAxis dataKey="hour" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Area type="monotone" dataKey="value" stroke={color} fill={color} fillOpacity={0.2} />
            </AreaChart>
          </ResponsiveContainer>
        </section>

        <section className="space-y-3 rounded-xl border bg-white p-4 md:col-span-3 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="font-semibold">Today's health outlook</h2>
          <p className="text-sm">{risk.data?.explanation ?? "Loading AI summary..."}</p>
          <ShareCard score={score} severity={risk.data?.severity ?? "low"} topRiskFactor="Air quality" />
        </section>
      </div>
      <ImpactBanner reportCount={2834} hoursAhead={24} />
    </div>
  );
}
