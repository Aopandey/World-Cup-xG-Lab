import Link from "next/link";

import EvidenceBadge from "@/components/EvidenceBadge";
import SourceBadge from "@/components/SourceBadge";
import { assetUrl, flagLabel, formatNumber, slugPath, sourceTakeaway, teamHasExternalContext } from "@/lib/format";
import type { Team } from "@/lib/types";

type TeamCardProps = {
  team: Team;
};

export default function TeamCard({ team }: TeamCardProps) {
  const flagSrc = assetUrl(team.flag_image_url);
  const takeaway = sourceTakeaway({
    statsbombShots: team.statsbomb_shots,
    fbrefAvailable: team.fbref_players_matched > 0,
    understatAvailable: Boolean(team.understat_players_matched)
  });
  const sources = [
    team.statsbomb_shots > 0 ? "statsbomb" : null,
    team.fbref_players_matched > 0 ? "fbref" : null,
    team.understat_players_matched ? "understat" : null
  ].filter(Boolean) as Array<"statsbomb" | "fbref" | "understat">;

  return (
    <Link
      href={`/teams/${slugPath(team.world_cup_team)}`}
      className="group block rounded-lg border border-white/10 bg-white/[0.05] p-4 shadow-card transition hover:-translate-y-0.5 hover:border-grass-400/45 hover:bg-white/[0.075] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-400"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-pitch-700 text-lg font-semibold text-white">
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
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold text-white">{team.world_cup_team}</h2>
            <p className="mt-1 text-xs text-slate-400">{takeaway}</p>
          </div>
        </div>
        <EvidenceBadge
          level={team.data_confidence}
          hasHistoricalSample={team.statsbomb_shots > 0}
          hasExternalContext={teamHasExternalContext(team)}
        />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-white/10 bg-black/15 px-3 py-3">
          <p className="stat-label">Past sample shots</p>
          <p className="mt-1 text-xl font-semibold text-white">{formatNumber(team.statsbomb_shots)}</p>
          <p className="mt-1 text-xs text-slate-500">StatsBomb open data</p>
        </div>
        <div className="rounded-lg border border-white/10 bg-black/15 px-3 py-3">
          <p className="stat-label">Past sample xG</p>
          <p className="mt-1 text-xl font-semibold text-white">{formatNumber(team.total_xg, 1)}</p>
          <p className="mt-1 text-xs text-slate-500">Not a 2026 forecast</p>
        </div>
      </div>

      <div className="mt-4 border-t border-white/10 pt-3">
        <p className="stat-label">Sources matched</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {sources.length ? (
            sources.map((source) => <SourceBadge key={source} source={source} />)
          ) : (
            <span className="text-xs text-slate-500">No matched data yet</span>
          )}
        </div>
      </div>
    </Link>
  );
}
