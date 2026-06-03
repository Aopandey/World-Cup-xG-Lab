import Link from "next/link";

import DataConfidenceBadge from "@/components/DataConfidenceBadge";
import { formatNumber, initials, slugPath } from "@/lib/format";
import type { PlayerProfile } from "@/lib/types";

type PlayerCardProps = {
  player: PlayerProfile;
};

export default function PlayerCard({ player }: PlayerCardProps) {
  return (
    <Link
      href={`/players/${slugPath(player.player)}`}
      className="block rounded-lg border border-white/10 bg-white/[0.04] p-4 transition hover:border-grass-400/50 hover:bg-white/[0.07]"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-pitch-700 text-sm font-black text-white">
          {initials(player.player)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="truncate font-semibold text-white">{player.player}</h3>
              <p className="mt-0.5 text-xs text-slate-400">{player.position_group ?? "Position unknown"}</p>
            </div>
            <DataConfidenceBadge value={player.data_confidence} />
          </div>
          <p className="mt-3 line-clamp-2 text-sm text-slate-300">
            {player.club ?? "Club unknown"} - {player.league ?? "League unknown"}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-300">
            <span className="rounded-lg bg-white/[0.06] px-2 py-1">{formatNumber(player.statsbomb_shots)} shots</span>
            <span className="rounded-lg bg-white/[0.06] px-2 py-1">
              {player.fbref_available ? "FBref context" : "No FBref context"}
            </span>
            <span className="rounded-lg bg-white/[0.06] px-2 py-1">
              {player.understat_available ? "Understat xG" : "No Understat"}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
