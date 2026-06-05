"use client";

import { useMemo, useState } from "react";

import { formatNumber } from "@/lib/format";
import type { ShotPoint } from "@/lib/types";

type PitchShotMapProps = {
  shots?: ShotPoint[];
  emptyMessage?: string;
  sampleSize?: number;
  title?: string;
};

const modes = ["All shots", "Goals", "High xG"];

function scaleDot(shot: ShotPoint) {
  const xg = Number(shot.predicted_xg ?? 0);
  return 1.2 + Math.min(xg * 9, 4.5);
}

export default function PitchShotMap({
  shots = [],
  emptyMessage = "No reliable shot-location data available for this player.",
  sampleSize,
  title = "Shot Map"
}: PitchShotMapProps) {
  const [mode, setMode] = useState("All shots");
  const validShots = shots.filter(
    (shot) => typeof shot.shot_x === "number" && typeof shot.shot_y === "number"
  );

  const filteredShots = useMemo(() => {
    if (mode === "Goals") {
      return validShots.filter((shot) => Boolean(shot.actual_goal));
    }

    if (mode === "High xG") {
      return validShots.filter((shot) => Number(shot.predicted_xg ?? 0) >= 0.2);
    }

    return validShots;
  }, [mode, validShots]);

  if (!validShots.length) {
    return (
      <div className="surface-inset p-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <MiniPitch />
          <div>
            <p className="text-sm font-semibold text-white">{title}</p>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">{emptyMessage}</p>
            <p className="mt-2 text-xs text-slate-500">
              Historical sample size: {typeof sampleSize === "number" ? formatNumber(sampleSize) : "not exposed"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-white/10 bg-pitch-900 p-4 shadow-card">
      <div className="mb-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold text-white">{title}</p>
          <p className="text-xs text-slate-400">{formatNumber(validShots.length)} shots with coordinates</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {modes.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setMode(option)}
              className={`rounded-md border px-2.5 py-1.5 text-xs transition ${
                mode === option
                  ? "border-grass-400/60 bg-grass-400/15 text-white"
                  : "border-white/10 bg-white/[0.035] text-slate-300 hover:bg-white/[0.06]"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      <svg viewBox="0 0 120 80" role="img" aria-label="Shot map pitch" className="h-auto w-full">
        <rect x="0" y="0" width="120" height="80" fill="#0b2a2f" />
        <rect x="2" y="2" width="116" height="76" fill="none" stroke="#d9fff0" strokeOpacity="0.65" strokeWidth="0.7" />
        <line x1="60" y1="2" x2="60" y2="78" stroke="#d9fff0" strokeOpacity="0.5" strokeWidth="0.5" />
        <circle cx="60" cy="40" r="9" fill="none" stroke="#d9fff0" strokeOpacity="0.45" strokeWidth="0.5" />
        <rect x="102" y="22" width="16" height="36" fill="none" stroke="#d9fff0" strokeOpacity="0.55" strokeWidth="0.5" />
        <rect x="112" y="30" width="6" height="20" fill="none" stroke="#d9fff0" strokeOpacity="0.55" strokeWidth="0.5" />
        <line x1="120" y1="36" x2="120" y2="44" stroke="#f5c451" strokeWidth="1.2" />

        {filteredShots.map((shot, index) => {
          const isGoal = Boolean(shot.actual_goal);
          const highXg = Number(shot.predicted_xg ?? 0) >= 0.2;
          return (
            <circle
              key={`${shot.shot_x}-${shot.shot_y}-${index}`}
              cx={shot.shot_x ?? 0}
              cy={shot.shot_y ?? 0}
              r={isGoal || highXg ? scaleDot(shot) + 0.8 : scaleDot(shot)}
              fill={isGoal || highXg ? "#f5c451" : "#69b7ff"}
              fillOpacity={isGoal ? 0.95 : 0.62}
              stroke="#ffffff"
              strokeOpacity="0.7"
              strokeWidth="0.3"
            />
          );
        })}
      </svg>

      <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-400">
        <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-source-statsbomb" /> Shot</span>
        <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-source-understat" /> Goal or high xG</span>
      </div>
    </div>
  );
}
function MiniPitch() {
  return (
    <svg viewBox="0 0 120 80" className="h-24 w-36 shrink-0 rounded-md border border-white/10 bg-pitch-900">
      <rect x="6" y="6" width="108" height="68" fill="none" stroke="#d9fff0" strokeOpacity="0.45" strokeWidth="1" />
      <line x1="60" y1="6" x2="60" y2="74" stroke="#d9fff0" strokeOpacity="0.3" strokeWidth="1" />
      <rect x="98" y="24" width="16" height="32" fill="none" stroke="#d9fff0" strokeOpacity="0.35" strokeWidth="1" />
      <line x1="120" y1="36" x2="120" y2="44" stroke="#f5c451" strokeWidth="2" />
    </svg>
  );
}
