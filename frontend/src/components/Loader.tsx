import type { CompareStatus } from "../types";

const messages: Record<string, string> = {
  uploading: "Uploading tracks...",
  analyzing: "Analyzing audio features...",
};

export default function Loader({ status }: { status: CompareStatus }) {
  const msg = messages[status] || "Processing...";

  return (
    <div className="flex flex-col items-center py-16 animate-fadeIn">
      {/* Pulsing rings */}
      <div className="relative w-20 h-20 mb-6">
        <div className="absolute inset-0 rounded-full border-2 border-brand-500/30 animate-ping" />
        <div className="absolute inset-2 rounded-full border-2 border-brand-400/50 animate-ping [animation-delay:150ms]" />
        <div className="absolute inset-4 rounded-full border-2 border-brand-400 animate-pulse" />
        <div className="absolute inset-0 flex items-center justify-center">
          <svg className="w-8 h-8 text-brand-400 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
        </div>
      </div>
      <p className="text-sm text-gray-400">{msg}</p>
    </div>
  );
}
