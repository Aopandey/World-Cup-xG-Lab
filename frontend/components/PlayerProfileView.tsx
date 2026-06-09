"use client";

import { useMemo, useState } from "react";

import AvailabilityStrip from "@/components/AvailabilityStrip";
import CompactSeasonTable from "@/components/CompactSeasonTable";
import type { CompactColumn } from "@/components/CompactSeasonTable";
import DataConfidenceBadge from "@/components/DataConfidenceBadge";
import DataStateCallout from "@/components/DataStateCallout";
import EmptyDataState from "@/components/EmptyDataState";
import PitchShotMap from "@/components/PitchShotMap";
import QuickReadCard from "@/components/QuickReadCard";
import SectionTabs from "@/components/SectionTabs";
import SourceBadge from "@/components/SourceBadge";
import SourceLegend from "@/components/SourceLegend";
import StatCard from "@/components/StatCard";
import TakeawayCard from "@/components/TakeawayCard";
import {
  assetUrl,
  dedupeUnderstatRows,
  formatDateRange,
  formatNumber,
  initials,
  latestSeasonRows,
  normalizeSeasonLabel,
  playerHasExternalContext,
  shortLeagueName,
  sourceTakeaway
} from "@/lib/format";
import type { FbrefRecentRow, PlayerProfile, UnderstatModelRecentRow, UnderstatRecentRow } from "@/lib/types";

type PlayerProfileViewProps = {
  player: PlayerProfile;
};

const tabs = [
  { label: "Overview", value: "overview" },
  { label: "Historical xG", value: "historical" },
  { label: "Percentile profile", value: "datamb" },
  { label: "FBref Form", value: "fbref" },
  { label: "Understat Context", value: "understat" },
  { label: "Experimental shot model", value: "understat-model" }
];

