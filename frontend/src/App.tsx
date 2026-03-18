import { useState } from "react";
import SongInput from "./components/SongInput";
import ResultsPanel from "./components/ResultsPanel";
import Loader from "./components/Loader";
import Footer from "./components/Footer";
import { useCompare } from "./hooks/useCompare";
import type { InputMode, SearchQuery } from "./types";

const EMPTY_SEARCH: SearchQuery = { name: "", artist: "" };

const YT_URL_RE =
  /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)[\w-]+/;

export default function App() {
  const [mode, setMode] = useState<InputMode>("search");
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [searchA, setSearchA] = useState<SearchQuery>(EMPTY_SEARCH);
  const [searchB, setSearchB] = useState<SearchQuery>(EMPTY_SEARCH);
  const { status, result, error, compareFiles, compareMixed, reset } = useCompare();

  // Show URL fallback inputs when a search has failed
  const showUrlFallback = status === "error" && mode === "search";

  // Determine if each song input is valid
  function isSongReady(s: SearchQuery): boolean {
    if (s.fallbackUrl?.trim() && YT_URL_RE.test(s.fallbackUrl.trim())) return true;
    return s.name.trim() !== "" && s.artist.trim() !== "";
  }

  const canCompareFiles = mode === "file" && fileA && fileB && status !== "analyzing" && status !== "uploading";
  const canCompareSearch =
    mode === "search" &&
    isSongReady(searchA) &&
    isSongReady(searchB) &&
    status !== "analyzing" &&
    status !== "uploading";
  const canCompare = canCompareFiles || canCompareSearch;
  const isLoading = status === "uploading" || status === "analyzing";

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

  function songDisplayName(s: SearchQuery, fallback: string): string {
    if (s.fallbackUrl?.trim()) return s.fallbackUrl.trim();
    if (s.name) return `${s.name} — ${s.artist}`;
    return fallback;
  }

  const songAName = mode === "file" ? (fileA?.name || "Song A") : songDisplayName(searchA, "Song A");
  const songBName = mode === "file" ? (fileB?.name || "Song B") : songDisplayName(searchB, "Song B");

  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero / Header */}
      <header className="pt-16 pb-8 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-gradient-to-r from-brand-400 to-emerald-300 bg-clip-text text-transparent">
          SongDiff
        </h1>
        <p className="mt-3 text-lg text-gray-400 max-w-md mx-auto">
          Compare songs. Discover similarity.
        </p>
        <p className="mt-1 text-sm text-gray-600 max-w-sm mx-auto">
          Search for any two songs or upload audio files to see how similar they are across rhythm, tempo, timbre, and harmony.
        </p>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-2xl w-full mx-auto px-4 pb-12">
        {/* Input area */}
        {(status === "idle" || status === "error") && (
          <div className="animate-fadeIn">
            {/* Mode toggle */}
            <div className="flex justify-center mb-6">
              <div className="inline-flex rounded-lg bg-gray-800/80 p-1">
                <button
                  onClick={() => setMode("search")}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                    mode === "search"
                      ? "bg-gray-700 text-white shadow"
                      : "text-gray-400 hover:text-gray-300"
                  }`}
                >
                  Search Song
                </button>
                <button
                  onClick={() => setMode("file")}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                    mode === "file"
                      ? "bg-gray-700 text-white shadow"
                      : "text-gray-400 hover:text-gray-300"
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
                      ? "bg-brand-500 text-white hover:bg-brand-600 shadow-lg shadow-brand-500/25"
                      : "bg-gray-800 text-gray-500 cursor-not-allowed"
                  }
                `}
              >
                {showUrlFallback ? "Retry Comparison" : "Compare Now"}
              </button>
            </div>

            {mode === "search" && !showUrlFallback && (
              <p className="mt-3 text-center text-xs text-gray-600">
                Songs are found on YouTube automatically — may take 20-40 seconds
              </p>
            )}
          </div>
        )}

        {/* Loading state */}
        {isLoading && <Loader status={status} />}

        {/* Results */}
        {status === "done" && result && (
          <ResultsPanel
            result={result}
            songAName={songAName}
            songBName={songBName}
            onReset={handleReset}
          />
        )}
      </main>

      <Footer />
    </div>
  );
}
