"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { AgentGrid } from "@/components/AgentGrid";
import { ChainChart } from "@/components/ChainChart";
import { CircuitBreakerAlert } from "@/components/CircuitBreakerAlert";
import { DimensionDetail } from "@/components/DimensionDetail";
import { GradeBadge } from "@/components/GradeBadge";
import { ProgressBar } from "@/components/ProgressBar";
import { StatusPill } from "@/components/StatusPill";
import { ApiError, deleteRating, pdfUrl } from "@/lib/api";
import {
  formatPercent,
  formatScore,
  formatTimestamp,
} from "@/lib/format";
import type { Rating } from "@/lib/types";
import { CHAIN_POSITIONS, DIMENSION_CODES } from "@/lib/types";
import { useRatingStream } from "@/lib/useRatingStream";

export default function RatingDetailPage() {
  const params = useParams<{ id: string }>();
  const ratingId = decodeURIComponent(params.id);
  const state = useRatingStream(ratingId);
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const isTerminal = state.status === "done" || state.status === "failed";

  const dimsDone = useMemo(
    () =>
      Object.values(state.dimensions).filter((d) => d.state === "done").length,
    [state.dimensions],
  );
  const chainDone = useMemo(
    () => Object.values(state.chain).filter((d) => d.state === "done").length,
    [state.chain],
  );

  const onDelete = async () => {
    if (!confirm("Delete this rating? This cannot be undone.")) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteRating(ratingId);
      router.push("/");
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : String(err);
      setDeleteError(msg);
      setDeleting(false);
    }
  };

  const companyName =
    state.rating?.input.company_name ??
    (state.status !== "pending" ? "—" : "Loading…");
  const sector = state.rating?.input.sector ?? "";

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <Link
          href="/"
          className="text-xs font-medium uppercase tracking-widest text-ink-500 hover:text-ink-300"
        >
          ← Ratings
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-3">
              <h1 className="font-display text-3xl font-bold tracking-tight">
                {companyName}
              </h1>
              {sector ? (
                <span className="chip border border-ink-700 text-ink-300">
                  {sector}
                </span>
              ) : null}
              <StatusPill status={state.status} />
              {state.connected ? (
                <span className="flex items-center gap-1.5 text-[11px] text-ink-500">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-grade-aplus" />
                  live
                </span>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-ink-500">
              <span className="font-mono">{ratingId}</span>
              {state.sealedDigest ? (
                <>
                  <span>·</span>
                  <span className="inline-flex items-center gap-1 text-copper-300">
                    <SealIcon />
                    sealed{" "}
                    <span className="font-mono text-ink-400">
                      {state.sealedDigest.slice(0, 12)}…
                    </span>
                  </span>
                </>
              ) : null}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {state.rating ? (
              <a
                href={pdfUrl(ratingId)}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary"
                title="Open the one-page PDF leave-behind"
              >
                <PdfIcon />
                PDF
              </a>
            ) : null}
            <button
              onClick={onDelete}
              disabled={deleting}
              className="btn-ghost text-grade-f hover:bg-grade-f/10 disabled:opacity-50"
            >
              {deleting ? "Deleting…" : "Delete"}
            </button>
          </div>
        </div>
        {deleteError ? (
          <div className="card border-grade-f/40 bg-grade-f/10 p-3 text-sm text-grade-f">
            {deleteError}
          </div>
        ) : null}
      </header>

      {state.error ? (
        <div className="card border-grade-f/40 bg-grade-f/10 p-4">
          <div className="font-display text-sm font-semibold uppercase tracking-[0.18em] text-grade-f">
            Pipeline failed
          </div>
          <div className="mt-1.5 text-sm text-ink-200">{state.error}</div>
        </div>
      ) : null}

      {!isTerminal ? (
        <LiveProgress
          state={state}
          dimsDone={dimsDone}
          chainDone={chainDone}
        />
      ) : null}

      {state.rating ? (
        <FinalReport rating={state.rating} />
      ) : (
        <AgentGrid state={state} />
      )}
    </div>
  );
}

