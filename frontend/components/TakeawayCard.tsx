type TakeawayCardProps = {
  label: string;
  value: string;
  detail?: string;
};

export default function TakeawayCard({ label, value, detail }: TakeawayCardProps) {
  return (
    <div className="surface-inset p-4">
      <p className="stat-label">{label}</p>
      <p className="mt-2 text-base font-semibold text-white">{value}</p>
      {detail ? <p className="mt-2 text-sm leading-6 text-slate-400">{detail}</p> : null}
    </div>
  );
}

