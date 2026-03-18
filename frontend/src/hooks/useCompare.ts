import { useState, useCallback } from "react";
import type { ComparisonResult, CompareStatus, SearchQuery, MixedSongInput } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "/api";

/** Safely parse JSON, throw a readable error if response is HTML (e.g. timeout page). */
async function safeJson(res: Response) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    // Server returned HTML (Render timeout/error page) instead of JSON
    if (text.includes("<!DOCTYPE") || text.includes("<html")) {
      throw new Error(
        res.status === 504 || res.status === 502
          ? "Request timed out — the server took too long. Try again in a moment."
          : `Server error (${res.status}). The service may be waking up — please retry in 30 seconds.`
      );
    }
    throw new Error(`Unexpected response: ${text.slice(0, 100)}`);
  }
}

/** Build the mixed-endpoint payload for a single song. */
function toMixedInput(search: SearchQuery): MixedSongInput {
  if (search.fallbackUrl?.trim()) {
    return { type: "url", url: search.fallbackUrl.trim() };
  }
  return { type: "search", name: search.name.trim(), artist: search.artist.trim() };
}

export function useCompare() {
  const [status, setStatus] = useState<CompareStatus>("idle");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const compareFiles = useCallback(async (fileA: File, fileB: File) => {
    setStatus("uploading");
    setResult(null);
    setError(null);

    try {
      const form = new FormData();
      form.append("file_a", fileA);
      form.append("file_b", fileB);

      setStatus("analyzing");

      const res = await fetch(`${API_URL}/compare`, {
        method: "POST",
        body: form,
      });

      const data = await safeJson(res);

      if (!res.ok) {
        throw new Error(data.error || "Comparison failed");
      }

      setResult(data);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setStatus("error");
    }
  }, []);

  /** Compare two songs — each can be a search query or a direct URL. */
  const compareMixed = useCallback(async (searchA: SearchQuery, searchB: SearchQuery) => {
    setStatus("uploading");
    setResult(null);
    setError(null);

    try {
      setStatus("analyzing");

      const res = await fetch(`${API_URL}/compare-mixed`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          song_a: toMixedInput(searchA),
          song_b: toMixedInput(searchB),
        }),
      });

      const data = await safeJson(res);

      if (!res.ok) {
        throw new Error(data.error || "Comparison failed");
      }

      setResult(data);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setStatus("error");
    }
  }, []);

  const reset = useCallback(() => {
    setStatus("idle");
    setResult(null);
    setError(null);
  }, []);

  return { status, result, error, compareFiles, compareMixed, reset };
}
