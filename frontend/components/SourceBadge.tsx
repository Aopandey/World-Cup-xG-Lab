type Source = "statsbomb" | "fbref" | "understat";

const sourceStyles: Record<Source, string> = {
  statsbomb: "border-source-statsbomb/40 bg-source-statsbomb/10 text-sky-100",
  fbref: "border-source-fbref/40 bg-source-fbref/10 text-emerald-100",
  understat: "border-source-understat/45 bg-source-understat/10 text-amber-100"
};

const sourceLabels: Record<Source, string> = {
  statsbomb: "StatsBomb",
  fbref: "FBref",
  understat: "Understat"
};

type SourceBadgeProps = {
  source: Source;
  label?: string;
  muted?: boolean;
};

export default function SourceBadge({ source, label, muted = false }: SourceBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.12em] ${
        muted ? "border-white/10 bg-white/[0.035] text-slate-400" : sourceStyles[source]
      }`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {label ?? sourceLabels[source]}
    </span>
  );
}

