import type { ReactNode } from "react";

type QuickReadCardProps = {
  title?: string;
  children: ReactNode;
  tone?: "default" | "warning" | "quiet";
};

const toneStyles = {
  default: "border-grass-400/25 bg-grass-400/[0.08]",
  warning: "border-amber-400/35 bg-amber-400/[0.09]",
  quiet: "border-white/10 bg-white/[0.04]"
};

export default function QuickReadCard({ title = "Quick read", children, tone = "default" }: QuickReadCardProps) {
  return (
    <div className={`rounded-lg border p-4 shadow-card ${toneStyles[tone]}`}>
      <p className="stat-label text-grass-400">{title}</p>
      <div className="mt-2 text-sm leading-6 text-slate-200">{children}</div>
    </div>
  );
}
