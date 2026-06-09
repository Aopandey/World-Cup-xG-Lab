"use client";

import { useState } from "react";

import SourceLegend from "@/components/SourceLegend";

type CollapsibleSourceLegendProps = {
  defaultOpen?: boolean;
};

export default function CollapsibleSourceLegend({ defaultOpen = false }: CollapsibleSourceLegendProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="surface-inset p-4">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-4 text-left"
      >
        <span>
          <span className="stat-label">Source guide</span>
          <span className="mt-1 block text-sm text-slate-300">What each data layer means</span>
        </span>
        <span className="rounded-md border border-white/10 px-2 py-1 text-xs text-slate-300">
          {open ? "Hide" : "Show"}
        </span>
      </button>
      {open ? <div className="mt-4"><SourceLegend compact /></div> : null}
    </div>
  );
}
