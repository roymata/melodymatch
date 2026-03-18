import { useState, useRef, useCallback } from "react";
import type { InputMode, SearchQuery } from "../types";

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
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) onFileSelect(dropped);
    },
    [onFileSelect]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) onFileSelect(selected);
    },
    [onFileSelect]
  );

  const hasSearch = search.name.length > 0 && search.artist.length > 0;
  const hasUrl = (search.fallbackUrl ?? "").length > 0;

  if (mode === "search") {
    return (
      <div
        className={`
          relative flex flex-col rounded-2xl border-2 border-dashed
          px-6 py-6 transition-all duration-200
          ${hasSearch || hasUrl ? "border-brand-500/50 bg-brand-500/5" : "border-gray-700 bg-gray-900/50"}
        `}
      >
        {/* Music search icon */}
        <div className="mb-3 text-gray-500 self-center">
          <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m9 9 10.5-3m0 6.553v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 1 1-.99-3.467l2.31-.66a2.25 2.25 0 0 0 1.632-2.163Zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 0 1-.99-3.467l2.31-.66A2.25 2.25 0 0 0 9 15.553Z" />
          </svg>
        </div>

        <p className="text-sm font-medium text-gray-300 mb-3 text-center">{label}</p>

        <div className="space-y-2">
          <input
            type="text"
            value={search.name}
            onChange={(e) => onSearchChange({ ...search, name: e.target.value, fallbackUrl: undefined })}
            placeholder="Song name"
            className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-3 py-2 text-sm
                       text-gray-200 placeholder-gray-500 outline-none
                       focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/25 transition-all"
          />
          <input
            type="text"
            value={search.artist}
            onChange={(e) => onSearchChange({ ...search, artist: e.target.value, fallbackUrl: undefined })}
            placeholder="Artist"
            className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-3 py-2 text-sm
                       text-gray-200 placeholder-gray-500 outline-none
                       focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/25 transition-all"
          />
        </div>

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

        <p className="mt-2 text-[10px] text-gray-600 text-center">
          {showUrlFallback ? "Paste a direct link if search didn't find it" : "Searches YouTube automatically"}
        </p>
      </div>
    );
  }

  // File mode (existing behavior)
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`
        relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed
        px-6 py-8 cursor-pointer transition-all duration-200
        ${dragging ? "border-brand-400 bg-brand-400/10" : "border-gray-700 hover:border-gray-500 bg-gray-900/50"}
        ${file ? "border-brand-500/50 bg-brand-500/5" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        onChange={handleChange}
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
