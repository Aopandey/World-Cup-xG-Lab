type SummaryTone = "default" | "warning" | "quiet";

type SummaryCardProps = {
  eyebrow: string;
  title: string;
  paragraphs: string[];
  takeaway: string;
  tone?: SummaryTone;
};

const toneStyles: Record<SummaryTone, string> = {
  default: "border-grass-400/25 bg-grass-400/[0.08]",
  warning: "border-amber-400/35 bg-amber-400/[0.09]",
  quiet: "border-white/10 bg-white/[0.04]"
};

export default function SummaryCard({
  eyebrow,
  title,
  paragraphs,
  takeaway,
  tone = "default"
}: SummaryCardProps) {
  return (
    <section className={`rounded-lg border p-5 shadow-card ${toneStyles[tone]}`}>
      <p className="stat-label text-grass-400">{eyebrow}</p>
      <h2 className="mt-2 text-xl font-semibold text-white">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-6 text-slate-200">
        {paragraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
      <div className="mt-4 rounded-lg border border-white/10 bg-black/15 p-3 text-sm leading-6 text-slate-200">
        {takeaway}
      </div>
    </section>
  );
}
