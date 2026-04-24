import type { ChainAssessment } from "@/lib/types";
import { CHAIN_POSITION_NAMES } from "@/lib/types";
import { scoreColor } from "@/lib/format";

export function ChainChart({
  chain,
  modifier,
}: {
  chain: ChainAssessment;
  modifier: number;
}) {
  const pillColor = modifier >= 1.0 ? "text-grade-aplus" : "text-grade-d";
  const direction = modifier >= 1.0 ? "tailwind" : "headwind";

  return (
    <div className="card p-5">
      <div className="flex items-baseline justify-between">
        <h3 className="font-display text-sm font-semibold uppercase tracking-[0.18em] text-ink-300">
          Chain modifier
        </h3>
        <div className="flex items-baseline gap-2">
          <span className="text-xs text-ink-500">{direction}</span>
          <span className={`font-display text-2xl font-bold ${pillColor}`}>
            ×{modifier.toFixed(2)}
          </span>
        </div>
      </div>
      <div className="mt-5 grid gap-3">
        {chain.positions.map((p) => {
          const width = `${p.score * 10}%`;
          return (
            <div key={p.position} className="flex items-center gap-3">
              <div className="w-44 text-sm text-ink-200">
                {CHAIN_POSITION_NAMES[p.position]}
              </div>
              <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-ink-800">
                <div
                  className={`h-full ${scoreColor(p.score)}`}
                  style={{ width }}
                />
              </div>
              <div className="w-8 text-right font-display text-base font-bold text-ink-100">
                {p.score}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
