import ErrorState from "@/components/ErrorState";
import PlayerXgExplorer from "@/components/PlayerXgExplorer";
import { getPlayers } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function PlayersPage() {
  try {
    const playersResponse = await getPlayers();

    return <PlayerXgExplorer players={playersResponse.players} />;
  } catch (error) {
    return (
      <ErrorState
        title="Could not load players"
        message={error instanceof Error ? error.message : "Start the FastAPI backend and try again."}
      />
    );
  }
}
