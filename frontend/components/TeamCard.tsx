import Link from "next/link";

import DataConfidenceBadge from "@/components/DataConfidenceBadge";
import { assetUrl, flagLabel, formatNumber, formatPercent, slugPath } from "@/lib/format";
import type { Team } from "@/lib/types";

type TeamCardProps = {
  team: Team;
};

export default function TeamCard({ team }: TeamCardProps) {
  const flagSrc = assetUrl(team.flag_image_url);

  return (
    <Link
      href={`/teams/${slugPath(team.world_cup_team)}`}
      className="group block rounded-lg border border-white/10 bg-white/[0.045] p-5 shadow-card transition hover:-translate-y-0.5 hover:border-grass-400/50 hover:bg-white/[0.07]"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-pitch-700 text-lg font-black text-white">
            {flagSrc ? (
              <img
                src={flagSrc}
                alt={`${team.world_cup_team} flag`}
                className="h-full w-full object-cover"
              />
            ) : (
              flagLabel(team.flag_code)
            )}
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">{team.world_cup_team}</h2>
            <p className="text-xs uppercase tracking-wide text-slate-400">{team.squad_status.replace("_", " ")}</p>
          </div>
        </div>
        <DataConfidenceBadge value={team.data_confidence} />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-slate-400">StatsBomb shots</p>
          <p className="font-semibold text-white">{formatNumber(team.statsbomb_shots)}</p>
        </div>
        <div>
          <p className="text-slate-400">Total xG</p>
          <p className="font-semibold text-white">{formatNumber(team.total_xg, 1)}</p>
        </div>
        <div>
          <p className="text-slate-400">FBref coverage</p>
          <p className="font-semibold text-white">{formatPercent(team.fbref_coverage_rate)}</p>
        </div>
        <div>
          <p className="text-slate-400">Understat coverage</p>
          <p className="font-semibold text-white">{formatPercent(team.understat_coverage_rate ?? 0)}</p>
        </div>
        <div>
          <p className="text-slate-400">Squad players</p>
          <p className="font-semibold text-white">{formatNumber(team.players_confirmed)}</p>
        </div>
      </div>
    </Link>
  );
}
