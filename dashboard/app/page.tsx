"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listRatings } from "@/lib/api";
import { formatScore, formatTimestamp, gradeColor, relativeTime } from "@/lib/format";
import type { RatingListItem } from "@/lib/types";
import { GradeBadge } from "@/components/GradeBadge";
import { StatusPill } from "@/components/StatusPill";

export default function HomePage() {
  const [ratings, setRatings] = useState<RatingListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listRatings();
        if (!cancelled) setRatings(data);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      }
    }
    load();
    const id = setInterval(load, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="space-y-8">
      <Hero />
      {error ? (
        <div className="card border-grade-f/40 bg-grade-f/10 p-4 text-sm text-grade-f">
          API unreachable: {error}. Is <code>amaya serve</code> running on port
          8000?
        </div>
      ) : null}
      <section>
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="font-display text-lg font-semibold tracking-tight">
            Ratings
          </h2>
          <span className="text-xs text-ink-500">
            {ratings?.length ?? 0} total · auto-refreshing
          </span>
        </div>

        {ratings === null ? (
          <LoadingList />
        ) : ratings.length === 0 ? (
          <EmptyState />
        ) : (
          <ul className="grid gap-3">
            {ratings.map((r) => (
              <RatingRow key={r.rating_id} rating={r} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Hero() {
  return (
    <div className="card overflow-hidden p-8 sm:p-10">
      <div className="max-w-2xl space-y-3">
        <div className="flex items-center gap-2">
          <span className="chip border border-ink-700 text-ink-300">
            <span className="h-1.5 w-1.5 rounded-full bg-copper-400" />
            Methodology v1.0
          </span>
          <span className="chip border border-ink-700 text-ink-300">
            12 dimensions · 4 chain positions · 4 circuit breakers
          </span>
        </div>
        <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
          The AI Durability Index
        </h1>
        <p className="text-ink-300">
          Evidence-linked ratings of a company&apos;s exposure to
          AI-driven disruption. 16 specialized agents read the data room,
          score 12 dimensions and 4 chain positions, and feed a
          deterministic engine. Every rating is methodology-versioned and
          can be sealed into an immutable provenance bundle.
        </p>
        <div className="flex gap-2 pt-2">
          <Link href="/new" className="btn-primary">
            New rating
          </Link>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="btn-secondary"
          >
            API docs
          </a>
        </div>
      </div>
    </div>
  );
}

function RatingRow({ rating }: { rating: RatingListItem }) {
  const hasGrade = rating.grade !== null;
  return (
    <li>
      <Link
        href={`/ratings/${encodeURIComponent(rating.rating_id)}`}
        className="card card-hoverable flex items-center justify-between gap-4 p-4"
      >
        <div className="flex items-center gap-4">
          {hasGrade ? (
            <GradeBadge grade={rating.grade!} size="md" />
          ) : (
            <div className="flex h-10 w-14 items-center justify-center rounded-xl border border-dashed border-ink-700 text-xs text-ink-500">
              —
            </div>
          )}
          <div>
            <div className="font-display text-base font-semibold leading-tight">
              {rating.company_name}
              {rating.sector ? (
                <span className="ml-2 text-sm font-normal text-ink-400">
                  {rating.sector}
                </span>
              ) : null}
            </div>
            <div className="mt-0.5 flex items-center gap-2 text-xs text-ink-500">
              <span className="font-mono">{rating.rating_id}</span>
              <span>·</span>
              <span>{relativeTime(rating.created_at)}</span>
              <span className="hidden sm:inline">·</span>
              <span className="hidden sm:inline">
                {formatTimestamp(rating.created_at)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {rating.final_score !== null ? (
            <div className="text-right">
              <div className="font-display text-xl font-bold">
                {formatScore(rating.final_score)}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-ink-500">
                / 100
              </div>
            </div>
          ) : null}
          <StatusPill status={rating.status} />
        </div>
      </Link>
    </li>
  );
}

function LoadingList() {
  return (
    <ul className="grid gap-3">
      {[0, 1, 2].map((i) => (
        <li
          key={i}
          className="card h-20 animate-pulse bg-ink-900"
          aria-hidden="true"
        />
      ))}
    </ul>
  );
}

function EmptyState() {
  return (
    <div className="card flex flex-col items-center gap-4 p-10 text-center">
      <div className="text-sm text-ink-400">
        No ratings yet. Upload a data room to produce your first ADI rating.
      </div>
      <Link href="/new" className="btn-primary">
        Rate a company
      </Link>
    </div>
  );
}
