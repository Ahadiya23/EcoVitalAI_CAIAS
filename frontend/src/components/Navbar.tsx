import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAppStore } from "../store/useAppStore";

export function Navbar() {
  const risk = useAppStore((s) => s.currentRisk);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(prefersDark);
    document.documentElement.classList.toggle("dark", prefersDark);
  }, []);

  const toggleDark = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
  };

  const badgeColor =
    !risk ? "bg-slate-300" : risk.severity === "critical" ? "bg-red-600" : risk.severity === "high" ? "bg-orange-500 animate-pulse" : risk.severity === "medium" ? "bg-amber-500" : "bg-emerald-600";

  return (
    <nav className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <Link to="/" className="font-semibold text-emerald-600">EcoVital AI</Link>
        <div className="flex gap-4 text-sm">
          <Link to="/">Dashboard</Link>
          <Link to="/map">Map</Link>
          <Link to="/chat">Chat</Link>
        </div>
        <div className="flex items-center gap-2">
          <button aria-label="Toggle dark mode" className="rounded border px-2 py-1 text-xs" onClick={toggleDark}>
            {dark ? "Light" : "Dark"}
          </button>
          <div className={`rounded-full px-3 py-1 text-xs font-semibold text-white ${badgeColor}`}>
            {risk ? `${Math.round(risk.overall_score)} · ${risk.severity}` : "No data"}
          </div>
        </div>
      </div>
    </nav>
  );
}
