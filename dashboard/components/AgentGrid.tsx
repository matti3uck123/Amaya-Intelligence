"use client";

import type {
  AgentTileState,
  StreamState,
} from "@/lib/useRatingStream";
import {
  CHAIN_POSITION_NAMES,
  DIMENSION_LAYER,
  DIMENSION_NAMES,
  LAYER_NAMES,
  type ChainPosition,
  type DimensionCode,
} from "@/lib/types";

interface Props {
  state: StreamState;
}

/**
 * Renders the 12 dimension agents grouped by their scoring layer
 * (External / Internal / Adaptive) plus the 4 chain-position agents.
 * Each tile reflects live SSE state and, when complete, shows the score.
 */
export function AgentGrid({ state }: Props) {
  const score = (code: DimensionCode): number | null => {
    const dim = state.rating?.input.dimension_scores.find(
      (d) => d.code === code,
    );
    return dim ? dim.score : null;
  };
  const chainScore = (pos: ChainPosition): number | null => {
    const p = state.rating?.input.chain.positions.find(
      (c) => c.position === pos,
    );
    return p ? p.score : null;
  };

  const byLayer: Record<string, DimensionCode[]> = {
    external: [],
    internal: [],
    adaptive: [],
  };
  for (const [code, layer] of Object.entries(DIMENSION_LAYER)) {
    byLayer[layer].push(code as DimensionCode);
  }

  return (
    <div className="space-y-6">
      {(["external", "internal", "adaptive"] as const).map((layer) => (
        <section key={layer}>
          <LayerHeading layer={layer} />
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {byLayer[layer].map((code) => (
              <AgentTile
                key={code}
                code={code}
                title={DIMENSION_NAMES[code]}
                tile={state.dimensions[code]}
                score={score(code)}
              />
            ))}
          </div>
        </section>
      ))}

      <section>
        <h3 className="flex items-baseline justify-between">
          <span className="font-display text-sm font-semibold uppercase tracking-[0.18em] text-ink-300">
            Chain position
          </span>
          <span className="text-xs text-ink-500">modifier 0.70 – 1.15</span>
        </h3>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(Object.keys(CHAIN_POSITION_NAMES) as ChainPosition[]).map((pos) => (
            <AgentTile
              key={pos}
              code={pos}
              title={CHAIN_POSITION_NAMES[pos]}
              tile={state.chain[pos]}
              score={chainScore(pos)}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function LayerHeading({
  layer,
}: {
  layer: "external" | "internal" | "adaptive";
}) {
  const weight = { external: "40%", internal: "35%", adaptive: "25%" }[layer];
  return (
    <h3 className="flex items-baseline justify-between">
      <span className="font-display text-sm font-semibold uppercase tracking-[0.18em] text-ink-300">
        {LAYER_NAMES[layer]}
      </span>
      <span className="text-xs text-ink-500">weight {weight}</span>
    </h3>
  );
}

function AgentTile({
  code,
  title,
  tile,
  score,
}: {
  code: string;
  title: string;
  tile: AgentTileState | undefined;
  score: number | null;
}) {
  const state = tile?.state ?? "pending";
  const borderState = {
    pending: "border-ink-800",
    running: "border-copper-500/60 shadow-glow animate-pulse_ring",
    done: "border-ink-700",
    error: "border-grade-f/60",
  }[state];

  const scoreColor = (s: number): string => {
    if (s >= 8) return "text-grade-aplus";
    if (s >= 6) return "text-grade-bplus";
    if (s >= 5) return "text-grade-b";
    if (s >= 4) return "text-grade-cplus";
    if (s >= 3) return "text-grade-d";
    return "text-grade-f";
  };

  return (
    <div
      className={`card card-hoverable relative flex flex-col gap-2 p-3.5 ${borderState}`}
    >
      <div className="flex items-start justify-between">
        <div className="font-mono text-[11px] uppercase tracking-wider text-ink-400">
          {code}
        </div>
        <TileStateDot state={state} />
      </div>
      <div className="text-xs leading-snug text-ink-200">{title}</div>
      <div className="mt-auto flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-widest text-ink-500">
          {state === "done" ? "score" : state === "running" ? "analyzing…" : state === "error" ? "failed" : "queued"}
        </span>
        {score !== null ? (
          <span
            className={`font-display text-2xl font-bold ${scoreColor(score)}`}
          >
            {score}
          </span>
        ) : (
          <span className="text-ink-600">—</span>
        )}
      </div>
    </div>
  );
}

function TileStateDot({ state }: { state: AgentTileState["state"] }) {
  const cls = {
    pending: "bg-ink-600",
    running: "bg-copper-400 animate-pulse",
    done: "bg-grade-aplus",
    error: "bg-grade-f",
  }[state];
  return <span className={`h-2 w-2 rounded-full ${cls}`} />;
}
