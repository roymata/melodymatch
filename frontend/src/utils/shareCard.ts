import type { ComparisonResult } from "../types";

const W = 600;
const H = 520;
const PAD = 32;
const BAR_H = 18;
const BAR_GAP = 36;

const BREAKDOWN_LABELS: Record<string, string> = {
  rhythm: "Rhythm",
  tempo: "Tempo",
  timbre: "Timbre",
  harmony: "Harmony",
  lyrics: "Lyrics",
};

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

/**
 * Generate a shareable image card from comparison results.
 * Returns a Blob (image/png).
 */
export async function generateShareCard(
  result: ComparisonResult,
  songAName: string,
  songBName: string,
): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d")!;

  // ── Background ──
  ctx.fillStyle = "#111827";
  roundRect(ctx, 0, 0, W, H, 16);
  ctx.fill();

  // Subtle border
  ctx.strokeStyle = "#1f2937";
  ctx.lineWidth = 1;
  roundRect(ctx, 0.5, 0.5, W - 1, H - 1, 16);
  ctx.stroke();

  // ── Header ──
  ctx.fillStyle = "#9ca3af";
  ctx.font = "600 13px system-ui, -apple-system, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("🎵  MelodyMatch", W / 2, PAD + 4);

  // ── Song names ──
  const nameY = PAD + 38;
  ctx.fillStyle = "#e5e7eb";
  ctx.font = "600 16px system-ui, -apple-system, sans-serif";
  const maxNameW = (W - PAD * 2 - 60) / 2;

  ctx.textAlign = "right";
  let nameA = songAName;
  while (ctx.measureText(nameA).width > maxNameW && nameA.length > 3) {
    nameA = nameA.slice(0, -2) + "…";
  }
  ctx.fillText(nameA, W / 2 - 30, nameY);

  ctx.fillStyle = "#6b7280";
  ctx.font = "400 14px system-ui, -apple-system, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("vs", W / 2, nameY);

  ctx.fillStyle = "#e5e7eb";
  ctx.font = "600 16px system-ui, -apple-system, sans-serif";
  ctx.textAlign = "left";
  let nameB = songBName;
  while (ctx.measureText(nameB).width > maxNameW && nameB.length > 3) {
    nameB = nameB.slice(0, -2) + "…";
  }
  ctx.fillText(nameB, W / 2 + 30, nameY);

  // ── Score circle ──
  const cx = W / 2;
  const cy = nameY + 80;
  const radius = 48;

  // Outer ring
  const pct = result.overall / 100;
  ctx.lineWidth = 6;
  ctx.lineCap = "round";

  // Background ring
  ctx.strokeStyle = "#1f2937";
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.stroke();

  // Progress ring
  const color =
    result.overall >= 70 ? "#22c55e" :
    result.overall >= 40 ? "#eab308" : "#ef4444";
  ctx.strokeStyle = color;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * pct);
  ctx.stroke();

  // Score text
  ctx.fillStyle = "#f3f4f6";
  ctx.font = "700 28px system-ui, -apple-system, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(`${result.overall}%`, cx, cy - 4);

  ctx.fillStyle = "#9ca3af";
  ctx.font = "500 11px system-ui, -apple-system, sans-serif";
  ctx.fillText("Similar", cx, cy + 18);
  ctx.textBaseline = "alphabetic";

  // ── Breakdown bars ──
  const barStartY = cy + radius + 40;
  const barLeft = PAD + 70;
  const barW = W - PAD * 2 - 110;

  const entries = Object.entries(result.breakdown);
  entries.forEach(([key, value], i) => {
    const label = BREAKDOWN_LABELS[key];
    if (!label) return;
    const y = barStartY + i * BAR_GAP;

    // Label
    ctx.fillStyle = "#d1d5db";
    ctx.font = "500 13px system-ui, -apple-system, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(label, barLeft - 12, y + BAR_H / 2 + 4);

    // Bar background
    ctx.fillStyle = "#1f2937";
    roundRect(ctx, barLeft, y, barW, BAR_H, 4);
    ctx.fill();

    if (value === null || value === undefined) {
      // N/A
      ctx.fillStyle = "#4b5563";
      ctx.font = "500 11px system-ui, -apple-system, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("N/A", barLeft + barW + 8, y + BAR_H / 2 + 4);
    } else {
      // Filled bar
      const fillW = Math.max(2, (value / 100) * barW);
      const barColor =
        value >= 70 ? "#22c55e" : value >= 40 ? "#eab308" : "#ef4444";
      ctx.fillStyle = barColor;
      roundRect(ctx, barLeft, y, fillW, BAR_H, 4);
      ctx.fill();

      // Value
      ctx.fillStyle = "#d1d5db";
      ctx.font = "600 12px system-ui, -apple-system, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(`${value}%`, barLeft + barW + 8, y + BAR_H / 2 + 4);
    }
  });

  // ── Footer ──
  ctx.fillStyle = "#4b5563";
  ctx.font = "400 11px system-ui, -apple-system, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("melodymatch-2i62.onrender.com", W / 2, H - PAD + 8);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob!), "image/png");
  });
}

/**
 * Share or download the comparison card.
 */
export async function shareResults(
  result: ComparisonResult,
  songAName: string,
  songBName: string,
): Promise<void> {
  const blob = await generateShareCard(result, songAName, songBName);
  const file = new File([blob], "melodymatch-comparison.png", { type: "image/png" });

  // Try native share (mobile + modern browsers)
  if (navigator.share && navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({
        title: "MelodyMatch Comparison",
        text: `${songAName} vs ${songBName} — ${result.overall}% similar!`,
        files: [file],
      });
      return;
    } catch {
      // User cancelled or share failed — fall through to download
    }
  }

  // Fallback: download the image
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "melodymatch-comparison.png";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
