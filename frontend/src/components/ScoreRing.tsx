import { useState, useEffect, useId } from "react";

interface ScoreRingProps {
  score: number; // 0-100
  size?: number;
  strokeWidth?: number;
}

function scoreColor(score: number): string {
  if (score >= 75) return "#22c55e"; // green
  if (score >= 50) return "#eab308"; // yellow
  if (score >= 25) return "#f97316"; // orange
  return "#ef4444"; // red
}

export default function ScoreRing({ score, size = 180, strokeWidth = 10 }: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = scoreColor(score);
  const gradientId = useId();

  // Animated count-up
  const [displayScore, setDisplayScore] = useState(0);
  useEffect(() => {
    let frame: number;
    let start: number | null = null;
    const duration = 1000;
    const animate = (ts: number) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplayScore(Math.round(eased * score));
      if (p < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [score]);

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#a855f7" />
            <stop offset="50%" stopColor="#ec4899" />
            <stop offset="100%" stopColor={color} />
          </linearGradient>
        </defs>

        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
        />

        {/* Glow arc (blurred behind) */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth + 8}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out blur-md opacity-30"
        />

        {/* Score arc (gradient) */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-bold font-display" style={{ color }}>
          {displayScore}%
        </span>
        <span className="text-xs text-gray-400 mt-1 font-display tracking-wider uppercase">similarity</span>
      </div>
    </div>
  );
}
