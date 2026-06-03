"use client";

import { useMemo, useState } from "react";

import DataConfidenceBadge from "@/components/DataConfidenceBadge";
import PitchShotMap from "@/components/PitchShotMap";
import SampleWarning from "@/components/SampleWarning";
import SquadGrid from "@/components/SquadGrid";
import StatCard from "@/components/StatCard";
import { assetUrl, flagLabel, formatDateRange, formatNumber, formatPercent } from "@/lib/format";
import type { PlayerProfile, Team, TeamProfile } from "@/lib/types";

type TeamProfileViewProps = {
  team: Team | null;
  profile: TeamProfile;
  players: PlayerProfile[];
};

const positionOptions = ["All", "Goalkeeper", "Defender", "Midfielder", "Forward"];

export default function TeamProfileView({ team, profile, players }: TeamProfileViewProps) {
  const [positionGroup, setPositionGroup] = useState("All");
  const flagSrc = assetUrl(profile.flag_image_url);

  const filteredPlayers = useMemo(() => {
    if (positionGroup === "All") {
      return players;
    }

    return players.filter((player) => player.position_group === positionGroup);
  }, [players, positionGroup]);

  return (
    <div className="space-y-8">
      <section className="rounded-lg border border-white/10 bg-white/[0.045] p-5 shadow-card">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-pitch-700 text-xl font-black text-white">
              {flagSrc ? (
                <img
                  src={flagSrc}
                  alt={`${profile.world_cup_team} flag`}
                  className="h-full w-full object-cover"
                />
              ) : (
                flagLabel(profile.flag_code)
              )}
            </div>
            <div>
              <h1 className="text-3xl font-black text-white">{profile.world_cup_team}</h1>
              <p className="mt-1 text-sm text-slate-400">
                {team?.squad_status?.replace("_", " ") ?? "Squad status unavailable"} - {formatDateRange(profile.statsbomb_date_range)}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <DataConfidenceBadge value={team?.data_confidence ?? "Unavailable"} />
            <span className="rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2 text-sm text-slate-300">
              FBref coverage {formatPercent(team?.fbref_coverage_rate ?? 0)}
            </span>
            <span className="rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2 text-sm text-slate-300">
              Understat coverage {formatPercent(team?.understat_coverage_rate ?? 0)}
            </span>
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <StatCard label="StatsBomb Shots" value={formatNumber(profile.statsbomb_shots)} />
          <StatCard label="Goals" value={formatNumber(profile.statsbomb_goals)} />
          <StatCard label="Total xG" value={formatNumber(profile.total_xg, 1)} />
          <StatCard label="Goals minus xG" value={formatNumber(profile.goals_minus_xg, 1)} />
          <StatCard label="Avg xG per Shot" value={formatNumber(profile.avg_xg_per_shot, 3)} />
        </div>
      </section>

      {profile.warnings.length ? (
        <SampleWarning>{profile.warnings.join(" ")}</SampleWarning>
      ) : null}

      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Official Squad Grid</h2>
            <p className="text-sm text-slate-400">
              Player cards show StatsBomb sample size, FBref availability, and data confidence.
            </p>
          </div>
          <select
            value={positionGroup}
            onChange={(event) => setPositionGroup(event.target.value)}
            className="rounded-lg border border-white/10 bg-pitch-800 px-3 py-2 text-white outline-none focus:border-grass-400"
          >
            {positionOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
        <SquadGrid players={filteredPlayers} />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <h2 className="text-xl font-bold text-white">Top Historical xG Players</h2>
          <div className="mt-4 space-y-3">
            {profile.top_xg_players.length ? (
              profile.top_xg_players.slice(0, 8).map((player) => (
                <div key={player.player} className="flex items-center justify-between gap-3 rounded-lg bg-white/[0.045] px-3 py-2 text-sm">
                  <span className="font-medium text-white">{player.player}</span>
                  <span className="text-slate-300">{formatNumber(player.total_xg, 2)} xG</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400">No historical xG player sample available.</p>
            )}
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <h2 className="text-xl font-bold text-white">Top Recent FBref Players</h2>
          <div className="mt-4 space-y-3">
            {profile.top_recent_fbref_players.length ? (
              profile.top_recent_fbref_players.slice(0, 8).map((player) => (
                <div key={`${player.player}-${player.season}`} className="rounded-lg bg-white/[0.045] px-3 py-2 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-white">{player.player}</span>
                    <span className="text-slate-300">{formatNumber(player.xg, 2)} xG</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    {player.club ?? "Club unknown"} - {player.league ?? "League unknown"} - {player.season ?? "Season unknown"}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400">No recent FBref player context found for this team yet.</p>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
        <h2 className="text-xl font-bold text-white">Top Club xG Context from Understat</h2>
        <p className="mt-2 text-sm text-slate-400">
          Understat rows are club-season context only and are separate from the trained StatsBomb xG model.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {profile.top_recent_understat_players?.length ? (
            profile.top_recent_understat_players.slice(0, 10).map((player) => (
              <div key={`${player.player}-${player.season}-${player.team}`} className="rounded-lg bg-white/[0.045] px-3 py-2 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-white">{player.player}</span>
                  <span className="text-slate-300">{formatNumber(player.xg, 2)} xG</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {player.team ?? player.club ?? "Club unknown"} - {player.league ?? "League unknown"} - {player.season ?? "Season unknown"}
                </p>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-400">No Understat club xG context found for this team yet.</p>
          )}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl font-bold text-white">Team Shot and Scoring-Zone View</h2>
        <p className="text-sm text-slate-400">
          StatsBomb powers the historical xG model and shot-location views. This frontend is ready to render shot dots when shot-level coordinates are added to the API artifacts.
        </p>
        <PitchShotMap emptyMessage="Shot-level coordinates are not included in the current dashboard artifacts for this team yet." />
      </section>
    </div>
  );
}
