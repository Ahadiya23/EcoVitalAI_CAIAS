import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import apiClient from "../lib/apiClient";
import { useMapData } from "../hooks/useMapData";

export function MapPage() {
  const [bbox] = useState("12.8,77.5,13.1,77.7");
  const [showHeat, setShowHeat] = useState(true);
  const [showAQI, setShowAQI] = useState(true);
  const [severity, setSeverity] = useState("medium");
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const { data } = useMapData(bbox);

  const points = useMemo(() => data?.heat ?? [], [data]);
  useEffect(() => {
    // Placeholder for leaflet-heat overlay setup.
    void L;
  }, [points, showHeat]);

  const submitReport = async () => {
    const { data } = await apiClient.post("/api/map/report", { lat: 12.97, lng: 77.59, symptoms, severity });
    const aqi = data?.location_aqi?.aqi;
    const category = data?.location_aqi?.category?.replaceAll("_", " ");
    alert(`Report submitted. Thank you.\nNearby AQI: ${aqi} (${category}).`);
  };

  return (
    <div className="grid gap-4 md:grid-cols-[1fr_320px]">
      <div className="h-[75vh] overflow-hidden rounded-xl border">
        <MapContainer center={[12.9716, 77.5946]} zoom={11} className="h-full w-full">
          <TileLayer attribution="OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {showAQI &&
            points.slice(0, 50).map((point, idx) => (
              <CircleMarker key={idx} center={[point.lat, point.lng]} radius={5} pathOptions={{ color: point.intensity > 0.7 ? "red" : "orange" }} />
            ))}
        </MapContainer>
      </div>
      <aside className="rounded-xl border bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="font-semibold">Map Controls</h2>
        <label className="mt-2 flex justify-between"><span>Heatmap</span><input type="checkbox" checked={showHeat} onChange={(e) => setShowHeat(e.target.checked)} /></label>
        <label className="mt-2 flex justify-between"><span>AQI stations</span><input type="checkbox" checked={showAQI} onChange={(e) => setShowAQI(e.target.checked)} /></label>
        <button className="mt-3 rounded border px-3 py-2" onClick={() => navigator.geolocation.getCurrentPosition(() => undefined)}>Center on me</button>
        <hr className="my-4" />
        <h3 className="font-medium">Report Symptoms</h3>
        <div className="mt-2 space-y-2 text-sm">
          {["cough", "headache", "breathlessness", "fatigue"].map((s) => (
            <label key={s} className="flex items-center gap-2"><input type="checkbox" onChange={(e) => setSymptoms((prev) => e.target.checked ? [...prev, s] : prev.filter((x) => x !== s))} />{s}</label>
          ))}
        </div>
        <select className="mt-2 w-full rounded border px-2 py-1" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option>low</option>
          <option>medium</option>
          <option>high</option>
        </select>
        <button className="mt-3 w-full rounded bg-emerald-600 px-3 py-2 text-white" onClick={submitReport}>Submit</button>
      </aside>
    </div>
  );
}
