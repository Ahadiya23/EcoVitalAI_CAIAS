import { useEffect, useState } from "react";

export function ImpactBanner({ reportCount, hoursAhead }: { reportCount: number; hoursAhead: number }) {
  const [animatedCount, setAnimatedCount] = useState(0);
  useEffect(() => {
    const start = performance.now();
    const duration = 1500;
    const tick = (ts: number) => {
      const progress = Math.min(1, (ts - start) / duration);
      setAnimatedCount(Math.round(reportCount * progress));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [reportCount]);

  return (
    <section className="mt-4 rounded-xl border bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="grid gap-3 md:grid-cols-4">
        <p><strong>7 million deaths/year</strong><br />air pollution</p>
        <p><strong>250,000 additional deaths by 2030</strong><br />climate impacts</p>
        <p><strong>{animatedCount} community reports this week</strong><br />live from DB</p>
        <p><strong>Your risk predicted {hoursAhead} hours in advance</strong><br />forecast lead time</p>
      </div>
      <p className="mt-2 text-xs text-slate-500">Source: WHO Global Health Observatory</p>
    </section>
  );
}
