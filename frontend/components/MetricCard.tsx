import SourceBadge from "@/components/SourceBadge";

type MetricCardProps = {
  label: string;
  value: string | number;
  detail?: string;
  source?: "statsbomb" | "fbref" | "understat" | "datamb";
  accent?: "statsbomb" | "fbref" | "understat" | "datamb" | "neutral";
};

const accentStyles = {
  statsbomb: "border-source-statsbomb/25",
  fbref: "border-source-fbref/25",
  understat: "border-source-understat/30",
  datamb: "border-source-datamb/30",
  neutral: "border-white/10"
};

export default function MetricCard({ label, value, detail, source, accent = "neutral" }: MetricCardProps) {
  return (
    <div className={`flex min-h-[128px] flex-col rounded-lg border bg-white/[0.04] p-4 shadow-card ${accentStyles[accent]}`}>
      <p className="stat-label leading-5">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</p>
      {detail || source ? (
        <div className="mt-auto space-y-2 pt-3">
          {detail ? <p className="text-sm leading-5 text-slate-400">{detail}</p> : null}
          {source ? (
            <div className="flex flex-wrap gap-2">
              <SourceBadge source={source} muted label={source === "statsbomb" ? "StatsBomb" : undefined} />
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
