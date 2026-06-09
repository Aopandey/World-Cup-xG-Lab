import { formatPercent } from "@/lib/format";

type CoverageProgressBarProps = {
  label: string;
  value: number;
  detail?: string;
  accent?: "statsbomb" | "fbref" | "understat" | "datamb" | "neutral";
};

const barStyles = {
  statsbomb: "bg-source-statsbomb",
  fbref: "bg-source-fbref",
  understat: "bg-source-understat",
  datamb: "bg-source-datamb",
  neutral: "bg-grass-400"
};

export default function CoverageProgressBar({ label, value, detail, accent = "neutral" }: CoverageProgressBarProps) {
  const clamped = Math.max(0, Math.min(1, Number(value) || 0));

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-white">{label}</p>
        <span className="text-sm font-semibold text-white">{formatPercent(clamped, 1)}</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/[0.08]">
        <div className={`h-full rounded-full ${barStyles[accent]}`} style={{ width: `${clamped * 100}%` }} />
      </div>
      {detail ? <p className="mt-2 text-xs leading-5 text-slate-400">{detail}</p> : null}
    </div>
  );
}