export default function PlayerProfileView({ player }: PlayerProfileViewProps) {
  const [activeTab, setActiveTab] = useState("overview");
  const [showAllFbref, setShowAllFbref] = useState(false);
  const [showAllUnderstat, setShowAllUnderstat] = useState(false);
  const [showAllUnderstatModel, setShowAllUnderstatModel] = useState(false);
  const weakStatsBombSample = player.statsbomb_shots < 20;

  const understatRows = useMemo(
    () => dedupeUnderstatRows(player.understat_recent_rows ?? []),
    [player.understat_recent_rows]
  );
  const visibleFbrefRows = showAllFbref ? player.fbref_recent_rows : latestSeasonRows(player.fbref_recent_rows, 3);
  const visibleUnderstatRows = showAllUnderstat ? understatRows : latestSeasonRows(understatRows, 3);
  const understatModelRows = player.understat_model_recent_rows ?? [];
  const visibleUnderstatModelRows = showAllUnderstatModel
    ? understatModelRows
    : latestSeasonRows(understatModelRows, 3);
  const datamb = player.datamb_25_26;
  const datambAvailable = Boolean(datamb?.available);
  const availableSourceCount = [
    player.statsbomb_shots > 0,
    player.fbref_available,
    player.understat_available,
    player.understat_model_available,
    datambAvailable
  ].filter(Boolean).length;
  const noMatchedData = availableSourceCount === 0;

  return (
    <div className="space-y-7">
      <section className="surface-hero p-5 md:p-7">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.85fr)]">
          <div className="flex flex-col gap-5 sm:flex-row">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-pitch-700 text-2xl font-semibold text-white">
              {initials(player.player)}
            </div>
            <div>
              <p className="stat-label text-grass-400">{player.world_cup_team}</p>
              <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">{player.player}</h1>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="rounded-md border border-white/10 bg-white/[0.05] px-2.5 py-1 text-xs text-slate-300">
                  {player.position_group ?? player.position ?? "Position unknown"}
                </span>
                <DataConfidenceBadge
                  value={player.data_confidence}
                  hasHistoricalSample={player.statsbomb_shots > 0}
                  hasExternalContext={playerHasExternalContext(player)}
                />
              </div>
              <p className="mt-3 text-sm text-slate-300">
                {player.club ?? "Club unknown"} - {shortLeagueName(player.league)}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            <AvailabilityStrip
              statsbombShots={player.statsbomb_shots}
              fbrefAvailable={player.fbref_available}
              understatAvailable={Boolean(player.understat_available)}
              understatModelAvailable={Boolean(player.understat_model_available)}
              datambAvailable={datambAvailable}
            />
            <TakeawayCard
              label="Data read"
              value={sourceTakeaway({
                statsbombShots: player.statsbomb_shots,
                fbrefAvailable: player.fbref_available,
                understatAvailable: Boolean(player.understat_available)
              })}
              detail="When the historical sample is weak, use club context to understand recent volume and form."
            />
          </div>
        </div>
      </section>

      {weakStatsBombSample && !noMatchedData ? (
        <DataStateCallout title="Limited historical shot sample" tone="warning">
          Small StatsBomb shot sample: use the club and percentile context below to better understand recent player form.
        </DataStateCallout>
      ) : null}

      <QuickReadCard tone={noMatchedData ? "quiet" : weakStatsBombSample ? "warning" : "default"}>
        {playerQuickRead(player)}
      </QuickReadCard>

      {noMatchedData ? (
        <EmptyDataState
          title="No matched data yet"
          action={
            <a href="/coverage" className="inline-flex rounded-md bg-grass-500 px-4 py-2 text-sm font-semibold text-pitch-900 hover:bg-grass-400">
              Check team coverage
            </a>
          }
        >
          <p>
            This player exists in the World Cup squad layer, but we do not currently have a matched StatsBomb,
            Percentile profile, FBref, or Understat profile.
          </p>
          <ul className="mt-3 space-y-1">
            <li>- The player may not appear in the open StatsBomb competitions used here.</li>
            <li>- Name matching can differ across data sources.</li>
            <li>- Some leagues or clubs are not covered by the external sources.</li>
          </ul>
        </EmptyDataState>
      ) : null}

      {!noMatchedData && availableSourceCount <= 1 ? (
        <DataStateCallout title="Limited profile" tone="warning">
          This player has a narrow matched profile in the current dashboard build. Treat the visible source as context,
          not a complete player evaluation.
        </DataStateCallout>
      ) : null}

      {!noMatchedData ? (
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <SourceSummaryCard
          source="statsbomb"
          title="Historical StatsBomb"
          primary={`${formatNumber(player.statsbomb_shots)} shots`}
          detail={`${formatNumber(player.total_xg, 2)} xG, ${formatNumber(player.statsbomb_goals)} goals. ${formatDateRange(player.statsbomb_date_range)}.`}
        />
        <SourceSummaryCard
          source="datamb"
          title="Percentile profile"
          primary={datambAvailable ? `${formatNumber(datamb?.minutes, 0)} min` : "Not available"}
          detail={
            datambAvailable
              ? `${datamb?.template ?? "Template unknown"} percentile context.`
              : datamb?.reason ?? "No percentile profile matched."
          }
          muted={!datambAvailable}
        />
        <SourceSummaryCard
          source="fbref"
          title="Recent FBref Form"
          primary={player.fbref_available ? `${formatNumber(sumRows(player.fbref_recent_rows, "shots"))} shots` : "Not available"}
          detail={player.fbref_available ? "Aggregate club/league form where pulled." : "No recent form match in currently supported leagues."}
          muted={!player.fbref_available}
        />
        <SourceSummaryCard
          source="understat"
          title="Understat Club xG"
          primary={player.understat_available ? `${formatNumber(sumRows(understatRows, "xg"), 2)} xG` : "Not available"}
          detail={player.understat_available ? "Club xG context from covered leagues." : "No matched Understat context in the current archive."}
          muted={!player.understat_available}
        />
        <SourceSummaryCard
          source="understat"
          title="Experimental shot model"
          primary={
            player.understat_model_available && player.understat_model_summary
              ? `${formatNumber(player.understat_model_summary.experimental_xg, 2)} xG`
              : "Not available"
          }
          detail={
            player.understat_model_available && player.understat_model_summary
              ? `${formatNumber(player.understat_model_summary.shots)} modeled Understat shots. Research layer only.`
              : "No matched Understat shot-model context."
          }
          muted={!player.understat_model_available}
        />
      </section>
      ) : null}

      {!noMatchedData ? <SectionTabs options={tabs} value={activeTab} onChange={setActiveTab} /> : null}

      {!noMatchedData && activeTab === "overview" ? (
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.85fr)]">
          <div className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Overview</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              This profile separates historical shot-quality evidence from recent club context. It avoids treating a small
              StatsBomb sample as a complete player forecast.
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <TakeawayCard label="Finishing vs expected" value={formatNumber(player.goals_minus_xg, 2)} />
              <TakeawayCard label="Average chance quality" value={formatNumber(player.avg_xg_per_shot, 3)} />
              <TakeawayCard label="Open-data sample range" value={formatDateRange(player.statsbomb_date_range)} />
            </div>
          </div>
          <SourceLegend />
        </section>
      ) : null}

      {!noMatchedData && activeTab === "historical" ? (
        <section className="grid gap-5 xl:grid-cols-[minmax(0,0.75fr)_minmax(320px,1.25fr)]">
          <div className="surface-card p-5">
            <div className="flex items-center gap-2">
              <SourceBadge source="statsbomb" />
              <h2 className="text-xl font-semibold text-white">Historical xG output</h2>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <StatCard label="Past sample shots" value={formatNumber(player.statsbomb_shots)} detail="StatsBomb open data" accent="statsbomb" />
              <StatCard label="Goals" value={formatNumber(player.statsbomb_goals)} accent="statsbomb" />
              <StatCard label="Past sample xG" value={formatNumber(player.total_xg, 2)} detail="Not a 2026 forecast" accent="statsbomb" />
              <StatCard label="Finishing vs expected" value={formatNumber(player.goals_minus_xg, 2)} detail="Goals minus xG" accent="statsbomb" />
            </div>
          </div>
          <PitchShotMap
            title="Shot-Location Profile"
            shots={player.shot_points ?? []}
            sampleSize={player.statsbomb_shots}
            emptyMessage="No reliable shot-location coordinates are available for this player in the current StatsBomb sample."
          />
        </section>
      ) : null}

      {!noMatchedData && activeTab === "fbref" ? (
        <SourceTableSection
          source="fbref"
          title="Recent Club/League Shooting Context from FBref"
          explanation="FBref adds recent aggregate player context where available, especially when the historical shot sample is small."
          rows={visibleFbrefRows}
          columns={fbrefColumns}
          emptyMessage="FBref context is unavailable for this player with the currently supported/pulled leagues."
          canExpand={player.fbref_recent_rows.length > 3}
          expanded={showAllFbref}
          onToggle={() => setShowAllFbref((current) => !current)}
        />
      ) : null}

      {!noMatchedData && activeTab === "understat" ? (
        <SourceTableSection
          source="understat"
          title="Understat Club xG Context"
          explanation="Understat is club-season xG context only. It has not been used to retrain the StatsBomb model."
          rows={visibleUnderstatRows}
          columns={understatColumns}
          emptyMessage="Understat club xG context is not available for this player in the current archive."
          canExpand={understatRows.length > 3}
          expanded={showAllUnderstat}
          onToggle={() => setShowAllUnderstat((current) => !current)}
        />
      ) : null}

      {!noMatchedData && activeTab === "understat-model" ? (
        <section className="space-y-5">
          <DataStateCallout title="Experimental research layer" tone="info">
            This section applies our experimental Understat-only shot model to matched Understat club shots. It is shown for
            context and comparison, not as the production player xG layer.
          </DataStateCallout>

          {player.understat_model_summary ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <StatCard
                label="Modeled Shots"
                value={formatNumber(player.understat_model_summary.shots)}
                accent="understat"
              />
              <StatCard
                label="Experimental xG"
                value={formatNumber(player.understat_model_summary.experimental_xg, 2)}
                accent="understat"
              />
              <StatCard
                label="Understat Source xG"
                value={formatNumber(player.understat_model_summary.understat_source_xg, 2)}
                accent="understat"
              />
              <StatCard
                label="Model - Source"
                value={formatNumber(player.understat_model_summary.experimental_minus_source_xg, 2)}
                accent="understat"
              />
              <StatCard
                label="High-xG Shots"
                value={formatNumber(player.understat_model_summary.high_xg_shots)}
                accent="understat"
              />
            </div>
          ) : null}

          <SourceTableSection
            source="understat"
            title="Experimental Understat Shot-Model Rows"
            explanation="Rows are grouped by player, club, league, and season. Understat source xG is a benchmark and was not used as a model input."
            rows={visibleUnderstatModelRows}
            columns={understatModelColumns}
            emptyMessage="Experimental Understat shot-model context is not available for this player."
            canExpand={understatModelRows.length > 3}
            expanded={showAllUnderstatModel}
            onToggle={() => setShowAllUnderstatModel((current) => !current)}
          />
        </section>
      ) : null}

      {!noMatchedData && activeTab === "datamb" ? (
        <DataMbSection datamb={datamb} playerName={player.player} />
      ) : null}
    </div>
  );
}

