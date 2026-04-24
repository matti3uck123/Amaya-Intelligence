interface Props {
  label: string;
  done: number;
  total: number;
  accent?: "copper" | "green";
}

export function ProgressBar({ label, done, total, accent = "copper" }: Props) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  const fill = accent === "green" ? "bg-grade-aplus" : "bg-copper-400";
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-medium uppercase tracking-wider text-ink-400">
          {label}
        </span>
        <span className="font-mono text-ink-300">
          {done} / {total}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-800">
        <div
          className={`h-full ${fill} transition-all duration-500 ease-out`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
