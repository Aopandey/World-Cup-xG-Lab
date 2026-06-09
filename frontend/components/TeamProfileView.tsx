"use client";

import { useMemo, useState } from "react";

import AvailabilityStrip from "@/components/AvailabilityStrip";
import DataConfidenceBadge from "@/components/DataConfidenceBadge";
import DataStateCallout from "@/components/DataStateCallout";
import DetailAccordion from "@/components/DetailAccordion";
import PitchShotMap from "@/components/PitchShotMap";
import SectionTabs from "@/components/SectionTabs";
import SegmentedFilter from "@/components/SegmentedFilter";
import SourceBadge from "@/components/SourceBadge";
import SourceLegend from "@/components/SourceLegend";
import SquadFormationBoard from "@/components/SquadFormationBoard";
import SquadGrid from "@/components/SquadGrid";
import StatCard from "@/components/StatCard";
import SummaryCard from "@/components/SummaryCard";
import TakeawayCard from "@/components/TakeawayCard";
import {
  assetUrl,
  flagLabel,
  formatDateRange,
  formatNumber,
  formatPercent,
  normalizeSeasonLabel,
  shortLeagueName
} from "@/lib/format";
import { buildTeamSummary } from "@/lib/summaries";
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
  const externalContext = Boolean(team?.fbref_players_matched || team?.understat_players_matched);
  const teamSummary = buildTeamSummary(profile, team);

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

            <p className="mt-5 max-w-2xl text-sm leading-6 text-slate-300">
              Start with the team summary, then open the detail sections below for model output, data strength, and
              club-context coverage.
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <DataConfidenceBadge
                value={confidence}
                hasHistoricalSample={profile.statsbomb_shots > 0}
                hasExternalContext={externalContext}
              />
              <AvailabilityStrip
                statsbombShots={profile.statsbomb_shots}
                fbrefAvailable={Boolean(team?.fbref_players_matched)}
                understatAvailable={Boolean(team?.understat_players_matched)}
              />
            </div>
            <div className="surface-inset p-4 text-sm leading-6 text-slate-300">
              <p className="stat-label">Data read</p>
              <p className="mt-2">
                The detail sections below separate historical model output from club-context sources.
              </p>
            </div>
          </div>
        </div>
      </section>

      <SummaryCard
        eyebrow="Team summary"
        title={teamSummary.title}
        paragraphs={teamSummary.paragraphs}
        takeaway={teamSummary.takeaway}
        tone={teamSummary.tone}
      />

      {sampleWeak ? (
        <DataStateCallout title="Small historical sample" tone="warning">
          This team has fewer than 50 historical StatsBomb shots in the current dataset. Treat model totals as directional, not definitive.
        </DataStateCallout>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <DetailAccordion
          title="What did the xG model find?"
          summary="Past model output from StatsBomb open-data matches. These are not 2026 forecasts."
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <StatCard
              label="Past sample shots"
              value={formatNumber(profile.statsbomb_shots)}
              detail="StatsBomb open-data matches"
              accent="statsbomb"
            />
            <StatCard
              label="Goals"
              value={formatNumber(profile.statsbomb_goals)}
              detail="Goals in covered matches"
              accent="statsbomb"
            />
            <StatCard
              label="xG in available past matches"
              value={formatNumber(profile.total_xg, 1)}
              detail="Not a 2026 forecast"
              accent="statsbomb"
            />
            <StatCard
              label="Scoring vs expected"
              value={formatNumber(profile.goals_minus_xg, 1)}
              detail="Goals minus model xG"
              accent="statsbomb"
            />
          </div>
        </DetailAccordion>

        <DetailAccordion
          title="How strong is the data?"
          summary="Sample size and evidence level for this team's historical model layer."
          tone={sampleWeak ? "warning" : "default"}
        >
          <div className="space-y-4 text-sm leading-6 text-slate-300">
            <div className="flex flex-wrap items-center gap-2">
              <DataConfidenceBadge
                value={confidence}
                hasHistoricalSample={profile.statsbomb_shots > 0}
                hasExternalContext={externalContext}
              />
              <span>{formatNumber(profile.statsbomb_shots)} past sample shots are available.</span>
            </div>
            {sampleWeak ? (
              <DataStateCallout title="Small historical sample" tone="warning">
                This team has fewer than 50 historical StatsBomb shots in the current dataset. Treat model totals as
                directional, not definitive.
              </DataStateCallout>
            ) : (
              <p>
                This sample is large enough to make the historical model output easier to read, but it still describes
                available past data only.
              </p>
            )}
          </div>
        </DetailAccordion>

        <DetailAccordion
          title="What club context is available?"
          summary="External club-context sources are shown separately from the trained StatsBomb xG model."
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <TakeawayCard
              label="Players with recent club stats"
              value={formatPercent(team?.fbref_coverage_rate ?? 0, 1)}
              detail="FBref match rate"
            />
            <TakeawayCard
              label="Players with club xG context"
              value={formatPercent(team?.understat_coverage_rate ?? 0, 1)}
              detail="Understat match rate"
            />
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-400">
            FBref, Understat, and percentile sources help describe club form and source coverage. They do not replace
            the production StatsBomb-trained xG model.
          </p>
        </DetailAccordion>

        <DetailAccordion
          title="Which players should I explore?"
          summary="Use the squad board and player pages to move from team-level context to player-level evidence."
        >
          <div className="space-y-4">
            <button
              type="button"
              onClick={() => setActiveTab("squad")}
              className="rounded-md bg-grass-500 px-4 py-2 text-sm font-semibold text-pitch-900 transition hover:bg-grass-400"
            >
              Open squad board
            </button>
            <div>
              <p className="stat-label">Historical xG players</p>
              <div className="mt-3 space-y-2">
                {profile.top_xg_players.length ? (
                  profile.top_xg_players.slice(0, 5).map((player) => (
                    <div key={player.player} className="flex items-center justify-between gap-3 rounded-md bg-white/[0.045] px-3 py-2 text-sm">
                      <span className="font-medium text-white">{player.player}</span>
                      <span className="text-slate-300">{formatNumber(player.total_xg, 2)} xG</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-400">No player-level historical xG sample is available yet.</p>
                )}
              </div>
            </div>
          </div>
        </DetailAccordion>

        <DetailAccordion
          title="What should I be careful about?"
          summary="The dashboard is source-aware by design, so missing data is part of the story."
        >
          <ul className="space-y-2 text-sm leading-6 text-slate-300">
            <li>- These numbers describe past available data, not projected 2026 World Cup totals.</li>
            <li>- Historical international/open-data samples and club context are separate layers.</li>
            <li>- Missing data does not mean a weak team or player.</li>
            <li>- Source coverage differs by competition, league, and player-name matching.</li>
          </ul>
        </DetailAccordion>
      </section>

      <SectionTabs options={mainTabs} value={activeTab} onChange={setActiveTab} />

      {activeTab === "overview" ? (
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.85fr)]">
          <div className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Overview</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              What do we know about this team? Past sample shots describe the available international/open-data sample,
              while club context helps fill in recent form where available.
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <TakeawayCard
                label="How much past match data do we have?"
                value={formatNumber(profile.statsbomb_shots)}
                detail="StatsBomb open-data shots"
              />
              <TakeawayCard
                label="Shot danger"
                value={formatNumber(profile.avg_xg_per_shot, 3)}
                detail="xG per shot in covered matches"
              />
              <TakeawayCard
                label="Players with recent club stats"
                value={formatPercent(team?.fbref_coverage_rate ?? 0, 1)}
                detail="FBref match rate"
              />
              <TakeawayCard
                label="Players with club xG context"
                value={formatPercent(team?.understat_coverage_rate ?? 0, 1)}
                detail="Understat match rate"
              />
            </div>
          </div>
          <SourceLegend />
        </section>
      ) : null}

      {activeTab === "squad" ? (
        <section className="space-y-4">
          <SquadFormationBoard players={players} teamName={profile.world_cup_team} />
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
          <div>
            <h2 className="text-xl font-semibold text-white">Full squad list</h2>
            <p className="mt-1 text-sm text-slate-400">
              Use this list as the complete squad browser after exploring the football-shaped Data XI above.
            </p>
          </div>
          <SquadGrid players={filteredPlayers} />
        </section>
      ) : null}

      {activeTab === "historical" ? (
        <section className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(320px,1.05fr)]">
          <div className="surface-card p-5">
            <div className="flex items-center gap-2">
              <SourceBadge source="statsbomb" />
              <h2 className="text-xl font-semibold text-white">Historical chance creators</h2>
            </div>
            <TopXgList players={profile.top_xg_players} />
          </div>
          <div className="space-y-3">
            <PitchShotMap
              title="Team shot and scoring-zone view"
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
            title="Understat club xG context"
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
