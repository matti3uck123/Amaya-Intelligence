"use client";

import { useEffect, useRef, useState } from "react";
import { eventsUrl, getRating } from "./api";
import type {
  DimensionCode,
  JobStatus,
  Rating,
  RatingEvent,
  RatingStatus,
} from "./types";
import { CHAIN_POSITIONS, DIMENSION_CODES } from "./types";

export type AgentState = "pending" | "running" | "done" | "error";

export interface AgentTileState {
  name: string;
  state: AgentState;
}

export interface IngestInfo {
  files_ingested: number;
  files_skipped: string[];
  chunks: number;
  summary: Record<string, number>;
}

export interface StreamState {
  status: JobStatus;
  rating: Rating | null;
  error: string | null;
  ingest: IngestInfo | null;
  sealedDigest: string | null;
  dimensions: Record<string, AgentTileState>;
  chain: Record<string, AgentTileState>;
  connected: boolean;
}

function buildInitialAgents(
  names: readonly string[],
): Record<string, AgentTileState> {
  return Object.fromEntries(
    names.map((n) => [n, { name: n, state: "pending" as const }]),
  );
}

function applyEvent(state: StreamState, ev: RatingEvent): StreamState {
  switch (ev.type) {
    case "status":
      return { ...state, status: ev.status };
    case "ingest":
      return {
        ...state,
        ingest: {
          files_ingested: ev.files_ingested,
          files_skipped: ev.files_skipped,
          chunks: ev.chunks,
          summary: ev.summary,
        },
      };
    case "agent": {
      const isChain = (CHAIN_POSITIONS as readonly string[]).includes(ev.name);
      const bucket = isChain ? "chain" : "dimensions";
      const next: AgentState =
        ev.event === "start"
          ? "running"
          : ev.event === "done"
            ? "done"
            : "error";
      return {
        ...state,
        [bucket]: {
          ...state[bucket],
          [ev.name]: { name: ev.name, state: next },
        },
      } as StreamState;
    }
    case "rating":
      return { ...state, rating: ev.rating };
    case "sealed":
      return { ...state, sealedDigest: ev.digest };
    case "error":
      return { ...state, error: ev.error, status: "failed" };
  }
}

/**
 * Subscribes to the rating's SSE event stream and reconstructs UI state.
 *
 * Primes itself with one REST fetch of /ratings/{id} so a page reload
 * after completion still shows the final grade instantly, rather than
 * flickering through pending→done.
 */
export function useRatingStream(ratingId: string): StreamState {
  const [state, setState] = useState<StreamState>({
    status: "pending",
    rating: null,
    error: null,
    ingest: null,
    sealedDigest: null,
    dimensions: buildInitialAgents(DIMENSION_CODES),
    chain: buildInitialAgents(CHAIN_POSITIONS),
    connected: false,
  });
  const closedRef = useRef(false);

  useEffect(() => {
    closedRef.current = false;
    let cancelled = false;

    // Seed from REST so the UI isn't empty for the round-trip.
    getRating(ratingId)
      .then((status: RatingStatus) => {
        if (cancelled) return;
        setState((prev) => ({
          ...prev,
          status: status.status,
          rating: status.rating,
          error: status.error,
          sealedDigest: status.sealed_digest,
        }));
      })
      .catch(() => {
        /* 404s and friends — SSE will surface the real issue */
      });

    const es = new EventSource(eventsUrl(ratingId));

    es.onopen = () => {
      if (!cancelled) setState((p) => ({ ...p, connected: true }));
    };

    es.onmessage = (evt) => {
      if (!evt.data) return;
      try {
        const payload = JSON.parse(evt.data) as RatingEvent;
        setState((prev) => applyEvent(prev, payload));
      } catch {
        // swallow — malformed frames shouldn't crash the dashboard
      }
    };

    es.onerror = () => {
      // EventSource auto-reconnects; we only mark disconnected if we
      // haven't explicitly closed. For terminal jobs the server closes
      // the stream after replaying history, which surfaces here too.
      if (!closedRef.current) setState((p) => ({ ...p, connected: false }));
    };

    return () => {
      cancelled = true;
      closedRef.current = true;
      es.close();
    };
  }, [ratingId]);

  return state;
}

export function dimensionAgents(
  state: StreamState,
): Array<AgentTileState & { code: DimensionCode }> {
  return DIMENSION_CODES.map((code) => ({
    ...state.dimensions[code],
    code,
  }));
}

export function chainAgents(state: StreamState): AgentTileState[] {
  return CHAIN_POSITIONS.map((p) => state.chain[p]);
}
