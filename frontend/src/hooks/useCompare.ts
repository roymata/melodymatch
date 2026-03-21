import { useState, useCallback } from "react";
import type {
  ComparisonResult,
  CompareStatus,
  SearchQuery,
  MixedSongInput,
  ProgressInfo,
  ProgressStep,
} from "../types";

const API_URL = import.meta.env.VITE_API_URL || "/api";

const INITIAL_PROGRESS: ProgressInfo = { step: "searching", percent: 0 };

/** Safely parse JSON, throw a readable error if response is HTML. */
async function safeJson(res: Response) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
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

/**
 * Wake up the Render free-tier server before making the real request.
 * Retries the health endpoint until it responds (up to ~60s).
 */
async function ensureServerAwake(
  onWaking: () => void,
): Promise<void> {
  // Quick check — if health responds fast, server is already warm
  try {
    const fast = await fetch(`${API_URL}/health`, {
      signal: AbortSignal.timeout(3000),
    });
    if (fast.ok) return; // warm!
  } catch {
    // Server is cold — enter wake-up loop
  }

  onWaking(); // show "waking up" in UI

  const MAX_RETRIES = 15; // 15 × 4s = 60s max
  for (let i = 0; i < MAX_RETRIES; i++) {
    await new Promise((r) => setTimeout(r, 4000));
    try {
      const res = await fetch(`${API_URL}/health`, {
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) return; // server is awake
    } catch {
      // still waking up, keep trying
    }
  }

  throw new Error(
    "The server is taking too long to start. Please try again in a minute."
  );
}

/** Build the mixed-endpoint payload for a single song. */
function toMixedInput(search: SearchQuery): MixedSongInput {
  if (search.fallbackUrl?.trim()) {
    return { type: "url", url: search.fallbackUrl.trim() };
  }
  const track = search.selectedTrack;
  if (track) {
    return { type: "search", name: track.trackName, artist: track.artistName };
  }
  return { type: "search", name: search.query.trim(), artist: "" };
}

export function useCompare() {
  const [status, setStatus] = useState<CompareStatus>("idle");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressInfo>(INITIAL_PROGRESS);

  const compareFiles = useCallback(async (fileA: File, fileB: File) => {
    setStatus("uploading");
    setResult(null);
    setError(null);
    setProgress(INITIAL_PROGRESS);

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

  const compareMixed = useCallback(async (searchA: SearchQuery, searchB: SearchQuery) => {
    setStatus("streaming");
    setResult(null);
    setError(null);
    setProgress({ step: "searching", percent: 0 });

    try {
      // Wake up Render free-tier server if it's sleeping
      await ensureServerAwake(() => {
        setProgress({ step: "waking_up", percent: 0 });
      });

      // Server is awake — proceed with actual comparison
      setProgress({ step: "searching", percent: 2 });

      const payload = JSON.stringify({
        song_a: toMixedInput(searchA),
        song_b: toMixedInput(searchB),
      });

      const res = await fetch(`${API_URL}/compare-mixed-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
      });

      // If the response isn't OK and isn't a stream, handle as regular error
      if (!res.ok && res.headers.get("content-type")?.includes("application/json")) {
        const data = await safeJson(res);
        throw new Error(data.error || "Comparison failed");
      }

      if (!res.ok) {
        throw new Error(`Server error (${res.status}). The service may be waking up — please retry in 30 seconds.`);
      }

      // Read the SSE stream
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let gotResult = false;

      /** Parse a single SSE event chunk and update state. */
      function handleEvent(raw: string) {
        const dataLine = raw
          .split("\n")
          .find((l) => l.startsWith("data: "));
        if (!dataLine) return;

        const data = JSON.parse(dataLine.slice(6));

        if (data.error) {
          throw new Error(data.error);
        }

        setProgress({
          step: data.step as ProgressStep,
          percent: data.progress,
        });

        if (data.step === "done" && data.result) {
          setResult(data.result);
          setStatus("done");
          gotResult = true;
        }
      }

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by double newlines
        const parts = buffer.split("\n\n");
        buffer = parts.pop()!; // keep incomplete event in buffer

        for (const part of parts) {
          if (part.trim()) handleEvent(part);
        }
      }

      // Flush remaining buffer — the final event may not have
      // a trailing \n\n before the stream closes
      buffer += decoder.decode(); // flush decoder
      if (buffer.trim()) {
        // Buffer may contain one or more events
        for (const part of buffer.split("\n\n")) {
          if (part.trim()) handleEvent(part);
        }
      }

      if (!gotResult) {
        throw new Error(
          "Analysis completed but no results received. Please try again."
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setStatus("error");
    }
  }, []);

  const reset = useCallback(() => {
    setStatus("idle");
    setResult(null);
    setError(null);
    setProgress(INITIAL_PROGRESS);
  }, []);

  return { status, result, error, progress, compareFiles, compareMixed, reset };
}
