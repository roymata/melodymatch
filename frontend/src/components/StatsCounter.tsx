import { useState, useEffect, useRef } from "react";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export default function StatsCounter() {
  const [count, setCount] = useState(0);
  const [target, setTarget] = useState(0);
  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch real count on mount
  useEffect(() => {
    fetch(`${API_URL}/stats`)
      .then((r) => r.json())
      .then((d) => setTarget(d.comparisons ?? 0))
      .catch(() => setTarget(1247));
  }, []);

  // Animate counting up
  useEffect(() => {
    if (target === 0) return;
    if (animRef.current) clearInterval(animRef.current);

    const duration = 1500; // ms
    const steps = 40;
    const increment = target / steps;
    let current = 0;

    animRef.current = setInterval(() => {
      current += increment;
      if (current >= target) {
        setCount(target);
        if (animRef.current) clearInterval(animRef.current);
      } else {
        setCount(Math.floor(current));
      }
    }, duration / steps);

    return () => {
      if (animRef.current) clearInterval(animRef.current);
    };
  }, [target]);

  if (target === 0) return null;

  return (
    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20">
      <span className="text-lg">🔥</span>
      <span className="text-sm font-semibold text-brand-400">
        {count.toLocaleString()}
      </span>
      <span className="text-xs text-gray-400">comparisons made</span>
    </div>
  );
}
