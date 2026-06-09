"use client";

import type { ReactNode } from "react";
import { useState } from "react";

type DetailAccordionProps = {
  title: string;
  summary?: string;
  children: ReactNode;
  defaultOpen?: boolean;
  tone?: "default" | "warning";
};

const toneStyles = {
  default: "border-white/10 bg-white/[0.04]",
  warning: "border-amber-400/35 bg-amber-400/[0.08]"
};

export default function DetailAccordion({
  title,
  summary,
  children,
  defaultOpen = false,
  tone = "default"
}: DetailAccordionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={`rounded-lg border shadow-card ${toneStyles[tone]}`}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="group flex w-full items-start justify-between gap-4 p-4 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-400"
      >
        <span>
          <span className="block text-sm font-semibold text-white">{title}</span>
          {summary ? <span className="mt-1 block text-sm leading-6 text-slate-400">{summary}</span> : null}
        </span>
        <span
          aria-hidden="true"
          className="mt-0.5 inline-flex h-7 min-w-7 items-center justify-center rounded-md border border-white/10 text-slate-300 transition group-hover:border-white/20 group-hover:text-white"
        >
          {open ? <ChevronUpIcon /> : <ChevronDownIcon />}
        </span>
      </button>
      <div
        className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out ${
          open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="overflow-hidden">
          <div className="border-t border-white/10 p-4">{children}</div>
        </div>
      </div>
    </section>
  );
}

function ChevronDownIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

function ChevronUpIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 15l6-6 6 6" />
    </svg>
  );
}
