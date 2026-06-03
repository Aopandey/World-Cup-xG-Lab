import ErrorState from "@/components/ErrorState";
import PageHeader from "@/components/PageHeader";
import SampleWarning from "@/components/SampleWarning";
import StatCard from "@/components/StatCard";
import { getCoverage, getPlayers, getTeams } from "@/lib/api";
import { formatDateRange, formatNumber, formatPercent } from "@/lib/format";

export default async function CoveragePage() {
  try {
    const [coverage, teams, limitedPlayers, unavailablePlayers] = await Promise.all([
      getCoverage(),
      getTeams(),
      getPlayers({ data_confidence: "Limited" }),
      getPlayers({ data_confidence: "Unavailable" })
    ]);
    const limitedTeams = teams.filter((team) => team.data_confidence === "Limited").length;

    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Data transparency"
          title="Coverage and Limitations"
          subtitle="Understand where the dashboard has strong samples, where context is limited, and why the results should be read as historical evidence rather than future certainty."
        />

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total Teams" value={coverage.total_world_cup_teams} />
          <StatCard label="Teams with Squad Data" value={coverage.teams_with_squad_data} />
          <StatCard label="Teams with StatsBomb Data" value={coverage.teams_with_statsbomb_data} />
          <StatCard label="FBref Match Rate" value={formatPercent(coverage.fbref_coverage_rate, 1)} />
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Squad Players" value={formatNumber(coverage.total_squad_players)} />
          <StatCard label="FBref Matched Players" value={formatNumber(coverage.fbref_matched_players)} />
          <StatCard label="FBref Missing Players" value={formatNumber(coverage.fbref_missing_players)} />
          <StatCard label="Historical Date Range" value={formatDateRange(coverage.date_range)} />
        </section>

        <SampleWarning>
          Some players have limited or no historical shot-location data. Weak samples are displayed with warnings, not treated as confident scoring-zone evidence.
        </SampleWarning>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
            <h2 className="text-xl font-bold text-white">Missing Team Coverage</h2>
            <div className="mt-4 space-y-4 text-sm text-slate-300">
              <div>
                <p className="font-semibold text-white">Teams missing squad data</p>
                <p className="mt-1">{coverage.teams_missing_squad_data.join(", ") || "None"}</p>
              </div>
              <div>
                <p className="font-semibold text-white">Teams missing StatsBomb data</p>
                <p className="mt-1">{coverage.missing_teams.join(", ") || "None"}</p>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
            <h2 className="text-xl font-bold text-white">Limited Samples</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <StatCard label="Limited Teams" value={limitedTeams} />
              <StatCard label="Limited Players" value={formatNumber(limitedPlayers.count)} />
              <StatCard label="Unavailable Players" value={formatNumber(unavailablePlayers.count)} />
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <h2 className="text-2xl font-bold text-white">Known Limitations</h2>
          <ul className="mt-4 space-y-2 text-sm leading-6 text-slate-300">
            {coverage.known_limitations.map((limitation) => (
              <li key={limitation}>- {limitation}</li>
            ))}
          </ul>
        </section>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        title="Could not load coverage summary"
        message={error instanceof Error ? error.message : "Start the FastAPI backend and try again."}
      />
    );
  }
}
