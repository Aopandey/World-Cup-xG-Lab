"use client";

import { useMemo, useState } from "react";

import SearchBar from "@/components/SearchBar";
import SegmentedFilter from "@/components/SegmentedFilter";
import SourceLegend from "@/components/SourceLegend";
import TeamCard from "@/components/TeamCard";
import { formatDateRange, formatNumber, formatPercent } from "@/lib/format";
import type { DataCoverage, Team } from "@/lib/types";

type HomeDashboardProps = {
  teams: Team[];
  coverage: DataCoverage;
};

const confidenceOptions = ["All", "Strong", "Moderate", "Limited", "Unavailable"];
const confidenceLabels: Record<string, string> = {
  All: "All",
  Strong: "Strong evidence",
  Moderate: "Some evidence",
  Limited: "Limited evidence",
  Unavailable: "No historical sample"
};

export default function HomeDashboard({ teams, coverage }: HomeDashboardProps) {
  const [confidence, setConfidence] = useState("All");

  const confidenceCounts = useMemo(() => {
    return confidenceOptions.reduce<Record<string, number>>((counts, option) => {
      counts[option] = option === "All" ? teams.length : teams.filter((team) => team.data_confidence === option).length;
      return counts;
    }, {});
  }, [teams]);

  const filteredTeams = useMemo(() => {
    if (confidence === "All") {
      return teams;
    }

    return teams.filter((team) => team.data_confidence === confidence);
  }, [confidence, teams]);

  return (
    <div className="space-y-8">
      <section className="surface-hero overflow-hidden p-5 md:p-7">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.8fr)] lg:items-end">
          <div className="space-y-5">
            <div>
              <p className="stat-label text-grass-400">Football analytics dashboard</p>
              <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-white md:text-6xl">
                World Cup xG Lab
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-slate-300">
                Explore 2026 World Cup teams through historical open-data shot samples, recent club context, and
                transparent source coverage. The numbers in this dashboard describe past available data, not projected
                2026 tournament goals.
              </p>
            </div>
            <SearchBar />
          </div>

          <div className="surface-inset p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="stat-label">Coverage Snapshot</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Historical open event data plus current squad context. Not a complete 2025/26 current-season dataset.
                </p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <MiniMetric label="Teams" value={`${teams.length}/${coverage.total_world_cup_teams}`} />
              <MiniMetric label="Open-data sample range" value={formatDateRange(coverage.date_range)} />
              <MiniMetric label="Teams with past StatsBomb sample" value={`${coverage.teams_with_statsbomb_data}`} />
              <MiniMetric label="Percentile profiles" value={formatPercent(coverage.datamb_coverage_rate ?? 0, 1)} />
              <MiniMetric label="Squad players" value={formatNumber(coverage.total_squad_players)} />
              <MiniMetric label="Players matched to recent form" value={formatPercent(coverage.fbref_coverage_rate, 1)} />
              <MiniMetric label="Players with club xG context" value={formatPercent(coverage.understat_coverage_rate ?? 0, 1)} />
            </div>
          </div>
        </div>
      </section>

      <SourceLegend />

      <section className="space-y-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-white">Explore 2026 Teams</h2>
            <p className="mt-1 text-sm text-slate-400">
              Choose a national team to explore its historical shot data, squad context, and source coverage. Detailed
              xG numbers live inside each team profile.
            </p>
          </div>
          <SegmentedFilter
            label="Data evidence"
            value={confidence}
            onChange={setConfidence}
            options={confidenceOptions.map((option) => ({
              label: confidenceLabels[option] ?? option,
              value: option,
              count: confidenceCounts[option]
            }))}
          />
        </div>

        {filteredTeams.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredTeams.map((team) => (
              <TeamCard key={team.world_cup_team} team={team} />
            ))}
          </div>
        ) : (
          <div className="surface-card p-6 text-slate-300">
            No teams match the selected data evidence filter.
          </div>
        )}
      </section>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/15 p-3">
      <p className="stat-label">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-white">{value}</p>
    </div>
  );
}
