export interface SimilarityBreakdown {
  rhythm: number;
  tempo: number;
  timbre: number;
  harmony: number;
  lyrics: number | null;
}

export interface SongDetails {
  tempo_bpm: number;
  spectral_centroid: number;
}

export interface ComparisonResult {
  overall: number;
  breakdown: SimilarityBreakdown;
  details: {
    song_a: SongDetails;
    song_b: SongDetails;
  };
}

export interface UploadedFile {
  file: File;
  name: string;
}

export type CompareStatus = "idle" | "uploading" | "analyzing" | "streaming" | "done" | "error";

export type InputMode = "file" | "search";

export interface ItunesTrack {
  trackId: number;
  trackName: string;
  artistName: string;
  collectionName: string;
  artworkUrl: string;
  previewUrl?: string;
}

export interface SearchQuery {
  query: string;
  selectedTrack?: ItunesTrack;
  fallbackUrl?: string;
}

/** Payload shape for the /compare-mixed endpoint. */
export interface MixedSongInput {
  type: "search" | "url";
  name?: string;
  artist?: string;
  url?: string;
}

/** SSE progress step names from the streaming endpoint. */
export type ProgressStep =
  | "waking_up"
  | "searching"
  | "fetching_lyrics"
  | "analyzing"
  | "comparing"
  | "done"
  | "error";

/** Real-time progress info from the SSE stream. */
export interface ProgressInfo {
  step: ProgressStep;
  percent: number;
}
