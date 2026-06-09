import DataStateCallout from "@/components/DataStateCallout";
import ErrorState from "@/components/ErrorState";
import CoverageProgressBar from "@/components/CoverageProgressBar";
import PageHeader from "@/components/PageHeader";
import SourceLegend from "@/components/SourceLegend";
import StatCard from "@/components/StatCard";
import { getCoverage, getTeams } from "@/lib/api";
import { formatDateRange, formatNumber, formatPercent } from "@/lib/format";

export default async function CoveragePage() {
  try {
    const [coverage, teams] = await Promise.all([
      getCoverage(),
      getTeams()
    ]);

    const confidenceCounts = {
      "Strong evidence": teams.filter((team) => team.data_confidence === "Strong").length,
      "Some evidence": teams.filter((team) => team.data_confidence === "Moderate").length,
      "Limited evidence": teams.filter((team) => team.data_confidence === "Limited").length,
      "No historical sample": teams.filter((team) => team.data_confidence === "Unavailable").length
    };

    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Data transparency"
          title="Coverage & Trust"
          subtitle="How much should you trust each team/player profile? This page explains where the evidence is strong, limited, or missing."
        />

        <section className="surface-hero p-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <StatCard label="Total Teams" value={coverage.total_world_cup_teams} />
            <StatCard label="Teams with StatsBomb" value={coverage.teams_with_statsbomb_data} accent="statsbomb" />
            <StatCard label="Percentile profile rate" value={formatPercent(coverage.datamb_coverage_rate ?? 0, 1)} accent="datamb" />
            <StatCard label="Recent form match rate" value={formatPercent(coverage.fbref_coverage_rate, 1)} accent="fbref" />
            <StatCard label="Club xG match rate" value={formatPercent(coverage.understat_coverage_rate ?? 0, 1)} accent="understat" />
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-400">
            Historical date range: {formatDateRange(coverage.date_range)}. This is a historical xG analysis dashboard,
            not a complete current-season or 2026 prediction model.
          </p>
        </section>

        <section className="surface-card p-5">
          <h2 className="text-xl font-semibold text-white">Source coverage at a glance</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Missing StatsBomb data does not mean a team or player is bad. It means the open-data competitions used for
            the historical model do not include enough shots for them.
          </p>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <CoverageProgressBar
              label="Teams with historical StatsBomb"
              value={coverage.teams_with_statsbomb_data / coverage.total_world_cup_teams}
              detail={`${coverage.teams_with_statsbomb_data} of ${coverage.total_world_cup_teams} teams`}
              accent="statsbomb"
            />
            <CoverageProgressBar
              label="Percentile profile match rate"
              value={coverage.datamb_coverage_rate ?? 0}
              detail="25/26 percentile profiles"
              accent="datamb"
            />
            <CoverageProgressBar
              label="FBref player match rate"
              value={coverage.fbref_coverage_rate}
              detail="Recent aggregate club form"
              accent="fbref"
            />
            <CoverageProgressBar
              label="Understat player match rate"
              value={coverage.understat_coverage_rate ?? 0}
              detail="Club xG context"
              accent="understat"
            />
          </div>
        </section>

        <SourceLegend />

        <section className="grid gap-5 lg:grid-cols-2">
          <div className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Player Source Coverage</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <StatCard label="Squad Players" value={formatNumber(coverage.total_squad_players)} />
              <StatCard label="Percentile profiles" value={formatNumber(coverage.datamb_matched_players ?? 0)} accent="datamb" />
              <StatCard label="Percentile missing" value={formatNumber(coverage.datamb_missing_players ?? 0)} accent="datamb" />
              <StatCard label="Recent form matched" value={formatNumber(coverage.fbref_matched_players)} accent="fbref" />
              <StatCard label="Recent form missing" value={formatNumber(coverage.fbref_missing_players)} accent="fbref" />
              <StatCard label="Club xG matched" value={formatNumber(coverage.understat_matched_players ?? 0)} accent="understat" />
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
              Limited or no historical samples are normal in this product, so pages shift visual emphasis toward
              source availability and recent club context.
            </p>
          </div>
        </section>

        <DataStateCallout title="Known limitations" tone="neutral">
          <ul className="space-y-2">
            {coverage.known_limitations.map((limitation) => (
              <li key={limitation}>- {limitation}</li>
            ))}
            <li>- This is not a betting model.</li>
            <li>- This does not guarantee 2026 World Cup performance.</li>
            <li>- Historical international xG and club context are separate.</li>
            <li>- Data source coverage differs by league, competition, and player.</li>
            <li>- Name matching can create missing or imperfect joins.</li>
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
