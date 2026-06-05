"use client";

import { useMemo, useState } from "react";

import AvailabilityStrip from "@/components/AvailabilityStrip";
import DataConfidenceBadge from "@/components/DataConfidenceBadge";
import DataStateCallout from "@/components/DataStateCallout";
import PitchShotMap from "@/components/PitchShotMap";
import SectionTabs from "@/components/SectionTabs";
import SegmentedFilter from "@/components/SegmentedFilter";
import SourceBadge from "@/components/SourceBadge";
import SourceLegend from "@/components/SourceLegend";
import SquadGrid from "@/components/SquadGrid";
import StatCard from "@/components/StatCard";
import TakeawayCard from "@/components/TakeawayCard";
import {
  assetUrl,
  flagLabel,
  formatDateRange,
  formatNumber,
  formatPercent,
  normalizeSeasonLabel,
  shortLeagueName,
  sourceTakeaway
} from "@/lib/format";
import type { PlayerProfile, RecentFbrefPlayer, RecentUnderstatPlayer, Team, TeamProfile } from "@/lib/types";

type TeamProfileViewProps = {
  team: Team | null;
  profile: TeamProfile;
  players: PlayerProfile[];
};

const mainTabs = [
  { label: "Overview", value: "overview" },
  { label: "Squad", value: "squad" },
  { label: "Historical xG", value: "historical" },
  { label: "Club Context", value: "club" },
  { label: "Coverage", value: "coverage" }
];

const positionOptions = ["All", "Goalkeeper", "Defender", "Midfielder", "Forward"];

