import { useState, useEffect, useRef } from "react";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export default function StatsCounter() {
  const [count, setCount] = useState(0);
  const [target, setTarget] = useState(0);
  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/stats`)
      .then((r) => r.json())
      .then((d) => setTarget(d.comparisons ?? 0))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (target === 0) return;
    if (animRef.current) clearInterval(animRef.current);

    const duration = 1500;
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
    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
                    bg-white/[0.04] backdrop-blur-sm border border-accent-purple/20">
      <span className="text-lg">🔥</span>
      <span className="text-sm font-semibold font-display bg-gradient-to-r from-accent-purple to-accent-pink bg-clip-text text-transparent">
        {count.toLocaleString()}
      </span>
      <span className="text-xs text-gray-400">comparisons made</span>
    </div>
  );
}
