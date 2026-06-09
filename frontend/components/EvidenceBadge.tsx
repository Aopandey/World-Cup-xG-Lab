import { evidenceLabel, evidenceLevelFromConfidence } from "@/lib/format";
import type { DataConfidence, EvidenceLevel } from "@/lib/types";

const badgeStyles: Record<EvidenceLevel, string> = {
  strong: "border-emerald-400/50 bg-emerald-400/15 text-emerald-100",
  moderate: "border-sky-400/50 bg-sky-400/15 text-sky-100",
  limited: "border-amber-400/60 bg-amber-400/15 text-amber-100",
  unavailable: "border-slate-400/30 bg-slate-400/10 text-slate-200"
};

type EvidenceBadgeProps = {
  level?: EvidenceLevel | DataConfidence | string;
  hasHistoricalSample?: boolean;
  hasExternalContext?: boolean;
  label?: string;
};

export default function EvidenceBadge({
  level = "unavailable",
  hasHistoricalSample = false,
  hasExternalContext = false,
  label
}: EvidenceBadgeProps) {
  const normalizedLevel = evidenceLevelFromConfidence(level);
  const displayLabel = label ?? evidenceLabel(level, { hasHistoricalSample, hasExternalContext });

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.12em] ${badgeStyles[normalizedLevel]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {displayLabel}
    </span>
  );
}
