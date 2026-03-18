import type { ComparisonResult } from "../types";
import ScoreRing from "./ScoreRing";
import BreakdownBar from "./BreakdownBar";

interface ResultsPanelProps {
  result: ComparisonResult;
  songAName: string;
  songBName: string;
  onReset: () => void;
}

const BREAKDOWN_META: Record<string, { label: string; description: string }> = {
  rhythm: { label: "Rhythm", description: "Beat patterns & groove" },
  tempo: { label: "Tempo", description: "BPM comparison" },
  timbre: { label: "Timbre", description: "Tonal quality & texture" },
  harmony: { label: "Harmony", description: "Pitch & chord content" },
};

export default function ResultsPanel({ result, songAName, songBName, onReset }: ResultsPanelProps) {
  const { overall, breakdown, details } = result;

  return (
    <div className="animate-fadeIn space-y-8">
      {/* Overall score */}
      <div className="flex flex-col items-center">
        <ScoreRing score={overall} />

        {/* Song details */}
        <div className="mt-6 grid grid-cols-2 gap-8 text-center text-sm">
          <div>
            <p className="text-gray-400 text-xs mb-1">Song A</p>
            <p className="font-medium text-gray-200 truncate max-w-[160px]">{songAName}</p>
            <p className="text-xs text-gray-500 mt-1">{details.song_a.tempo_bpm} BPM</p>
          </div>
          <div>
            <p className="text-gray-400 text-xs mb-1">Song B</p>
            <p className="font-medium text-gray-200 truncate max-w-[160px]">{songBName}</p>
            <p className="text-xs text-gray-500 mt-1">{details.song_b.tempo_bpm} BPM</p>
          </div>
        </div>
      </div>

      {/* Breakdown */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-200">Breakdown</h3>
        {Object.entries(breakdown).map(([key, value]) => {
          const meta = BREAKDOWN_META[key];
          if (!meta) return null;
          return (
            <BreakdownBar
              key={key}
              label={meta.label}
              description={meta.description}
              value={value}
            />
          );
        })}
      </div>

      {/* CTA */}
      <div className="flex justify-center pt-4">
        <button
          onClick={onReset}
          className="px-6 py-2.5 rounded-xl bg-gray-800 text-gray-300 text-sm font-medium
                     hover:bg-gray-700 transition-colors"
        >
          Compare Another Pair
        </button>
      </div>
    </div>
  );
}
