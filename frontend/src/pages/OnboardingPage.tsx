import { useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../lib/apiClient";
import { useAppStore } from "../store/useAppStore";

export function OnboardingPage() {
  const navigate = useNavigate();
  const user = useAppStore((s) => s.user);
  const [step, setStep] = useState(1);
  const [lat, setLat] = useState(12.9716);
  const [lng, setLng] = useState(77.5946);
  const [age, setAge] = useState(30);
  const [conditions, setConditions] = useState<string[]>([]);
  const [medications, setMedications] = useState("");
  const [threshold, setThreshold] = useState(60);
  const [push, setPush] = useState(false);
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  const toggleCondition = (condition: string) =>
    setConditions((prev) => (prev.includes(condition) ? prev.filter((c) => c !== condition) : [...prev, condition]));

  const submit = async () => {
    if (!user) return;
    await apiClient.put(`/api/profile/${user.id}`, {
      conditions,
      age,
      location_lat: lat,
      location_lng: lng,
      medications: medications ? medications.split(",").map((m) => m.trim()) : []
    });
    await apiClient.post("/api/alerts/subscribe", {
      user_id: user.id,
      threshold,
      push_token: push ? "browser-push-token" : "",
      phone,
      email
    });
    navigate("/");
  };

  return (
    <div className="mx-auto max-w-3xl rounded-xl border bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4 h-2 rounded bg-slate-200">
        <div className="h-full rounded bg-emerald-600 transition-all" style={{ width: `${(step / 3) * 100}%` }} />
      </div>
      <p className="mb-4 text-sm text-slate-500">{step}/3</p>

      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Step 1 - Location</h2>
          <button
            className="rounded border px-3 py-2"
            onClick={() =>
              navigator.geolocation.getCurrentPosition((pos) => {
                setLat(pos.coords.latitude);
                setLng(pos.coords.longitude);
              })
            }
          >
            Allow location
          </button>
          <div className="grid gap-3 md:grid-cols-2">
            <input className="rounded border px-3 py-2" value={lat} onChange={(e) => setLat(Number(e.target.value))} />
            <input className="rounded border px-3 py-2" value={lng} onChange={(e) => setLng(Number(e.target.value))} />
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Step 2 - Health Profile</h2>
          <div className="grid gap-2 md:grid-cols-2">
            {["Asthma", "Heart disease", "Seasonal allergies", "COPD", "Diabetes", "None of the above"].map((c) => (
              <label key={c} className="flex items-center gap-2 rounded border p-2">
                <input type="checkbox" checked={conditions.includes(c)} onChange={() => toggleCondition(c)} />
                {c}
              </label>
            ))}
          </div>
          <input className="w-full rounded border px-3 py-2" type="number" min={5} max={90} value={age} onChange={(e) => setAge(Number(e.target.value))} />
          <textarea className="w-full rounded border px-3 py-2" placeholder="Medications (optional)" value={medications} onChange={(e) => setMedications(e.target.value)} />
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Step 3 - Notifications</h2>
          <label className="flex items-center justify-between rounded border p-3">
            Push notifications
            <input type="checkbox" checked={push} onChange={(e) => setPush(e.target.checked)} />
          </label>
          <input className="w-full rounded border px-3 py-2" placeholder="Phone number" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <input className="w-full rounded border px-3 py-2" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <label className="block text-sm">Alert me when risk exceeds {threshold}/100</label>
          <input className="w-full" type="range" min={0} max={100} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
        </div>
      )}

      <div className="mt-6 flex justify-between">
        <button className="rounded border px-3 py-2" disabled={step === 1} onClick={() => setStep((s) => Math.max(1, s - 1))}>Back</button>
        {step < 3 ? (
          <button className="rounded bg-emerald-600 px-3 py-2 text-white" onClick={() => setStep((s) => Math.min(3, s + 1))}>Next</button>
        ) : (
          <button className="rounded bg-emerald-600 px-3 py-2 text-white" onClick={submit}>Finish</button>
        )}
      </div>
    </div>
  );
}
