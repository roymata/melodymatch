import { useState, useRef, useCallback, useEffect } from "react";
import type { InputMode, SearchQuery, ItunesTrack } from "../types";
import { useItunesSearch } from "../hooks/useItunesSearch";

interface SongInputProps {
  label: string;
  mode: InputMode;
  file: File | null;
  search: SearchQuery;
  showUrlFallback: boolean;
  onFileSelect: (file: File) => void;
  onSearchChange: (search: SearchQuery) => void;
}

const ACCEPTED = ".mp3,.wav,.flac,.ogg,.m4a,.aac";

export default function SongInput({
  label,
  mode,
  file,
  search,
  showUrlFallback,
  onFileSelect,
  onSearchChange,
}: SongInputProps) {
  const [dragging, setDragging] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { suggestions, loading, search: itunesSearch, clear: clearSuggestions } = useItunesSearch();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleQueryChange = useCallback(
    (value: string) => {
      onSearchChange({ query: value, selectedTrack: undefined, fallbackUrl: undefined });
      itunesSearch(value);
      setShowDropdown(true);
    },
    [onSearchChange, itunesSearch]
  );

  const handleSelectTrack = useCallback(
    (track: ItunesTrack) => {
      onSearchChange({
        query: `${track.trackName} — ${track.artistName}`,
        selectedTrack: track,
        fallbackUrl: undefined,
      });
      clearSuggestions();
      setShowDropdown(false);
    },
    [onSearchChange, clearSuggestions]
  );

  const handleClearSelection = useCallback(() => {
    onSearchChange({ query: "", selectedTrack: undefined, fallbackUrl: undefined });
    clearSuggestions();
  }, [onSearchChange, clearSuggestions]);

  // File mode handlers
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) onFileSelect(dropped);
    },
    [onFileSelect]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) onFileSelect(selected);
    },
    [onFileSelect]
  );

  // ── Search mode ──────────────────────────────────────────────────────────

  if (mode === "search") {
    const track = search.selectedTrack;

    return (
      <div
        ref={dropdownRef}
        className={`
          relative flex flex-col rounded-2xl border-2 border-dashed
          px-5 py-5 transition-all duration-200
          ${track ? "border-brand-500/50 bg-brand-500/5" : "border-gray-700 bg-gray-900/50"}
        `}
      >
        <p className="text-sm font-medium text-gray-300 mb-3 text-center">{label}</p>

        {/* Selected track card */}
        {track ? (
          <div className="flex items-center gap-3 animate-fadeIn">
            <img
              src={track.artworkUrl}
              alt={track.collectionName}
              className="w-16 h-16 rounded-lg shadow-lg flex-shrink-0"
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-200 truncate">{track.trackName}</p>
              <p className="text-xs text-gray-400 truncate">{track.artistName}</p>
              <p className="text-[10px] text-gray-600 truncate">{track.collectionName}</p>
            </div>
            <button
              onClick={handleClearSelection}
              className="flex-shrink-0 p-1 rounded-full hover:bg-gray-700 transition-colors text-gray-500 hover:text-gray-300"
              title="Clear selection"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ) : (
          <>
            {/* Search input */}
            <div className="relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                </svg>
              </div>
              <input
                type="text"
                value={search.query}
                onChange={(e) => handleQueryChange(e.target.value)}
                onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
                placeholder="Search song or artist..."
                className="w-full bg-gray-800/80 border border-gray-700 rounded-lg pl-9 pr-3 py-2.5 text-sm
                           text-gray-200 placeholder-gray-500 outline-none
                           focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/25 transition-all"
              />
              {loading && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="w-4 h-4 border-2 border-gray-600 border-t-brand-400 rounded-full animate-spin" />
                </div>
              )}
            </div>

            {/* Suggestions dropdown */}
            {showDropdown && suggestions.length > 0 && (
              <div className="absolute left-0 right-0 top-[calc(100%-8px)] z-50 mx-3 mt-1
                              bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden animate-fadeIn">
                {suggestions.map((s) => (
                  <button
                    key={s.trackId}
                    onClick={() => handleSelectTrack(s)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-700/70
                               transition-colors text-left"
                  >
                    <img
                      src={s.artworkUrl.replace("256x256", "60x60")}
                      alt=""
                      className="w-10 h-10 rounded flex-shrink-0"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-gray-200 truncate">{s.trackName}</p>
                      <p className="text-xs text-gray-500 truncate">{s.artistName}</p>
                    </div>
                  </button>
                ))}
              </div>
            )}

            <p className="mt-2 text-[10px] text-gray-600 text-center">
              Type to search songs from iTunes
            </p>
          </>
        )}

        {/* URL fallback — shown after a search error */}
        {showUrlFallback && (
          <div className="mt-3 animate-fadeIn">
            <div className="flex items-center gap-2 my-2">
              <div className="flex-1 h-px bg-gray-700" />
              <span className="text-[10px] text-gray-500 uppercase tracking-wider">or paste YouTube URL</span>
              <div className="flex-1 h-px bg-gray-700" />
            </div>
            <input
              type="text"
              value={search.fallbackUrl ?? ""}
              onChange={(e) => onSearchChange({ ...search, fallbackUrl: e.target.value })}
              placeholder="https://youtube.com/watch?v=..."
              className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-3 py-2 text-sm
                         text-gray-200 placeholder-gray-500 outline-none
                         focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/25 transition-all"
            />
          </div>
        )}
      </div>
    );
  }

  // ── File mode (unchanged) ────────────────────────────────────────────────

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      className={`
        relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed
        px-6 py-8 cursor-pointer transition-all duration-200
        ${dragging ? "border-brand-400 bg-brand-400/10" : "border-gray-700 hover:border-gray-500 bg-gray-900/50"}
        ${file ? "border-brand-500/50 bg-brand-500/5" : ""}
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED}
        onChange={handleFileChange}
        className="hidden"
      />

      <div className="mb-3 text-gray-500">
        <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 8.25H7.5a2.25 2.25 0 0 0-2.25 2.25v9a2.25 2.25 0 0 0 2.25 2.25h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25H15m0-3-3-3m0 0-3 3m3-3V15" />
        </svg>
      </div>

      <p className="text-sm font-medium text-gray-300">{label}</p>

      {file ? (
        <p className="mt-2 text-xs text-brand-400 truncate max-w-[200px]">{file.name}</p>
      ) : (
        <p className="mt-2 text-xs text-gray-500">Drag & drop or click to browse</p>
      )}

      <p className="mt-1 text-[10px] text-gray-600">MP3, WAV, FLAC, OGG, M4A, AAC</p>
    </div>
  );
}
