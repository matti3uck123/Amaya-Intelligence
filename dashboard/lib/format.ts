import type { Grade } from "./types";

export function formatScore(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

export function formatPercent(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const delta = Date.now() - then;
  const min = Math.round(delta / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.round(hr / 24);
  return `${d}d ago`;
}

const GRADE_COLORS: Record<Grade, { bg: string; text: string; ring: string }> = {
  "A+": { bg: "bg-grade-aplus", text: "text-grade-aplus", ring: "ring-grade-aplus" },
  A:    { bg: "bg-grade-a",     text: "text-grade-a",     ring: "ring-grade-a" },
  "B+": { bg: "bg-grade-bplus", text: "text-grade-bplus", ring: "ring-grade-bplus" },
  B:    { bg: "bg-grade-b",     text: "text-grade-b",     ring: "ring-grade-b" },
  "C+": { bg: "bg-grade-cplus", text: "text-grade-cplus", ring: "ring-grade-cplus" },
  C:    { bg: "bg-grade-c",     text: "text-grade-c",     ring: "ring-grade-c" },
  D:    { bg: "bg-grade-d",     text: "text-grade-d",     ring: "ring-grade-d" },
  F:    { bg: "bg-grade-f",     text: "text-grade-f",     ring: "ring-grade-f" },
};

export function gradeColor(grade: Grade) {
  return GRADE_COLORS[grade] ?? GRADE_COLORS.C;
}

// 1-10 dimension score → heatmap color (green → amber → red).
export function scoreColor(score: number): string {
  if (score >= 8) return "bg-grade-aplus";
  if (score >= 6) return "bg-grade-bplus";
  if (score >= 5) return "bg-grade-b";
  if (score >= 4) return "bg-grade-cplus";
  if (score >= 3) return "bg-grade-d";
  return "bg-grade-f";
}

export function scoreRing(score: number): string {
  if (score >= 8) return "ring-grade-aplus/60";
  if (score >= 6) return "ring-grade-bplus/60";
  if (score >= 5) return "ring-grade-b/60";
  if (score >= 4) return "ring-grade-cplus/60";
  if (score >= 3) return "ring-grade-d/60";
  return "ring-grade-f/60";
}
