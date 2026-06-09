import ErrorState from "@/components/ErrorState";
import TeamProfileView from "@/components/TeamProfileView";
import { getPlayers, getTeamProfile, getTeams } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type TeamPageProps = {
  params: {
    teamName: string;
  };
};

export default async function TeamPage({ params }: TeamPageProps) {
  const teamName = decodeURIComponent(params.teamName);

  try {
    const [teams, profile, playersResponse] = await Promise.all([
      getTeams(),
      getTeamProfile(teamName),
      getPlayers({ team: teamName })
    ]);
    const team = teams.find((candidate) => candidate.world_cup_team.toLowerCase() === profile.world_cup_team.toLowerCase()) ?? null;

    return <TeamProfileView team={team} profile={profile} players={playersResponse.players} />;
  } catch (error) {
    return (
      <ErrorState
        title="Team not found"
        message={error instanceof Error ? error.message : "No team profile was found for this route."}
      />
    );
  }
}
