interface BreakdownBarProps {
  label: string;
  description: string;
  value: number | null; // 0-100 or null for N/A
}

function barGradient(value: number): string {
  if (value >= 75) return "bg-gradient-to-r from-brand-500 to-emerald-400";
  if (value >= 50) return "bg-gradient-to-r from-yellow-500 to-amber-400";
  if (value >= 25) return "bg-gradient-to-r from-orange-500 to-amber-500";
  return "bg-gradient-to-r from-red-500 to-rose-400";
}

export default function BreakdownBar({ label, description, value }: BreakdownBarProps) {
  const isNA = value === null;

  return (
    <div className="space-y-1.5 group cursor-default">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-semibold text-gray-200 font-display">{label}</span>
          <span className="ml-2 text-xs text-gray-500">{description}</span>
        </div>
        {isNA ? (
          <span className="text-xs font-medium text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
            N/A
          </span>
        ) : (
          <span className="text-sm font-semibold text-gray-300">{value}%</span>
        )}
      </div>
      <div className="h-2.5 rounded-full bg-gray-800/80 overflow-hidden group-hover:bg-gray-700/80 transition-colors">
        {isNA ? (
          <div className="h-full rounded-full bg-gray-700/40 w-full" />
        ) : (
          <div
            className={`h-full rounded-full transition-all duration-1000 ease-out ${barGradient(value)}
              ${value >= 75 ? "shadow-[0_0_8px_rgba(34,197,94,0.4)]" : ""}`}
            style={{ width: `${value}%` }}
          />
        )}
      </div>
    </div>
  );
}
