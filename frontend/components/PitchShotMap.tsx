import type { ShotPoint } from "@/lib/types";

type PitchShotMapProps = {
  shots?: ShotPoint[];
  emptyMessage?: string;
};

function scaleDot(shot: ShotPoint) {
  const xg = Number(shot.predicted_xg ?? 0);
  return 1.2 + Math.min(xg * 9, 4.5);
}

export default function PitchShotMap({
  shots = [],
  emptyMessage = "No reliable shot-location data available for this player."
}: PitchShotMapProps) {
  const validShots = shots.filter(
    (shot) => typeof shot.shot_x === "number" && typeof shot.shot_y === "number"
  );

  if (!validShots.length) {
    return (
      <div className="flex min-h-[280px] items-center justify-center rounded-lg border border-dashed border-white/15 bg-white/[0.035] p-6 text-center text-sm text-slate-300">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-white/10 bg-pitch-900 p-4 shadow-card">
      <svg viewBox="0 0 120 80" role="img" aria-label="Shot map pitch" className="h-auto w-full">
        <rect x="0" y="0" width="120" height="80" fill="#0b2a2f" />
        <rect x="2" y="2" width="116" height="76" fill="none" stroke="#d9fff0" strokeOpacity="0.65" strokeWidth="0.7" />
        <line x1="60" y1="2" x2="60" y2="78" stroke="#d9fff0" strokeOpacity="0.5" strokeWidth="0.5" />
        <circle cx="60" cy="40" r="9" fill="none" stroke="#d9fff0" strokeOpacity="0.45" strokeWidth="0.5" />
        <rect x="102" y="22" width="16" height="36" fill="none" stroke="#d9fff0" strokeOpacity="0.55" strokeWidth="0.5" />
        <rect x="112" y="30" width="6" height="20" fill="none" stroke="#d9fff0" strokeOpacity="0.55" strokeWidth="0.5" />
        <line x1="120" y1="36" x2="120" y2="44" stroke="#f5c451" strokeWidth="1.2" />

        {validShots.map((shot, index) => {
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
    </div>
  );
}