const fbrefColumns: CompactColumn<FbrefRecentRow>[] = [
  { key: "season", label: "Season", formatter: (value) => normalizeSeasonLabel(value as string | number | null) },
  { key: "league", label: "League", formatter: (value) => shortLeagueName(value as string | null) },
  { key: "team", label: "Club" },
  { key: "minutes", label: "Min" },
  { key: "goals", label: "G" },
  { key: "assists", label: "A", hideWhenEmpty: true },
  { key: "shots", label: "Sh" },
  { key: "shots_on_target", label: "SoT", hideWhenEmpty: true },
  { key: "shots_per_90", label: "Sh/90", digits: 2, hideWhenEmpty: true },
  { key: "xg", label: "xG", digits: 2, hideWhenEmpty: true },
  { key: "npxg", label: "npxG", digits: 2, hideWhenEmpty: true },
  { key: "xg_per_90", label: "xG/90", digits: 2, hideWhenEmpty: true }
];

const understatColumns: CompactColumn<UnderstatRecentRow>[] = [
  { key: "season", label: "Season", formatter: (value) => normalizeSeasonLabel(value as string | number | null) },
  { key: "league", label: "League", formatter: (value) => shortLeagueName(value as string | null), hideWhenEmpty: true },
  { key: "team", label: "Club" },
  { key: "minutes", label: "Min" },
  { key: "goals", label: "G" },
  { key: "assists", label: "A", hideWhenEmpty: true },
  { key: "shots", label: "Sh" },
  { key: "xg", label: "xG", digits: 2 },
  { key: "npxg", label: "npxG", digits: 2, hideWhenEmpty: true },
  { key: "xa", label: "xA", digits: 2, hideWhenEmpty: true },
  { key: "key_passes", label: "KP", hideWhenEmpty: true },
  { key: "xg_chain", label: "xGChain", digits: 2, hideWhenEmpty: true },
  { key: "avg_shot_xg", label: "Avg Sh xG", digits: 3, hideWhenEmpty: true }
];

