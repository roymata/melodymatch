import { useState } from "react";
import HeroSection from "./components/HeroSection";
import SongInput from "./components/SongInput";
import ResultsPanel from "./components/ResultsPanel";
import Loader from "./components/Loader";
import FunFacts from "./components/FunFacts";
import Footer from "./components/Footer";
import { useCompare } from "./hooks/useCompare";
import type { InputMode, SearchQuery } from "./types";

const EMPTY_SEARCH: SearchQuery = { query: "" };

const YT_URL_RE =
  /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)[\w-]+/;

export default function App() {
  const [mode, setMode] = useState<InputMode>("search");
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [searchA, setSearchA] = useState<SearchQuery>(EMPTY_SEARCH);
  const [searchB, setSearchB] = useState<SearchQuery>(EMPTY_SEARCH);
  const { status, result, error, progress, compareFiles, compareMixed, reset } = useCompare();

  const showUrlFallback = status === "error" && mode === "search";

  function isSongReady(s: SearchQuery): boolean {
    if (s.fallbackUrl?.trim() && YT_URL_RE.test(s.fallbackUrl.trim())) return true;
    return !!s.selectedTrack;
  }

  const isBusy = status === "analyzing" || status === "uploading" || status === "streaming";
  const canCompareFiles = mode === "file" && fileA && fileB && !isBusy;
  const canCompareSearch =
    mode === "search" &&
    isSongReady(searchA) &&
    isSongReady(searchB) &&
    !isBusy;
  const canCompare = canCompareFiles || canCompareSearch;
  const isLoading = isBusy;

  function handleCompare() {
    if (mode === "file" && fileA && fileB) {
      compareFiles(fileA, fileB);
    } else if (mode === "search") {
      compareMixed(searchA, searchB);
    }
  }

  function handleReset() {
    setFileA(null);
    setFileB(null);
    setSearchA(EMPTY_SEARCH);
    setSearchB(EMPTY_SEARCH);
    reset();
  }

  const songAName = mode === "file"
    ? (fileA?.name || "Song A")
    : (searchA.selectedTrack?.trackName || searchA.query || "Song A");
  const songBName = mode === "file"
    ? (fileB?.name || "Song B")
    : (searchB.selectedTrack?.trackName || searchB.query || "Song B");

  const songAArt = searchA.selectedTrack?.artworkUrl;
  const songBArt = searchB.selectedTrack?.artworkUrl;

  return (
    <div className="min-h-screen flex flex-col relative">
      {/* Animated gradient mesh background */}
      <div className="fixed inset-0 bg-mesh-animated pointer-events-none -z-10" />

      {/* Floating music notes */}
      {[
        { x: "10%", y: "15%", d: "0s", s: 24, o: 0.04 },
        { x: "85%", y: "25%", d: "1s", s: 18, o: 0.03 },
        { x: "70%", y: "70%", d: "2s", s: 28, o: 0.05 },
        { x: "20%", y: "80%", d: "0.5s", s: 20, o: 0.04 },
        { x: "50%", y: "8%", d: "1.5s", s: 22, o: 0.03 },
      ].map((n, i) => (
        <svg key={i} className="fixed animate-float text-accent-purple pointer-events-none"
          style={{ left: n.x, top: n.y, animationDelay: n.d, opacity: n.o, width: n.s, height: n.s }}
          fill="currentColor" viewBox="0 0 24 24">
          <path d="M9 19V5l12-2v14" /><circle cx="6" cy="18.5" r="3.5" /><circle cx="18" cy="16.5" r="3.5" />
        </svg>
      ))}

      <HeroSection />

      {/* Main content */}
      <main className="flex-1 max-w-2xl w-full mx-auto px-4 pb-12">
        {/* Input area */}
        {(status === "idle" || status === "error") && (
          <div className="animate-fadeIn">
            {/* Mode toggle */}
            <div className="flex justify-center mb-6">
              <div className="inline-flex rounded-xl bg-white/[0.04] backdrop-blur-sm border border-white/[0.06] p-1">
                <button
                  onClick={() => setMode("search")}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium font-display transition-all duration-200 ${
                    mode === "search"
                      ? "bg-gradient-to-r from-accent-purple/20 to-accent-pink/20 text-white shadow-lg shadow-accent-purple/10 border border-white/[0.08]"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  Search Song
                </button>
                <button
                  onClick={() => setMode("file")}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium font-display transition-all duration-200 ${
                    mode === "file"
                      ? "bg-gradient-to-r from-accent-purple/20 to-accent-pink/20 text-white shadow-lg shadow-accent-purple/10 border border-white/[0.08]"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  Upload Files
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <SongInput
                label="Song A"
                mode={mode}
                file={fileA}
                search={searchA}
                showUrlFallback={showUrlFallback}
                onFileSelect={setFileA}
                onSearchChange={setSearchA}
              />
              <SongInput
                label="Song B"
                mode={mode}
                file={fileB}
                search={searchB}
                showUrlFallback={showUrlFallback}
                onFileSelect={setFileB}
                onSearchChange={setSearchB}
              />
            </div>

            {error && (
              <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400 text-center">
                {error}
                {showUrlFallback && (
                  <p className="mt-1 text-xs text-gray-500">
                    You can paste YouTube URLs above and try again.
                  </p>
                )}
              </div>
            )}

            <div className="mt-6 flex justify-center">
              <button
                disabled={!canCompare}
                onClick={handleCompare}
                className={`
                  px-8 py-3 rounded-xl text-sm font-semibold transition-all duration-200
                  ${
                    canCompare
                      ? "bg-gradient-to-r from-accent-purple via-accent-pink to-brand-500 text-white font-display shadow-lg shadow-accent-purple/25 hover:shadow-glow-multi hover:scale-[1.02] active:scale-[0.98]"
                      : "bg-gray-800/50 text-gray-500 cursor-not-allowed border border-gray-700/50"
                  }
                `}
              >
                {showUrlFallback ? "Retry Comparison" : "Compare Now"}
              </button>
            </div>

            {mode === "search" && !showUrlFallback && (
              <p className="mt-3 text-center text-xs text-gray-600">
                Select songs from the search results, then compare
              </p>
            )}
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <Loader
            status={status}
            progress={progress}
            songAName={songAName}
            songBName={songBName}
          />
        )}

        {/* Results */}
        {status === "done" && result && (
          <ResultsPanel
            result={result}
            songAName={songAName}
            songBName={songBName}
            songAArt={songAArt}
            songBArt={songBArt}
            onReset={handleReset}
          />
        )}

        {/* Fun facts — shown when idle */}
        {status === "idle" && <FunFacts />}
      </main>

      <Footer />
    </div>
  );
}
