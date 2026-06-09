import type { ReactNode } from "react";

type EmptyDataStateProps = {
  title: string;
  children: ReactNode;
  action?: ReactNode;
};

export default function EmptyDataState({ title, children, action }: EmptyDataStateProps) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.035] p-5 shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-pitch-700 text-sm font-semibold text-slate-200">
          i
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <div className="mt-2 text-sm leading-6 text-slate-400">{children}</div>
          {action ? <div className="mt-4">{action}</div> : null}
        </div>
      </div>
    </div>
  );
}