function LiveProgress({
  state,
  dimsDone,
  chainDone,
}: {
  state: ReturnType<typeof useRatingStream>;
  dimsDone: number;
  chainDone: number;
}) {
  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <ProgressBar
            label="Dimension agents"
            done={dimsDone}
            total={DIMENSION_CODES.length}
          />
          <ProgressBar
            label="Chain agents"
            done={chainDone}
            total={CHAIN_POSITIONS.length}
            accent="green"
          />
        </div>
        {state.ingest ? (
          <div className="mt-5 grid gap-3 border-t border-ink-800 pt-4 sm:grid-cols-4">
            <Stat label="Files ingested" value={state.ingest.files_ingested} />
            <Stat label="Chunks" value={state.ingest.chunks} />
            <Stat
              label="Sources"
              value={Object.keys(state.ingest.summary).length}
            />
            <Stat
              label="Skipped"
              value={state.ingest.files_skipped.length}
              warn={state.ingest.files_skipped.length > 0}
            />
          </div>
        ) : null}
      </div>
      <AgentGrid state={state} />
    </div>
  );
}

function Stat({
  label,
  value,
  warn,
}: {
  label: string;
  value: number | string;
  warn?: boolean;
}) {
  return (
    <div>
      <div className="label">{label}</div>
      <div
        className={`font-display text-xl font-bold ${warn ? "text-grade-d" : "text-ink-100"}`}
      >
        {value}
      </div>
    </div>
  );
}

function FinalReport({ rating }: { rating: Rating }) {
  const r = rating.result;
  return (
    <div className="space-y-8">
      <div className="card grid gap-6 p-6 sm:grid-cols-[auto_1fr] sm:items-center">
        <GradeBadge grade={r.grade} size="xl" label={r.grade_label} />
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <ScoreStat
              label="Final score"
              value={formatScore(r.final_score)}
              sub="/ 100"
              big
            />
            <ScoreStat
              label="Raw score"
              value={formatScore(r.raw_score)}
              sub="/ 100"
            />
            <ScoreStat
              label="Chain modifier"
              value={`×${r.chain_modifier.toFixed(2)}`}
              sub={r.chain_modifier >= 1 ? "tailwind" : "headwind"}
            />
            <ScoreStat
              label="Adjusted"
              value={formatScore(r.adjusted_score)}
              sub="/ 100"
            />
          </div>
          <p className="text-sm leading-relaxed text-ink-200">
            {r.grade_action}
          </p>
          <div className="flex flex-wrap gap-2 text-xs text-ink-500">
            <span className="chip border border-ink-800">
              methodology {r.methodology_version}
            </span>
            <span className="chip border border-ink-800">
              pipeline {rating.pipeline_version}
            </span>
            <span className="chip border border-ink-800">
              issued {formatTimestamp(rating.issued_at)}
            </span>
          </div>
        </div>
      </div>

      <CircuitBreakerAlert triggers={r.circuit_breakers_triggered} />

      <ChainChart chain={rating.input.chain} modifier={r.chain_modifier} />

      <section>
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="font-display text-lg font-semibold tracking-tight">
            Dimension breakdown
          </h2>
          <span className="text-xs text-ink-500">
            avg confidence{" "}
            {formatPercent(
              rating.input.dimension_scores.reduce(
                (acc, d) => acc + d.confidence,
                0,
              ) / rating.input.dimension_scores.length,
            )}
          </span>
        </div>
        <DimensionDetail scores={rating.input.dimension_scores} />
      </section>

      {rating.input.analyst_notes ? (
        <section className="card p-5">
          <div className="label">Analyst notes</div>
          <p className="mt-2 text-sm leading-relaxed text-ink-200">
            {rating.input.analyst_notes}
          </p>
        </section>
      ) : null}
    </div>
  );
}

function ScoreStat({
  label,
  value,
  sub,
  big,
}: {
  label: string;
  value: string;
  sub?: string;
  big?: boolean;
}) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="flex items-baseline gap-1.5">
        <span
          className={`font-display font-bold text-ink-100 ${big ? "text-4xl" : "text-2xl"}`}
        >
          {value}
        </span>
        {sub ? <span className="text-xs text-ink-500">{sub}</span> : null}
      </div>
    </div>
  );
}

function PdfIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path d="M14 3v5h5" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path
        d="M9 14h1.5a1.5 1.5 0 0 0 0-3H9v6m5-6v6m0-3h2m-2-3h2.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SealIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 2 4 6v6c0 5 3.4 9.5 8 10 4.6-.5 8-5 8-10V6l-8-4z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="m9 12 2 2 4-4"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