const understatModelColumns: CompactColumn<UnderstatModelRecentRow>[] = [
  { key: "season", label: "Season", formatter: (value) => normalizeSeasonLabel(value as string | number | null) },
  { key: "league", label: "League", formatter: (value) => shortLeagueName(value as string | null), hideWhenEmpty: true },
  { key: "team", label: "Club" },
  { key: "understat_model_shots", label: "Shots" },
  { key: "understat_model_goals", label: "Goals" },
  { key: "understat_model_xg", label: "Exp xG", digits: 2 },
  { key: "understat_source_xg", label: "Source xG", digits: 2 },
  { key: "understat_model_minus_source_xg", label: "Diff", digits: 2 },
  { key: "avg_understat_model_xg", label: "Avg Exp xG", digits: 3 },
  { key: "high_xg_shots", label: "High xG", hideWhenEmpty: true }
];

function SourceSummaryCard({
  source,
  title,
  primary,
  detail,
  muted = false
}: {
  source: "statsbomb" | "fbref" | "understat" | "datamb";
  title: string;
  primary: string;
  detail: string;
  muted?: boolean;
}) {
  return (
    <div className={`rounded-lg border p-4 shadow-card ${muted ? "border-white/10 bg-white/[0.035]" : "border-white/10 bg-white/[0.05]"}`}>
      <SourceBadge source={source} muted={muted} />
      <p className="mt-3 text-sm font-semibold text-white">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{primary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-400">{detail}</p>
    </div>
  );
}

function DataMbSection({
  datamb,
  playerName
}: {
  datamb: PlayerProfile["datamb_25_26"];
  playerName: string;
}) {
  const metrics = Object.entries(datamb?.percentiles ?? {});
  const radarUrl = assetUrl(datamb?.generated_radar_path);

  if (!datamb?.available) {
    return (
      <section className="space-y-5">
        <DataStateCallout title="No percentile profile matched" tone="neutral">
          No percentile profile matched for this player in the current 25/26 external context layer.
        </DataStateCallout>
        <div className="surface-card p-5">
          <div className="flex items-center gap-2">
            <SourceBadge source="datamb" muted />
            <h2 className="text-xl font-semibold text-white">Percentile profile</h2>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            DataMB coverage depends on the public/free 25/26 player profile layer and selected league availability.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-5">
      <DataStateCallout title="External percentile context" tone="info">
        DataMB values are 0-100 percentiles. They are external scouting context, not raw per-90 stats and not model inputs.
      </DataStateCallout>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Season" value={datamb.season ?? "25/26"} accent="datamb" />
        <StatCard label="Template" value={datamb.template ?? "N/A"} accent="datamb" />
        <StatCard label="Club" value={datamb.club ?? "N/A"} accent="datamb" />
        <StatCard label="Minutes" value={formatNumber(datamb.minutes, 0)} accent="datamb" />
      </div>

      <section className="grid gap-5 xl:grid-cols-[minmax(320px,0.9fr)_minmax(0,1.1fr)]">
        <div className="surface-card p-5">
          <div className="flex items-center gap-2">
            <SourceBadge source="datamb" />
            <h2 className="text-xl font-semibold text-white">Percentile radar</h2>
          </div>
          {radarUrl ? (
            <img
              src={radarUrl}
              alt={`${playerName} 25/26 percentile profile radar`}
              className="mt-5 w-full rounded-lg border border-white/10 bg-pitch-900"
            />
          ) : (
            <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.035] p-4 text-sm text-slate-300">
              Radar chart has not been generated for this player yet.
            </div>
          )}
        </div>

        <div className="surface-card p-5">
          <div className="flex items-center gap-2">
            <SourceBadge source="datamb" />
            <h2 className="text-xl font-semibold text-white">Percentile Metrics</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Higher numbers mean the player ranked higher relative to the DataMB comparison group for that template.
          </p>
          <div className="mt-5 grid gap-2 sm:grid-cols-2">
            {metrics.length ? (
              metrics.map(([metric, value]) => (
                <div key={metric} className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
                  <p className="text-xs uppercase tracking-[0.12em] text-slate-400">{metric}</p>
                  <p className="mt-1 text-xl font-semibold text-white">{formatNumber(value, 0)}</p>
                  <p className="mt-1 text-xs text-slate-500">{percentileHint(value)}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400">No percentile metrics were available in the cleaned DataMB row.</p>
            )}
          </div>
        </div>
      </section>
    </section>
  );
}

function SourceTableSection<T extends object>({
  source,
  title,
  explanation,
  rows,
  columns,
  emptyMessage,
  canExpand,
  expanded,
  onToggle
}: {
  source: "fbref" | "understat";
  title: string;
  explanation: string;
  rows: T[];
  columns: CompactColumn<T>[];
  emptyMessage: string;
  canExpand: boolean;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section className="surface-card p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <SourceBadge source={source} />
            <h2 className="text-xl font-semibold text-white">{title}</h2>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{explanation}</p>
        </div>
        {canExpand ? (
          <button
            type="button"
            onClick={onToggle}
            className="rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-slate-200 transition hover:bg-white/[0.07]"
          >
            {expanded ? "Show latest 3" : "Show all"}
          </button>
        ) : null}
      </div>
      <div className="mt-5">
        <CompactSeasonTable rows={rows} columns={columns} emptyMessage={emptyMessage} />
      </div>
    </section>
  );
}

function sumRows<T extends object>(rows: T[], key: keyof T) {
  return rows.reduce((sum, row) => {
    const value = row[key];
    return typeof value === "number" ? sum + value : sum;
  }, 0);
}

function playerQuickRead(player: PlayerProfile) {
  const hasExternal = playerHasExternalContext(player);

  if (player.statsbomb_shots >= 20 && hasExternal) {
    return "This player has a usable historical StatsBomb shot sample plus recent club context. The historical xG numbers show past chance quality, while FBref, Understat, and Percentile profile help explain recent form where available.";
  }

  if (player.statsbomb_shots > 0) {
    return "This player has limited historical StatsBomb shots, so lean more on recent club context from FBref, Understat, and Percentile profile where available.";
  }

  if (hasExternal) {
    return "This player has no historical StatsBomb shot sample in the current dashboard build, but matched club or percentile context can still help describe recent form.";
  }

  return "We do not have enough matched data for this player yet. This does not mean the player is weak; it only means the current data sources do not expose a strong profile.";
}

function percentileHint(value: number) {
  if (value >= 90) {
    return "Elite percentile vs comparison group";
  }
  if (value >= 70) {
    return "Strong percentile vs comparison group";
  }
  if (value >= 40) {
    return "Around average percentile";
  }
  return "Lower percentile vs comparison group";
}
