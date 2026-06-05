import PlayerCard from "@/components/PlayerCard";
import type { PlayerProfile } from "@/lib/types";

type SquadGridProps = {
  players: PlayerProfile[];
};

export default function SquadGrid({ players }: SquadGridProps) {
  if (!players.length) {
    return (
      <div className="surface-card p-6 text-slate-300">
        No squad players found for this filter.
      </div>
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      {players.map((player) => (
        <PlayerCard key={`${player.world_cup_team}-${player.player}`} player={player} />
      ))}
    </div>
  );
}
