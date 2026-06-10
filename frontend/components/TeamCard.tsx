import Link from "next/link";

import EvidenceBadge from "@/components/EvidenceBadge";
import SourceBadge from "@/components/SourceBadge";
import { assetUrl, flagLabel, slugPath, teamHasExternalContext } from "@/lib/format";
import type { Team } from "@/lib/types";

type TeamCardProps = {
  team: Team;
};

type TeamSource = "statsbomb" | "fbref" | "understat";

export default function TeamCard({ team }: TeamCardProps) {
  const flagSrc = assetUrl(team.flag_image_url);
  const sources = getTeamSources(team);

  return (
    <Link
      href={`/teams/${slugPath(team.world_cup_team)}`}
      className="group block h-full rounded-lg border border-white/10 bg-gradient-to-br from-white/[0.075] to-white/[0.035] p-4 shadow-card transition hover:-translate-y-0.5 hover:border-grass-400/45 hover:bg-white/[0.085] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-400"
    >
      <div className="flex h-full flex-col gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-16 w-20 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-pitch-700 text-xl font-semibold text-white shadow-card">
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
          <div className="min-w-0 flex-1">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <h2 className="text-xl font-semibold text-white">{team.world_cup_team}</h2>
              <EvidenceBadge
                level={team.data_confidence}
                hasHistoricalSample={team.statsbomb_shots > 0}
                hasExternalContext={teamHasExternalContext(team)}
              />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-300">{teamDataRead(team)}</p>
          </div>
        </div>

        <div className="mt-auto border-t border-white/10 pt-3">
          <p className="stat-label">Sources available</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {sources.length ? (
              sources.map((source) => <SourceBadge key={source} source={source} />)
            ) : (
              <span className="text-sm text-slate-500">No matched data yet</span>
            )}
          </div>
          <span className="mt-4 inline-flex text-sm font-semibold text-grass-400 transition group-hover:text-grass-300">
            View profile -&gt;
          </span>
        </div>
      </div>
    </Link>
  );
}

function getTeamSources(team: Team) {
  return [
    team.statsbomb_shots > 0 ? "statsbomb" : null,
    team.fbref_players_matched > 0 ? "fbref" : null,
    team.understat_players_matched ? "understat" : null
  ].filter(Boolean) as TeamSource[];
}

function teamDataRead(team: Team) {
  const hasExternal = teamHasExternalContext(team);

  if (team.statsbomb_shots >= 250 && hasExternal) {
    return "Useful past shot sample plus recent club and league context.";
  }

  if (team.statsbomb_shots >= 50) {
    return hasExternal
      ? "Some past shot evidence with extra club and league context."
      : "Some past shot evidence from open-data matches.";
  }

  if (team.statsbomb_shots > 0) {
    return hasExternal
      ? "Small past shot sample, so club and league context matters more."
      : "Small past shot sample in the current open-data archive.";
  }

  if (hasExternal) {
    return "No past shot sample matched yet, but club and league context is available.";
  }

  return "Squad listed, but matched data is still limited.";
}
