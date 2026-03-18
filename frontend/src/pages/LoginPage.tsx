import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../store/useAppStore";

export function LoginPage() {
  const navigate = useNavigate();
  const setUser = useAppStore((s) => s.setUser);
  const [email, setEmail] = useState("");

  return (
    <div className="relative min-h-[calc(100vh-120px)] overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 text-white dark:border-slate-800">
      <div className="pointer-events-none absolute -left-16 -top-16 h-72 w-72 animate-pulse rounded-full bg-emerald-500/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-20 right-0 h-80 w-80 animate-pulse rounded-full bg-cyan-400/20 blur-3xl [animation-delay:300ms]" />
      <div className="relative grid min-h-[calc(100vh-120px)] gap-6 p-6 md:grid-cols-2 md:p-10">
        <section className="flex flex-col justify-center">
          <p className="mb-3 inline-flex w-fit rounded-full border border-emerald-300/40 bg-emerald-400/10 px-3 py-1 text-xs text-emerald-200">
            AI + Climate + Health Intelligence
          </p>
          <h1 className="text-4xl font-bold leading-tight md:text-5xl">
            EcoVital AI
          </h1>
          <p className="mt-4 max-w-xl text-slate-300">
            Predict personal health risk from AQI, weather, UV, and pollen in real time.
            Get proactive recommendations before symptoms escalate.
          </p>
          <div className="mt-6 grid max-w-lg gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-lg border border-white/15 bg-white/5 p-3 backdrop-blur">
              <p className="text-2xl font-semibold text-emerald-300">24h</p>
              <p className="text-slate-300">forecast horizon</p>
            </div>
            <div className="rounded-lg border border-white/15 bg-white/5 p-3 backdrop-blur">
              <p className="text-2xl font-semibold text-cyan-300">Live</p>
              <p className="text-slate-300">location AQI context</p>
            </div>
            <div className="rounded-lg border border-white/15 bg-white/5 p-3 backdrop-blur">
              <p className="text-2xl font-semibold text-amber-300">AI</p>
              <p className="text-slate-300">actionable guidance</p>
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center">
          <div className="w-full max-w-md rounded-2xl border border-white/20 bg-white/10 p-6 backdrop-blur-xl">
            <h2 className="text-2xl font-semibold">Sign in with magic link</h2>
            <p className="mt-2 text-sm text-slate-200">
              Enter your email to continue to your personalized climate-health dashboard.
            </p>
            <input
              aria-label="Email"
              className="mt-5 w-full rounded-lg border border-white/25 bg-slate-900/60 px-3 py-2 text-white placeholder:text-slate-400"
              placeholder="you@ecovital.app"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <button
              className="mt-4 w-full rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 px-4 py-2 font-medium text-white transition hover:scale-[1.01]"
              onClick={() => {
                setUser({ id: "demo-user", email });
                navigate("/onboarding");
              }}
            >
              Send magic link
            </button>
            <p className="mt-3 text-xs text-slate-300">
              Demo mode available: <span className="text-emerald-200">?demo=delhi</span> / <span className="text-emerald-200">?demo=mumbai</span>
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
