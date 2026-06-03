import ErrorState from "@/components/ErrorState";
import HomeDashboard from "@/components/HomeDashboard";
import PageHeader from "@/components/PageHeader";
import { getCoverage, getTeams } from "@/lib/api";

export default async function HomePage() {
  try {
    const [teams, coverage] = await Promise.all([getTeams(), getCoverage()]);

    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Football analytics dashboard"
          title="World Cup xG Lab"
          subtitle="Explore 2026 World Cup teams through historical StatsBomb xG outputs, official squad filters, and recent FBref aggregate player context. The dashboard shows who generated high-quality chances in available data, not guaranteed future scoring locations."
        />
        <HomeDashboard teams={teams} coverage={coverage} />
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        title="Could not load dashboard"
        message={error instanceof Error ? error.message : "Start the FastAPI backend and try again."}
      />
    );
  }
}
