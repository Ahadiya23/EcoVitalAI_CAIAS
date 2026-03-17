import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../store/useAppStore";

export function LoginPage() {
  const navigate = useNavigate();
  const setUser = useAppStore((s) => s.setUser);
  const [email, setEmail] = useState("");

  return (
    <div className="mx-auto mt-20 max-w-md rounded-xl border bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <h1 className="text-xl font-semibold">Sign in</h1>
      <p className="mt-2 text-sm text-slate-500">Supabase magic-link flow placeholder for hackathon demo.</p>
      <input
        aria-label="Email"
        className="mt-4 w-full rounded border px-3 py-2"
        placeholder="you@ecovital.app"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <button
        className="mt-4 w-full rounded bg-emerald-600 px-4 py-2 text-white"
        onClick={() => {
          setUser({ id: "demo-user", email });
          navigate("/onboarding");
        }}
      >
        Send magic link
      </button>
    </div>
  );
}
