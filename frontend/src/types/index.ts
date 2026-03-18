export interface SimilarityBreakdown {
  rhythm: number;
  tempo: number;
  timbre: number;
  harmony: number;
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

export type CompareStatus = "idle" | "uploading" | "analyzing" | "done" | "error";

export type InputMode = "file" | "search";

export interface SearchQuery {
  name: string;
  artist: string;
  fallbackUrl?: string;
}

/** Payload shape for the /compare-mixed endpoint. */
export interface MixedSongInput {
  type: "search" | "url";
  name?: string;
  artist?: string;
  url?: string;
}