export default function TeamProfileView({ team, profile, players }: TeamProfileViewProps) {
  const [activeTab, setActiveTab] = useState("overview");
  const [positionGroup, setPositionGroup] = useState("All");
  const flagSrc = assetUrl(profile.flag_image_url);
  const sampleWeak = profile.statsbomb_shots < 50;
  const confidence = team?.data_confidence ?? "Unavailable";
  const takeaway = sourceTakeaway({
    statsbombShots: profile.statsbomb_shots,
    fbrefAvailable: Boolean(team?.fbref_players_matched),
    understatAvailable: Boolean(team?.understat_players_matched)
  });

  const positionCounts = useMemo(() => {
    return positionOptions.reduce<Record<string, number>>((counts, option) => {
      counts[option] = option === "All" ? players.length : players.filter((player) => player.position_group === option).length;
      return counts;
    }, {});
  }, [players]);

  const filteredPlayers = useMemo(() => {
    if (positionGroup === "All") {
      return players;
    }

    return players.filter((player) => player.position_group === positionGroup);
  }, [players, positionGroup]);

  return (
    <div className="space-y-7">
      <section className="surface-hero p-5 md:p-7">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.8fr)]">
          <div>
            <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
              <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-pitch-700 text-2xl font-semibold text-white">
                {flagSrc ? (
                  <img src={flagSrc} alt={`${profile.world_cup_team} flag`} className="h-full w-full object-cover" />
                ) : (
                  flagLabel(profile.flag_code)
                )}
              </div>
              <div>
                <p className="stat-label text-grass-400">National team profile</p>
                <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">{profile.world_cup_team}</h1>
                <p className="mt-2 text-sm text-slate-400">{formatDateRange(profile.statsbomb_date_range)}</p>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard label="SB Shots" value={formatNumber(profile.statsbomb_shots)} accent="statsbomb" />
              <StatCard label="Goals" value={formatNumber(profile.statsbomb_goals)} accent="statsbomb" />
              <StatCard label="Total xG" value={formatNumber(profile.total_xg, 1)} accent="statsbomb" />
              <StatCard label="Goals - xG" value={formatNumber(profile.goals_minus_xg, 1)} accent="statsbomb" />
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <DataConfidenceBadge value={confidence} />
              <AvailabilityStrip
                statsbombShots={profile.statsbomb_shots}
                fbrefAvailable={Boolean(team?.fbref_players_matched)}
                understatAvailable={Boolean(team?.understat_players_matched)}
              />
            </div>
            <TakeawayCard
              label="What to know"
              value={takeaway}
              detail="Read team xG as historical evidence from available samples, then use FBref and Understat for recent club context."
            />
            {sampleWeak ? (
              <DataStateCallout title="Small sample" tone="warning">
                Small sample size: interpret this team's xG profile carefully.
              </DataStateCallout>
            ) : null}
          </div>
        </div>
      </section>

      <SectionTabs options={mainTabs} value={activeTab} onChange={setActiveTab} />

      {activeTab === "overview" ? (
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.85fr)]">
          <div className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Overview</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              StatsBomb is the historical shot-quality layer. Club sources are displayed separately so weak samples do not
              look more certain than they are.
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <TakeawayCard label="Avg xG / Shot" value={formatNumber(profile.avg_xg_per_shot, 3)} />
              <TakeawayCard label="FBref Coverage" value={formatPercent(team?.fbref_coverage_rate ?? 0, 1)} />
              <TakeawayCard label="Understat Coverage" value={formatPercent(team?.understat_coverage_rate ?? 0, 1)} />
            </div>
          </div>
          <SourceLegend />
        </section>
      ) : null}

      {activeTab === "squad" ? (
        <section className="space-y-4">
          <SegmentedFilter
            label="Position group"
            value={positionGroup}
            onChange={setPositionGroup}
            options={positionOptions.map((option) => ({
              label: option,
              value: option,
              count: positionCounts[option]
            }))}
          />
          <SquadGrid players={filteredPlayers} />
        </section>
      ) : null}

      {activeTab === "historical" ? (
        <section className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(320px,1.05fr)]">
          <div className="surface-card p-5">
            <div className="flex items-center gap-2">
              <SourceBadge source="statsbomb" />
              <h2 className="text-xl font-semibold text-white">Top Historical xG Players</h2>
            </div>
            <TopXgList players={profile.top_xg_players} />
          </div>
          <div className="space-y-3">
            <PitchShotMap
              title="Team Shot and Scoring-Zone View"
              shots={profile.shot_points ?? []}
              sampleSize={profile.statsbomb_shots}
              emptyMessage="No reliable shot-level coordinates are available for this team in the current StatsBomb sample."
            />
          </div>
        </section>
      ) : null}

      {activeTab === "club" ? (
        <section className="grid gap-5 xl:grid-cols-2">
          <ClubContextList
            source="fbref"
            title="Recent FBref Form"
            rows={profile.top_recent_fbref_players}
            emptyMessage="No recent FBref player context found for this team yet."
          />
          <ClubContextList
            source="understat"
            title="Understat Club xG Context"
            rows={profile.top_recent_understat_players ?? []}
            emptyMessage="No Understat club xG context found for this team yet."
          />
        </section>
      ) : null}

      {activeTab === "coverage" ? (
        <section className="grid gap-5 lg:grid-cols-2">
          <div className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Competitions Included</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {profile.competitions_included.length ? (
                profile.competitions_included.map((competition) => (
                  <span key={competition} className="rounded-md border border-white/10 bg-white/[0.045] px-3 py-2 text-sm text-slate-300">
                    {competition}
                  </span>
                ))
              ) : (
                <p className="text-sm text-slate-400">No competition metadata is available.</p>
              )}
            </div>
          </div>
          <div className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Position Group Samples</h2>
            <div className="mt-4 space-y-2">
              {profile.position_group_summaries.map((group) => (
                <div key={group.position_group ?? "Unknown"} className="flex items-center justify-between rounded-md bg-white/[0.04] px-3 py-2 text-sm">
                  <span className="text-slate-300">{group.position_group ?? "Unknown"}</span>
                  <span className="font-semibold text-white">{formatNumber(group.statsbomb_shots)} shots</span>
                </div>
              ))}
            </div>
          </div>
          {profile.warnings.length ? (
            <DataStateCallout title="Known team warnings" tone="warning">
              {profile.warnings.join(" ")}
            </DataStateCallout>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function TopXgList({ players }: { players: TeamProfile["top_xg_players"] }) {
  if (!players.length) {
    return <p className="mt-4 text-sm text-slate-400">No historical xG player sample available.</p>;
  }

  return (
    <div className="mt-4 space-y-2">
      {players.slice(0, 8).map((player) => (
        <div key={player.player} className="flex items-center justify-between gap-3 rounded-md bg-white/[0.045] px-3 py-2 text-sm">
          <span className="font-medium text-white">{player.player}</span>
          <span className="text-slate-300">{formatNumber(player.total_xg, 2)} xG</span>
        </div>
      ))}
    </div>
  );
}

function ClubContextList({
  source,
  title,
  rows,
  emptyMessage
}: {
  source: "fbref" | "understat";
  title: string;
  rows: Array<RecentFbrefPlayer | RecentUnderstatPlayer>;
  emptyMessage: string;
}) {
  const hasXg = rows.some((row) => typeof row.xg === "number");

  return (
    <div className="surface-card p-5">
      <div className="flex items-center gap-2">
        <SourceBadge source={source} />
        <h2 className="text-xl font-semibold text-white">{title}</h2>
      </div>
      <div className="mt-4 space-y-3">
        {rows.length ? (
          rows.slice(0, 8).map((row) => {
            const club = getContextClub(row);
            return (
              <div key={`${row.player}-${row.season}-${club}`} className="rounded-md bg-white/[0.045] px-3 py-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-white">{row.player}</span>
                  <span className="text-slate-300">
                    {hasXg ? `${formatNumber(row.xg, 2)} xG` : `${formatNumber(row.shots)} shots`}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {club || "Club unknown"} - {shortLeagueName(row.league)} - {normalizeSeasonLabel(row.season)}
                </p>
              </div>
            );
          })
        ) : (
          <p className="text-sm text-slate-400">{emptyMessage}</p>
        )}
      </div>
    </div>
  );
}

function getContextClub(row: RecentFbrefPlayer | RecentUnderstatPlayer) {
  if ("team" in row && row.team) {
    return row.team;
  }

  return row.club ?? null;
}
