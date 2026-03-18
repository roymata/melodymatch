import { useState, useRef, useCallback } from "react";

interface FileDropZoneProps {
  label: string;
  file: File | null;
  onSelect: (file: File) => void;
}

const ACCEPTED = ".mp3,.wav,.flac,.ogg,.m4a,.aac";

export default function FileDropZone({ label, file, onSelect }: FileDropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) onSelect(dropped);
    },
    [onSelect]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) onSelect(selected);
    },
    [onSelect]
  );

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
        px-6 py-10 cursor-pointer transition-all duration-200
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

      {/* Icon */}
      <div className="mb-3 text-gray-500">
        <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 8.25H7.5a2.25 2.25 0 0 0-2.25 2.25v9a2.25 2.25 0 0 0 2.25 2.25h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25H15m0-3-3-3m0 0-3 3m3-3V15" />
        </svg>
      </div>

      <p className="text-sm font-medium text-gray-300">{label}</p>

      {file ? (
        <p className="mt-2 text-xs text-brand-400 truncate max-w-[200px]">{file.name}</p>
      ) : (
        <p className="mt-2 text-xs text-gray-500">
          Drag & drop or click to browse
        </p>
      )}

      <p className="mt-1 text-[10px] text-gray-600">MP3, WAV, FLAC, OGG, M4A, AAC</p>
    </div>
  );
}
