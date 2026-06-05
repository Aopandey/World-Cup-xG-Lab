"use client";

import { useMemo, useState } from "react";

import AvailabilityStrip from "@/components/AvailabilityStrip";
import CompactSeasonTable from "@/components/CompactSeasonTable";
import type { CompactColumn } from "@/components/CompactSeasonTable";
import DataConfidenceBadge from "@/components/DataConfidenceBadge";
import DataStateCallout from "@/components/DataStateCallout";
import PitchShotMap from "@/components/PitchShotMap";
import SectionTabs from "@/components/SectionTabs";
import SourceBadge from "@/components/SourceBadge";
import SourceLegend from "@/components/SourceLegend";
import StatCard from "@/components/StatCard";
import TakeawayCard from "@/components/TakeawayCard";
import {
  dedupeUnderstatRows,
  formatDateRange,
  formatNumber,
  initials,
  latestSeasonRows,
  normalizeSeasonLabel,
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
  { label: "FBref Form", value: "fbref" },
  { label: "Understat Context", value: "understat" },
  { label: "Understat Model", value: "understat-model" }
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
                <DataConfidenceBadge value={player.data_confidence} />
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

      {weakStatsBombSample ? (
        <DataStateCallout title="Limited historical shot sample" tone="warning">
          Small StatsBomb shot sample: use the FBref and Understat context below to better understand recent player form.
        </DataStateCallout>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-4">
        <SourceSummaryCard
          source="statsbomb"
          title="Historical StatsBomb"
          primary={`${formatNumber(player.statsbomb_shots)} shots`}
          detail={`${formatNumber(player.total_xg, 2)} xG, ${formatNumber(player.statsbomb_goals)} goals. ${formatDateRange(player.statsbomb_date_range)}.`}
        />
        <SourceSummaryCard
          source="fbref"
          title="Recent FBref Form"
          primary={player.fbref_available ? `${formatNumber(sumRows(player.fbref_recent_rows, "shots"))} shots` : "Not available"}
          detail={player.fbref_available ? "Aggregate club/league form where pulled." : "Unavailable with currently supported/pulled leagues."}
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
          title="Experimental Understat xG"
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

      <SectionTabs options={tabs} value={activeTab} onChange={setActiveTab} />

      {activeTab === "overview" ? (
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.85fr)]">
          <div className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Overview</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              This profile separates historical shot-quality evidence from recent club context. It avoids treating a small
              StatsBomb sample as a complete player forecast.
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <TakeawayCard label="Goals - xG" value={formatNumber(player.goals_minus_xg, 2)} />
              <TakeawayCard label="Avg xG / Shot" value={formatNumber(player.avg_xg_per_shot, 3)} />
              <TakeawayCard label="Historical Range" value={formatDateRange(player.statsbomb_date_range)} />
            </div>
          </div>
          <SourceLegend />
        </section>
      ) : null}

      {activeTab === "historical" ? (
        <section className="grid gap-5 xl:grid-cols-[minmax(0,0.75fr)_minmax(320px,1.25fr)]">
          <div className="surface-card p-5">
            <div className="flex items-center gap-2">
              <SourceBadge source="statsbomb" />
              <h2 className="text-xl font-semibold text-white">Historical xG Output</h2>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <StatCard label="Shots" value={formatNumber(player.statsbomb_shots)} accent="statsbomb" />
              <StatCard label="Goals" value={formatNumber(player.statsbomb_goals)} accent="statsbomb" />
              <StatCard label="Total xG" value={formatNumber(player.total_xg, 2)} accent="statsbomb" />
              <StatCard label="Goals - xG" value={formatNumber(player.goals_minus_xg, 2)} accent="statsbomb" />
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

      {activeTab === "fbref" ? (
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

      {activeTab === "understat" ? (
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

      {activeTab === "understat-model" ? (
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
  source: "statsbomb" | "fbref" | "understat";
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
