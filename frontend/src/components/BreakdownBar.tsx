interface BreakdownBarProps {
  label: string;
  description: string;
  value: number | null; // 0-100 or null for N/A
}

function barColor(value: number): string {
  if (value >= 75) return "bg-green-500";
  if (value >= 50) return "bg-yellow-500";
  if (value >= 25) return "bg-orange-500";
  return "bg-red-500";
}

export default function BreakdownBar({ label, description, value }: BreakdownBarProps) {
  const isNA = value === null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-medium text-gray-200">{label}</span>
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
      <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
        {isNA ? (
          <div className="h-full rounded-full bg-gray-700/40 w-full" />
        ) : (
          <div
            className={`h-full rounded-full transition-all duration-1000 ease-out ${barColor(value)}`}
            style={{ width: `${value}%` }}
          />
        )}
      </div>
    </div>
  );
}
