import type { Grade } from "@/lib/types";
import { gradeColor } from "@/lib/format";

interface Props {
  grade: Grade;
  size?: "sm" | "md" | "lg" | "xl";
  label?: string;
}

const SIZE_CLASS = {
  sm: "h-7 w-10 text-sm",
  md: "h-10 w-14 text-base",
  lg: "h-16 w-20 text-2xl",
  xl: "h-28 w-32 text-5xl",
};

export function GradeBadge({ grade, size = "md", label }: Props) {
  const colors = gradeColor(grade);
  return (
    <div className="inline-flex flex-col items-center gap-1">
      <div
        className={`${SIZE_CLASS[size]} ${colors.bg} rounded-xl flex items-center justify-center font-display font-bold tracking-tight text-ink-950 shadow-lg ring-1 ring-white/10`}
      >
        {grade}
      </div>
      {label ? (
        <div className="text-[10px] uppercase tracking-[0.16em] text-ink-400">
          {label}
        </div>
      ) : null}
    </div>
  );
}
