import type { ReactNode } from "react";

type SampleWarningProps = {
  children?: ReactNode;
};

export default function SampleWarning({ children }: SampleWarningProps) {
  return (
    <div className="rounded-lg border border-amber-400/45 bg-amber-400/10 p-4 text-sm text-amber-100">
      {children ?? "Small sample size: scoring-zone patterns may not be reliable."}
    </div>
  );
}
