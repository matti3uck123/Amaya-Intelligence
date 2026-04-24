import type { CircuitBreakerTrigger } from "@/lib/types";

export function CircuitBreakerAlert({
  triggers,
}: {
  triggers: CircuitBreakerTrigger[];
}) {
  if (triggers.length === 0) return null;
  return (
    <div className="card border-grade-f/40 bg-grade-f/10 p-4">
      <div className="flex items-center gap-2 text-grade-f">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="font-display text-sm font-semibold uppercase tracking-[0.18em]">
          Circuit breakers triggered
        </span>
      </div>
      <ul className="mt-3 space-y-2">
        {triggers.map((t) => (
          <li
            key={t.code}
            className="flex items-baseline justify-between gap-3 text-sm"
          >
            <div>
              <span className="font-mono font-semibold text-grade-f">
                {t.code}
              </span>{" "}
              <span className="text-ink-200">{t.description}</span>
            </div>
            <span className="font-mono text-xs text-ink-400">
              caps score at {t.cap}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
