import { toBlob } from "html-to-image";
import { useRef } from "react";

interface Props {
  score: number;
  severity: string;
  topRiskFactor: string;
  aqiSummary?: string;
  age?: number;
  symptoms?: string[];
  reasons?: string[];
  preventionTips?: string[];
}

export function ShareCard({
  score,
  severity,
  topRiskFactor,
  aqiSummary = "AQI data pending",
  age,
  symptoms = [],
  reasons = [],
  preventionTips = [],
}: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const onShare = async () => {
    if (!ref.current) return;
    const blob = await toBlob(ref.current, { width: 1200, height: 630, cacheBust: true });
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ecovital-report.png";
    link.click();
    URL.revokeObjectURL(url);
    await navigator.clipboard.writeText(window.location.href);
  };

  return (
    <div>
      <div ref={ref} className="rounded-xl border bg-white p-6 text-slate-900">
        <h3 className="text-2xl font-bold text-emerald-700">EcoVital AI</h3>
        <p className="mt-3 text-6xl font-semibold">{Math.round(score)}</p>
        <p className="mt-1 text-xl capitalize">{severity}</p>
        <p className="mt-3 text-sm">Top factor: {topRiskFactor}</p>
        <p className="mt-1 text-sm">Location AQI: {aqiSummary}</p>
        <p className="mt-1 text-sm">Age: {age ?? "N/A"}</p>
        <p className="mt-1 text-sm">Symptoms/conditions: {symptoms.length ? symptoms.join(", ") : "Not provided"}</p>
        <p className="mt-2 text-xs font-semibold text-slate-700">Why this score</p>
        <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-700">
          {(reasons.length ? reasons : ["Risk reasons loading..."]).slice(0, 3).map((reason, idx) => (
            <li key={idx}>{reason}</li>
          ))}
        </ul>
        <p className="mt-2 text-xs font-semibold text-slate-700">How to reduce risk</p>
        <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-700">
          {(preventionTips.length ? preventionTips : ["Prevention guidance loading..."]).slice(0, 3).map((tip, idx) => (
            <li key={idx}>{tip}</li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-slate-600">{new Date().toDateString()}</p>
        <p className="mt-1 text-sm">Climate-aware personal health intelligence.</p>
      </div>
      <button aria-label="Share as image" className="mt-2 rounded bg-emerald-600 px-3 py-2 text-sm text-white" onClick={onShare}>
        Share Risk Report
      </button>
    </div>
  );
}
