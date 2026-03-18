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

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
        />
        {/* Score arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-bold" style={{ color }}>
          {score}%
        </span>
        <span className="text-xs text-gray-400 mt-1">similarity</span>
      </div>
    </div>
  );
}
