import { useState } from "react";
import type { ComparisonResult } from "../types";
import ScoreRing from "./ScoreRing";
import BreakdownBar from "./BreakdownBar";
import { shareResults } from "../utils/shareCard";

interface ResultsPanelProps {
  result: ComparisonResult;
  songAName: string;
  songBName: string;
  songAArt?: string;
  songBArt?: string;
  onReset: () => void;
}

const BREAKDOWN_META: Record<string, { label: string; description: string }> = {
  rhythm: { label: "Rhythm", description: "Beat patterns & groove" },
  tempo: { label: "Tempo", description: "BPM comparison" },
  timbre: { label: "Timbre", description: "Tonal quality & texture" },
  harmony: { label: "Harmony", description: "Pitch & chord content" },
  lyrics: { label: "Lyrics", description: "Word similarity" },
};

function AlbumArt({ src }: { src?: string }) {
  if (src) {
    return <img src={src} alt="" className="w-20 h-20 rounded-lg shadow-lg mb-2" />;
  }
  return (
    <div className="w-20 h-20 rounded-lg bg-gray-800 mb-2 flex items-center justify-center text-gray-600">
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="m9 9 10.5-3m0 6.553v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 1 1-.99-3.467l2.31-.66a2.25 2.25 0 0 0 1.632-2.163Zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 0 1-.99-3.467l2.31-.66A2.25 2.25 0 0 0 9 15.553Z" />
      </svg>
    </div>
  );
}

function ShareButton({
  result,
  songAName,
  songBName,
}: {
  result: ComparisonResult;
  songAName: string;
  songBName: string;
}) {
  const [sharing, setSharing] = useState(false);
  const [done, setDone] = useState(false);

  const handleShare = async () => {
    setSharing(true);
    try {
      await shareResults(result, songAName, songBName);
      setDone(true);
      setTimeout(() => setDone(false), 2000);
    } catch {
      // silently ignore
    } finally {
      setSharing(false);
    }
  };

  return (
    <button
      onClick={handleShare}
      disabled={sharing}
      className="px-5 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-medium
                 hover:bg-brand-500 transition-colors disabled:opacity-50 flex items-center gap-2"
    >
      {done ? (
        <>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          Saved!
        </>
      ) : sharing ? (
        "Generating..."
      ) : (
        <>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z" />
          </svg>
          Share
        </>
      )}
    </button>
  );
}

export default function ResultsPanel({
  result, songAName, songBName, songAArt, songBArt, onReset,
}: ResultsPanelProps) {
  const { overall, breakdown, details } = result;

  return (
    <div className="animate-fadeIn space-y-8">
      {/* Overall score */}
      <div className="flex flex-col items-center">
        <ScoreRing score={overall} />

        {/* Song details with album art */}
        <div className="mt-6 grid grid-cols-2 gap-8 text-center text-sm">
          <div className="flex flex-col items-center">
            <AlbumArt src={songAArt} />
            <p className="text-gray-400 text-xs mb-1">Song A</p>
            <p className="font-medium text-gray-200 truncate max-w-[160px]">{songAName}</p>
            <p className="text-xs text-gray-500 mt-1">{details.song_a.tempo_bpm} BPM</p>
          </div>
          <div className="flex flex-col items-center">
            <AlbumArt src={songBArt} />
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

      {/* Actions */}
      <div className="flex justify-center gap-3 pt-4">
        <button
          onClick={onReset}
          className="px-6 py-2.5 rounded-xl bg-gray-800 text-gray-300 text-sm font-medium
                     hover:bg-gray-700 transition-colors"
        >
          Compare Another Pair
        </button>
        <ShareButton
          result={result}
          songAName={songAName}
          songBName={songBName}
        />
      </div>
    </div>
  );
}
