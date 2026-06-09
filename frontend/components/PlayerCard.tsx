import Link from "next/link";

import AvailabilityStrip from "@/components/AvailabilityStrip";
import DataConfidenceBadge from "@/components/DataConfidenceBadge";
import { formatNumber, initials, playerHasExternalContext, shortLeagueName, slugPath } from "@/lib/format";
import type { PlayerProfile } from "@/lib/types";

type PlayerCardProps = {
  player: PlayerProfile;
};

export default function PlayerCard({ player }: PlayerCardProps) {
  return (
    <Link
      href={`/players/${slugPath(player.player)}`}
      className="block rounded-lg border border-white/10 bg-white/[0.045] p-4 transition hover:-translate-y-0.5 hover:border-grass-400/45 hover:bg-white/[0.07]"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-pitch-700 text-sm font-semibold text-white">
          {initials(player.player)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="truncate font-semibold text-white">{player.player}</h3>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="rounded-md border border-white/10 bg-white/[0.045] px-2 py-1 text-xs text-slate-300">
                  {player.position_group ?? player.position ?? "Position unknown"}
                </span>
                <DataConfidenceBadge
                  value={player.data_confidence}
                  hasHistoricalSample={player.statsbomb_shots > 0}
                  hasExternalContext={playerHasExternalContext(player)}
                />
              </div>
            </div>
          </div>
          <p className="mt-3 line-clamp-2 text-sm text-slate-300">
            {player.club ?? "Club unknown"} - {shortLeagueName(player.league)}
          </p>
          <div className="mt-3">
            <AvailabilityStrip
              compact
              statsbombShots={player.statsbomb_shots}
              fbrefAvailable={player.fbref_available}
              understatAvailable={Boolean(player.understat_available)}
              datambAvailable={Boolean(player.datamb_25_26?.available)}
            />
          </div>
          {player.statsbomb_shots > 0 ? (
            <p className="mt-3 text-xs text-slate-400">
              {formatNumber(player.total_xg, 2)} past sample xG from {formatNumber(player.statsbomb_shots)} past sample shots
            </p>
          ) : null}
        </div>
      </div>
    </Link>
  );
}
