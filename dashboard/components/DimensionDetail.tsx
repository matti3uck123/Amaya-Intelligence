import type { DimensionCode, DimensionScore } from "@/lib/types";
import {
  DIMENSION_LAYER,
  DIMENSION_NAMES,
  LAYER_NAMES,
  LAYER_WEIGHTS,
} from "@/lib/types";
import { scoreColor } from "@/lib/format";

export function DimensionDetail({
  scores,
}: {
  scores: DimensionScore[];
}) {
  const byLayer = {
    external: [] as DimensionScore[],
    internal: [] as DimensionScore[],
    adaptive: [] as DimensionScore[],
  };
  for (const s of scores) {
    byLayer[DIMENSION_LAYER[s.code]].push(s);
  }

  return (
    <div className="space-y-6">
      {(["external", "internal", "adaptive"] as const).map((layer) => (
        <div key={layer}>
          <div className="mb-3 flex items-baseline justify-between">
            <h3 className="font-display text-sm font-semibold uppercase tracking-[0.18em] text-ink-300">
              {LAYER_NAMES[layer]}
            </h3>
            <span className="text-xs text-ink-500">
              weight {(LAYER_WEIGHTS[layer] * 100).toFixed(0)}%
            </span>
          </div>
          <div className="grid gap-2">
            {byLayer[layer].map((s) => (
              <DimensionRow key={s.code} score={s} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function DimensionRow({ score }: { score: DimensionScore }) {
  const barWidth = `${score.score * 10}%`;
  const barColor = scoreColor(score.score);
  const confidencePct = Math.round(score.confidence * 100);

  return (
    <details className="card group p-4 transition-colors hover:border-ink-700">
      <summary className="flex cursor-pointer items-center gap-4 list-none">
        <div className="w-16 font-mono text-xs font-semibold uppercase text-ink-300">
          {score.code}
        </div>
        <div className="flex-1">
          <div className="text-sm text-ink-100">
            {DIMENSION_NAMES[score.code as DimensionCode]}
          </div>
          <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-ink-800">
            <div
              className={`h-full ${barColor} transition-all`}
              style={{ width: barWidth }}
            />
          </div>
        </div>
        <div className="w-16 text-right">
          <div className="font-display text-xl font-bold text-ink-100">
            {score.score}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-ink-500">
            conf {confidencePct}%
          </div>
        </div>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          className="text-ink-500 transition-transform group-open:rotate-180"
          aria-hidden
        >
          <path
            d="m6 9 6 6 6-6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </summary>
      <div className="mt-4 space-y-3 border-t border-ink-800 pt-4 text-sm">
        <p className="leading-relaxed text-ink-200">{score.rationale}</p>
        {score.evidence.length > 0 ? (
          <div>
            <div className="label">Evidence</div>
            <ul className="space-y-1.5">
              {score.evidence.map((e, i) => (
                <li
                  key={i}
                  className="flex items-baseline gap-2 text-xs text-ink-300"
                >
                  <span className="font-mono text-ink-500">[{i + 1}]</span>
                  <span className="font-mono text-ink-500">{e.kind}</span>
                  <span className="truncate">{e.locator}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="text-xs text-ink-500">
            No structured evidence references recorded.
          </div>
        )}
      </div>
    </details>
  );
}
