import type { DataConfidence } from "@/lib/types";

const badgeStyles: Record<DataConfidence, string> = {
  Strong: "border-emerald-400/50 bg-emerald-400/15 text-emerald-200",
  Moderate: "border-sky-400/50 bg-sky-400/15 text-sky-200",
  Limited: "border-amber-400/60 bg-amber-400/15 text-amber-100",
  Unavailable: "border-rose-400/50 bg-rose-400/15 text-rose-100"
};

type DataConfidenceBadgeProps = {
  value: DataConfidence | string;
};

export default function DataConfidenceBadge({ value }: DataConfidenceBadgeProps) {
  const confidence = value as DataConfidence;
  const className = badgeStyles[confidence] ?? badgeStyles.Unavailable;

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.12em] ${className}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {value}
    </span>
  );
}
