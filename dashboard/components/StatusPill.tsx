import type { JobStatus } from "@/lib/types";

const STATUS_STYLES: Record<
  JobStatus,
  { label: string; bg: string; dot: string }
> = {
  pending: {
    label: "Queued",
    bg: "bg-ink-800 text-ink-300",
    dot: "bg-ink-400",
  },
  ingesting: {
    label: "Ingesting",
    bg: "bg-copper-500/15 text-copper-300",
    dot: "bg-copper-400 animate-pulse",
  },
  rating: {
    label: "Agents running",
    bg: "bg-copper-500/15 text-copper-300",
    dot: "bg-copper-400 animate-pulse",
  },
  scoring: {
    label: "Scoring",
    bg: "bg-copper-500/15 text-copper-300",
    dot: "bg-copper-400 animate-pulse",
  },
  done: {
    label: "Complete",
    bg: "bg-grade-aplus/15 text-grade-aplus",
    dot: "bg-grade-aplus",
  },
  failed: {
    label: "Failed",
    bg: "bg-grade-f/15 text-grade-f",
    dot: "bg-grade-f",
  },
};

export function StatusPill({ status }: { status: JobStatus }) {
  const s = STATUS_STYLES[status];
  return (
    <span className={`chip ${s.bg}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}
