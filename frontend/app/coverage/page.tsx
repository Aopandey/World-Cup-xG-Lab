import DataStateCallout from "@/components/DataStateCallout";
import ErrorState from "@/components/ErrorState";
import PageHeader from "@/components/PageHeader";
import SourceLegend from "@/components/SourceLegend";
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

    const confidenceCounts = {
      Strong: teams.filter((team) => team.data_confidence === "Strong").length,
      Moderate: teams.filter((team) => team.data_confidence === "Moderate").length,
      Limited: teams.filter((team) => team.data_confidence === "Limited").length,
      Unavailable: teams.filter((team) => team.data_confidence === "Unavailable").length
    };

    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Data transparency"
          title="Coverage and Limitations"
          subtitle="A source audit for squad coverage, historical samples, recent aggregate context, and known gaps."
        />

        <section className="surface-hero p-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total Teams" value={coverage.total_world_cup_teams} />
            <StatCard label="Teams with StatsBomb" value={coverage.teams_with_statsbomb_data} accent="statsbomb" />
            <StatCard label="FBref Match Rate" value={formatPercent(coverage.fbref_coverage_rate, 1)} accent="fbref" />
            <StatCard label="Understat Match Rate" value={formatPercent(coverage.understat_coverage_rate ?? 0, 1)} accent="understat" />
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-400">
            Historical date range: {formatDateRange(coverage.date_range)}. This is a historical xG analysis dashboard,
            not a complete current-season or 2026 prediction model.
          </p>
        </section>

        <SourceLegend />

        <section className="grid gap-5 lg:grid-cols-2">
          <div className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Player Source Coverage</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <StatCard label="Squad Players" value={formatNumber(coverage.total_squad_players)} />
              <StatCard label="FBref Matched" value={formatNumber(coverage.fbref_matched_players)} accent="fbref" />
              <StatCard label="FBref Missing" value={formatNumber(coverage.fbref_missing_players)} accent="fbref" />
              <StatCard label="Understat Matched" value={formatNumber(coverage.understat_matched_players ?? 0)} accent="understat" />
            </div>
          </div>

          <div className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Confidence States</h2>
            <div className="mt-4 space-y-2 text-sm">
              {Object.entries(confidenceCounts).map(([label, count]) => (
                <div key={label} className="flex items-center justify-between rounded-md bg-white/[0.04] px-3 py-2">
                  <span className="text-slate-300">{label}</span>
                  <span className="font-semibold text-white">{count} teams</span>
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-400">
              Weak or unavailable historical samples are normal in this product, so pages shift visual emphasis toward
              source availability and recent club context.
            </p>
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-2">
          <MissingList title="Teams Missing Squad Data" values={coverage.teams_missing_squad_data} />
          <MissingList title="Teams Missing StatsBomb Historical Data" values={coverage.missing_teams} />
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <StatCard label="Limited Players" value={formatNumber(limitedPlayers.count)} />
          <StatCard label="Unavailable Players" value={formatNumber(unavailablePlayers.count)} />
          <StatCard label="Teams with Squad Data" value={formatNumber(coverage.teams_with_squad_data)} />
        </section>

        <DataStateCallout title="Known limitations" tone="neutral">
          <ul className="space-y-2">
            {coverage.known_limitations.map((limitation) => (
              <li key={limitation}>- {limitation}</li>
            ))}
          </ul>
        </DataStateCallout>
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

function MissingList({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="surface-card p-5">
      <h2 className="text-xl font-semibold text-white">{title}</h2>
      <div className="mt-4 flex flex-wrap gap-2">
        {values.length ? (
          values.map((value) => (
            <span key={value} className="rounded-md border border-white/10 bg-white/[0.045] px-3 py-2 text-sm text-slate-300">
              {value}
            </span>
          ))
        ) : (
          <p className="text-sm text-slate-400">None listed.</p>
        )}
      </div>
    </div>
  );
}
