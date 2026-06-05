import ErrorState from "@/components/ErrorState";
import PlayerProfileView from "@/components/PlayerProfileView";
import { getPlayerProfile } from "@/lib/api";

type PlayerPageProps = {
  params: {
    playerName: string;
  };
};

export default async function PlayerPage({ params }: PlayerPageProps) {
  const playerName = decodeURIComponent(params.playerName);

  try {
    const player = await getPlayerProfile(playerName);
    return <PlayerProfileView player={player} />;
  } catch (error) {
    return (
      <ErrorState
        title="Player not found"
        message={error instanceof Error ? error.message : "No player profile was found for this route."}
      />
    );
  }
}
