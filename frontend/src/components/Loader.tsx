import { useState, useEffect, useRef } from "react";
import type { CompareStatus, ProgressInfo } from "../types";

interface LoaderProps {
  status: CompareStatus;
  progress: ProgressInfo;
  songAName: string;
  songBName: string;
}

const TIPS = [
  { emoji: "🎵", text: "Most pop hits reuse the same I–V–vi–IV chord progression." },
  { emoji: "🧠", text: "We analyze 50+ audio features including timbre, rhythm, and harmony." },
  { emoji: "🎸", text: "Two songs can share tempo and key but sound completely different." },
  { emoji: "📊", text: "Our algorithm uses Euclidean distance in feature space for accuracy." },
  { emoji: "🎹", text: "The most popular tempo in music is around 120 BPM — the pace of walking." },
  { emoji: "🔊", text: "MFCCs capture the 'texture' of sound — like a fingerprint for audio." },
  { emoji: "🎤", text: "A 30-second clip contains enough audio DNA for a reliable comparison." },
  { emoji: "🥁", text: "Onset detection finds every beat — even subtle ones humans might miss." },
];

/** Truncate a name so the step labels don't overflow. */
function truncate(s: string, max = 24): string {
  return s.length > max ? s.slice(0, max - 1) + "\u2026" : s;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// ── Waveform bars animation ─────────────────────────────────────────────
function WaveformBars() {
  return (
    <div className="flex items-end gap-[3px] h-6">
      {[0, 1, 2, 3, 4, 5, 6].map((i) => (
        <div
          key={i}
          className="w-[3px] rounded-full bg-brand-400/70"
          style={{
            animation: `wave 1s ease-in-out ${i * 0.12}s infinite`,
          }}
        />
      ))}
      <style>{`
        @keyframes wave {
          0%, 100% { height: 6px; }
          50% { height: 22px; }
        }
      `}</style>
    </div>
  );
}

// ── Step indicator ──────────────────────────────────────────────────────
function StepRow({
  icon,
  activeLabel,
  doneLabel,
  isComplete,
  isActive,
}: {
  icon: string;
  activeLabel: string;
  doneLabel: string;
  isComplete: boolean;
  isActive: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-500 ${
        isActive
          ? "bg-brand-500/10 border border-brand-500/30 shadow-sm shadow-brand-500/10"
          : isComplete
          ? "bg-gray-800/20"
          : "opacity-40"
      }`}
    >
      {/* Status icon */}
      <div className="w-6 h-6 flex-shrink-0 flex items-center justify-center">
        {isComplete && (
          <svg
            className="w-5 h-5 text-emerald-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        )}
        {isActive && (
          <div className="w-5 h-5 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
        )}
        {!isComplete && !isActive && (
          <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-700" />
        )}
      </div>

      {/* Step icon */}
      <span className="text-base flex-shrink-0">{icon}</span>

      {/* Label */}
      <span
        className={`text-sm leading-tight ${
          isActive
            ? "text-gray-200 font-medium"
            : isComplete
            ? "text-gray-400"
            : "text-gray-600"
        }`}
      >
        {isComplete ? doneLabel : activeLabel}
        {isActive && (
          <span className="inline-block ml-0.5 animate-pulse">...</span>
        )}
      </span>
    </div>
  );
}

// ── Main Loader ─────────────────────────────────────────────────────────
export default function Loader({
  status,
  progress,
  songAName,
  songBName,
}: LoaderProps) {
  const [elapsed, setElapsed] = useState(0);
  const [tipIndex, setTipIndex] = useState(0);
  const startRef = useRef(Date.now());

  // Elapsed timer
  useEffect(() => {
    startRef.current = Date.now();
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  // Rotate tips every 6 seconds
  useEffect(() => {
    const id = setInterval(() => {
      setTipIndex((prev) => (prev + 1) % TIPS.length);
    }, 6000);
    return () => clearInterval(id);
  }, []);

  // ── File-upload fallback (simple spinner) ──
  if (status === "uploading" || status === "analyzing") {
    return (
      <div className="flex flex-col items-center py-16 animate-fadeIn">
        <div className="relative w-20 h-20 mb-6">
          <div className="absolute inset-0 rounded-full border-2 border-brand-500/30 animate-ping" />
          <div className="absolute inset-2 rounded-full border-2 border-brand-400/50 animate-ping [animation-delay:150ms]" />
          <div className="absolute inset-4 rounded-full border-2 border-brand-400 animate-pulse" />
          <div className="absolute inset-0 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-brand-400 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
          </div>
        </div>
        <p className="text-sm text-gray-400">
          {status === "uploading"
            ? "Uploading tracks..."
            : "Analyzing audio features..."}
        </p>
      </div>
    );
  }

  // ── Streaming mode: interactive step-by-step loader ──
  const nameA = truncate(songAName);
  const nameB = truncate(songBName);

  const steps = [
    {
      key: "searching",
      icon: "🔍",
      activeLabel: "Finding your songs",
      doneLabel: "Songs found",
    },
    {
      key: "analyzing_a",
      icon: "🧬",
      activeLabel: `Analyzing "${nameA}"`,
      doneLabel: `Analyzed "${nameA}"`,
    },
    {
      key: "analyzing_b",
      icon: "🧬",
      activeLabel: `Analyzing "${nameB}"`,
      doneLabel: `Analyzed "${nameB}"`,
    },
    {
      key: "comparing",
      icon: "📊",
      activeLabel: "Computing similarity score",
      doneLabel: "Similarity computed",
    },
  ];

  const stepKeys = steps.map((s) => s.key);
  const currentIndex = stepKeys.indexOf(progress.step);

  const tip = TIPS[tipIndex];

  return (
    <div className="flex flex-col items-center py-8 animate-fadeIn">
      {/* Header with waveform */}
      <div className="flex items-center gap-3 mb-8">
        <WaveformBars />
        <h2 className="text-lg font-semibold text-gray-200">
          Analyzing Your Tracks
        </h2>
        <WaveformBars />
      </div>

      {/* Steps timeline */}
      <div className="w-full max-w-sm space-y-2 mb-8">
        {steps.map((step, i) => {
          // Mark all complete when we reach "done"
          const isAllDone = progress.step === "done";
          const isActive = !isAllDone && i === currentIndex;
          const isDone = isAllDone || i < currentIndex;

          return (
            <StepRow
              key={step.key}
              icon={step.icon}
              activeLabel={step.activeLabel}
              doneLabel={step.doneLabel}
              isComplete={isDone}
              isActive={isActive}
            />
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-sm mb-5">
        <div className="flex justify-between text-xs text-gray-500 mb-1.5">
          <span>Progress</span>
          <span>{Math.min(progress.percent, 100)}%</span>
        </div>
        <div className="h-2 bg-gray-800/80 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${Math.min(progress.percent, 100)}%`,
              background:
                "linear-gradient(90deg, #22c55e 0%, #4ade80 50%, #34d399 100%)",
            }}
          />
        </div>
      </div>

      {/* Elapsed time */}
      <p className="text-xs text-gray-500 mb-6">
        <span className="inline-block w-4 text-center">&#9201;</span>{" "}
        {formatElapsed(elapsed)} elapsed
      </p>

      {/* Rotating fun fact */}
      <div className="w-full max-w-sm px-5 py-4 rounded-xl bg-gray-800/40 border border-gray-800 text-center">
        <div className="flex items-center justify-center gap-2 mb-1.5">
          <span className="text-lg">{tip.emoji}</span>
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Did you know?
          </span>
        </div>
        <p className="text-xs text-gray-500 leading-relaxed">{tip.text}</p>
      </div>
    </div>
  );
}
