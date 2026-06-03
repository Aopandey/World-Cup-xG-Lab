import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  subtitle: string;
  children?: ReactNode;
};

export default function PageHeader({ eyebrow, title, subtitle, children }: PageHeaderProps) {
  return (
    <header className="space-y-4">
      {eyebrow ? <p className="text-sm font-semibold uppercase tracking-wide text-grass-400">{eyebrow}</p> : null}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl">
          <h1 className="text-4xl font-black tracking-tight text-white md:text-5xl">{title}</h1>
          <p className="mt-3 max-w-3xl text-base leading-7 text-slate-300">{subtitle}</p>
        </div>
        {children ? <div className="shrink-0">{children}</div> : null}
      </div>
    </header>
  );
}
