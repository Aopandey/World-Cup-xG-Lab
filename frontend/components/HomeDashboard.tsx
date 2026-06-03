"use client";

import { useMemo, useState } from "react";

import SearchBar from "@/components/SearchBar";
import StatCard from "@/components/StatCard";
import TeamCard from "@/components/TeamCard";
import { formatDateRange, formatNumber, formatPercent } from "@/lib/format";
import type { DataCoverage, Team } from "@/lib/types";

type HomeDashboardProps = {
  teams: Team[];
  coverage: DataCoverage;
};

const confidenceOptions = ["All", "Strong", "Moderate", "Limited", "Unavailable"];

export default function HomeDashboard({ teams, coverage }: HomeDashboardProps) {
  const [confidence, setConfidence] = useState("All");

  const filteredTeams = useMemo(() => {
    if (confidence === "All") {
      return teams;
    }

    return teams.filter((team) => team.data_confidence === confidence);
  }, [confidence, teams]);

  return (
    <div className="space-y-8">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="World Cup Teams" value={coverage.total_world_cup_teams} />
        <StatCard label="Teams with StatsBomb Data" value={coverage.teams_with_statsbomb_data} />
        <StatCard label="Squad Players" value={formatNumber(coverage.total_squad_players)} />
        <StatCard label="FBref Match Rate" value={formatPercent(coverage.fbref_coverage_rate, 1)} detail={formatDateRange(coverage.date_range)} />
        <StatCard label="Understat Match Rate" value={formatPercent(coverage.understat_coverage_rate ?? 0, 1)} detail="Club xG context" />
      </section>

      <SearchBar />

      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">World Cup Team Grid</h2>
            <p className="text-sm text-slate-400">
              Showing teams from the 2026 World Cup list with available dashboard artifacts.
            </p>
          </div>
          <label className="flex items-center gap-3 text-sm text-slate-300">
            Data confidence
            <select
              value={confidence}
              onChange={(event) => setConfidence(event.target.value)}
              className="rounded-lg border border-white/10 bg-pitch-800 px-3 py-2 text-white outline-none focus:border-grass-400"
            >
              {confidenceOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>

        {filteredTeams.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredTeams.map((team) => (
              <TeamCard key={team.world_cup_team} team={team} />
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-white/10 bg-white/[0.04] p-6 text-slate-300">
            No teams match the selected confidence filter.
          </div>
        )}
      </section>
    </div>
  );
}
