type StatCardProps = {
  label: string;
  value: string | number;
  detail?: string;
};

export default function StatCard({ label, value, detail }: StatCardProps) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4 shadow-card">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-bold text-white">{value}</p>
      {detail ? <p className="mt-1 text-sm text-slate-400">{detail}</p> : null}
    </div>
  );
}
