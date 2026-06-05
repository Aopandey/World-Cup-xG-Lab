type StatCardProps = {
  label: string;
  value: string | number;
  detail?: string;
  accent?: "statsbomb" | "fbref" | "understat" | "neutral";
};

const accentStyles = {
  statsbomb: "border-source-statsbomb/25",
  fbref: "border-source-fbref/25",
  understat: "border-source-understat/30",
  neutral: "border-white/10"
};

export default function StatCard({ label, value, detail, accent = "neutral" }: StatCardProps) {
  return (
    <div className={`rounded-lg border bg-white/[0.04] p-4 shadow-card ${accentStyles[accent]}`}>
      <p className="stat-label">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-white">{value}</p>
      {detail ? <p className="mt-1 text-sm leading-5 text-slate-400">{detail}</p> : null}
    </div>
  );
}
