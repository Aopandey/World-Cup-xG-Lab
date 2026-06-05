import type { ReactNode } from "react";

type DataStateCalloutProps = {
  title: string;
  children: ReactNode;
  tone?: "info" | "warning" | "neutral";
};

const toneStyles = {
  info: "border-source-statsbomb/35 bg-source-statsbomb/10 text-sky-100",
  warning: "border-amber-400/40 bg-amber-400/10 text-amber-100",
  neutral: "border-white/10 bg-white/[0.04] text-slate-300"
};

export default function DataStateCallout({ title, children, tone = "neutral" }: DataStateCalloutProps) {
  return (
    <div className={`rounded-lg border p-4 ${toneStyles[tone]}`}>
      <p className="text-sm font-semibold text-white">{title}</p>
      <div className="mt-2 text-sm leading-6">{children}</div>
    </div>
  );
}

