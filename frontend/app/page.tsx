import ErrorState from "@/components/ErrorState";
import HomeDashboard from "@/components/HomeDashboard";
import { getCoverage, getTeams } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function HomePage() {
  try {
    const [teams, coverage] = await Promise.all([getTeams(), getCoverage()]);

    return <HomeDashboard teams={teams} coverage={coverage} />;
  } catch (error) {
    return (
      <ErrorState
        title="Could not load dashboard"
        message={error instanceof Error ? error.message : "Start the FastAPI backend and try again."}
      />
    );
  }
}
