import { useState, useRef, useCallback } from "react";
import type { ItunesTrack } from "../types";

const ITUNES_API = "https://itunes.apple.com/search";
const DEBOUNCE_MS = 400;
const MIN_QUERY_LEN = 3;

/** Simple in-memory cache to avoid duplicate requests. */
const cache = new Map<string, ItunesTrack[]>();

function parseResults(data: { results?: Array<Record<string, unknown>> }): ItunesTrack[] {
  return (data.results ?? [])
    .filter((r) => r.previewUrl && r.trackName)
    .map((r) => ({
      trackId: r.trackId as number,
      trackName: r.trackName as string,
      artistName: r.artistName as string,
      collectionName: (r.collectionName as string) || "",
      artworkUrl: ((r.artworkUrl100 as string) || "").replace("100x100", "256x256"),
      previewUrl: r.previewUrl as string,
    }));
}

export function useItunesSearch() {
  const [suggestions, setSuggestions] = useState<ItunesTrack[]>([]);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback((query: string) => {
    // Clear pending debounce
    if (timerRef.current) clearTimeout(timerRef.current);
    if (abortRef.current) abortRef.current.abort();

    const trimmed = query.trim();
    if (trimmed.length < MIN_QUERY_LEN) {
      setSuggestions([]);
      setLoading(false);
      return;
    }

    // Check cache
    if (cache.has(trimmed)) {
      setSuggestions(cache.get(trimmed)!);
      return;
    }

    setLoading(true);

    timerRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const url = `${ITUNES_API}?${new URLSearchParams({
          term: trimmed,
          media: "music",
          entity: "song",
          limit: "6",
        })}`;

        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok) throw new Error("iTunes API error");

        const data = await res.json();
        const tracks = parseResults(data);

        cache.set(trimmed, tracks);
        setSuggestions(tracks);
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setSuggestions([]);
        }
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);
  }, []);

  const clear = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (abortRef.current) abortRef.current.abort();
    setSuggestions([]);
    setLoading(false);
  }, []);

  return { suggestions, loading, search, clear };
}
