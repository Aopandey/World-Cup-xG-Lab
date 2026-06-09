"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import EmptyDataState from "@/components/EmptyDataState";
import EvidenceBadge from "@/components/EvidenceBadge";
import MetricCard from "@/components/MetricCard";
import SourceAvailabilityStrip from "@/components/SourceAvailabilityStrip";
import {
  formatNumber,
  initials,
  playerHasExternalContext,
  shortLeagueName,
  slugPath
} from "@/lib/format";
import type { DataConfidence, PlayerProfile } from "@/lib/types";

type PlayerXgExplorerProps = {
  players: PlayerProfile[];
};

type SortKey = "shots" | "xg" | "goals" | "finishing";

const evidenceOptions: Array<{ value: "All" | DataConfidence; label: string }> = [
  { value: "All", label: "All evidence" },
  { value: "Strong", label: "Strong evidence" },
  { value: "Moderate", label: "Some evidence" },
  { value: "Limited", label: "Limited evidence" },
  { value: "Unavailable", label: "No historical sample" }
];

const sortOptions: Array<{ value: SortKey; label: string }> = [
  { value: "shots", label: "Most past sample shots" },
  { value: "xg", label: "Highest past sample xG" },
  { value: "goals", label: "Most goals" },
  { value: "finishing", label: "Finishing vs expected" }
];

const inputClassName =
  "mt-2 w-full rounded-lg border border-white/10 bg-pitch-900 px-3 py-2 text-sm text-white shadow-inner outline-none transition placeholder:text-slate-500 focus:border-grass-400";

export default function PlayerXgExplorer({ players }: PlayerXgExplorerProps) {
  const [search, setSearch] = useState("");
  const [team, setTeam] = useState("All");
  const [position, setPosition] = useState("All");
  const [evidence, setEvidence] = useState<"All" | DataConfidence>("All");
  const [minimumShots, setMinimumShots] = useState(1);
  const [sortKey, setSortKey] = useState<SortKey>("shots");

  const historicalPlayers = useMemo(
    () => players.filter((player) => player.statsbomb_shots > 0),
    [players]
  );

  const summary = useMemo(() => {
    const teamsRepresented = new Set(historicalPlayers.map((player) => player.world_cup_team).filter(Boolean));

    return {
      playersWithShots: historicalPlayers.length,
      teamsRepresented: teamsRepresented.size
    };
  }, [historicalPlayers]);

  const teams = useMemo(() => {
    return ["All", ...uniqueSorted(players.map((player) => player.world_cup_team))];
  }, [players]);

  const positions = useMemo(() => {
    return ["All", ...uniqueSorted(players.map((player) => player.position_group ?? player.position ?? "Position unknown"))];
  }, [players]);

  const filteredPlayers = useMemo(() => {
    const query = search.trim().toLowerCase();

    return [...players]
      .filter((player) => {
        const club = player.club ?? "";
        const haystack = `${player.player} ${player.world_cup_team} ${club}`.toLowerCase();
        const playerPosition = player.position_group ?? player.position ?? "Position unknown";

        if (query && !haystack.includes(query)) {
          return false;
        }

        if (team !== "All" && player.world_cup_team !== team) {
          return false;
        }

        if (position !== "All" && playerPosition !== position) {
          return false;
        }

        if (evidence !== "All" && player.data_confidence !== evidence) {
          return false;
        }

        return player.statsbomb_shots >= minimumShots;
      })
      .sort((a, b) => sortValue(b, sortKey) - sortValue(a, sortKey) || a.player.localeCompare(b.player));
  }, [evidence, minimumShots, players, position, search, sortKey, team]);

  return (
    <div className="space-y-8">
      <section className="surface-hero overflow-hidden p-5 md:p-7">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(300px,0.8fr)] lg:items-end">
          <div>
            <p className="stat-label text-grass-400">Player-level historical xG</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white md:text-5xl">
              Player xG Explorer
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-slate-300">
              Browse players with historical StatsBomb shot samples and model xG output. These rankings show past
              available data, not projected 2026 World Cup scoring.
            </p>
          </div>

          <div className="surface-inset p-4">
            <p className="stat-label">What this page shows</p>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              The default view ranks by sample size so strong evidence appears first. Use the filters to explore by
              team, position, evidence level, or minimum past shot sample.
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <MetricCard
          label="Players with past sample shots"
          value={formatNumber(summary.playersWithShots)}
          detail="StatsBomb historical sample"
          source="statsbomb"
          accent="statsbomb"
        />
        <MetricCard
          label="Teams represented"
          value={formatNumber(summary.teamsRepresented)}
          detail="National teams with at least one past sample shot"
        />
      </section>

      <section className="surface-card p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Find Player Samples</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
              Default filters show players with at least one historical StatsBomb shot. Lower the minimum shot filter
              to zero if you want to inspect squad players who only have club-context sources.
            </p>
          </div>
          <label className="min-w-[220px] text-sm font-semibold text-slate-300">
            Sort
            <select className={inputClassName} value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
              {sortOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <label className="text-sm font-semibold text-slate-300 xl:col-span-2">
            Search player, team, or club
            <input
              className={inputClassName}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Messi, Argentina, Inter Miami..."
            />
          </label>

          <label className="text-sm font-semibold text-slate-300">
            Team
            <select className={inputClassName} value={team} onChange={(event) => setTeam(event.target.value)}>
              {teams.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm font-semibold text-slate-300">
            Position
            <select className={inputClassName} value={position} onChange={(event) => setPosition(event.target.value)}>
              {positions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm font-semibold text-slate-300">
            Evidence
            <select
              className={inputClassName}
              value={evidence}
              onChange={(event) => setEvidence(event.target.value as "All" | DataConfidence)}
            >
              {evidenceOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-[minmax(180px,240px)_minmax(0,1fr)] md:items-end">
          <label className="text-sm font-semibold text-slate-300">
            Minimum shots
            <input
              className={inputClassName}
              type="number"
              min={0}
              step={1}
              value={minimumShots}
              onChange={(event) => setMinimumShots(Math.max(0, Number(event.target.value) || 0))}
            />
          </label>
          <div className="surface-inset p-3 text-sm leading-6 text-slate-400">
            <span className="font-semibold text-white">{formatNumber(filteredPlayers.length)}</span> players match the
            current filters. The numbers shown here describe past available samples, not projected 2026 tournament
            totals.
          </div>
        </div>
      </section>

      <section className="surface-card p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Player Samples</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Sorted by {sortOptions.find((option) => option.value === sortKey)?.label.toLowerCase() ?? "sample size"}.
            </p>
          </div>
        </div>

        {filteredPlayers.length ? (
          <div className="mt-5 grid gap-4">
            {filteredPlayers.map((player) => (
              <PlayerExplorerCard key={`${player.world_cup_team}-${player.player}`} player={player} />
            ))}
          </div>
        ) : (
          <div className="mt-5">
            <EmptyDataState title="No players match these filters.">
              Try lowering the minimum shot sample or clearing team/position filters.
            </EmptyDataState>
          </div>
        )}
      </section>

      <EmptyDataState title="Why sample size matters">
        A player with 80 historical shots gives the model more evidence than a player with 4 shots. Use this page to
        separate strong historical samples from limited ones.
      </EmptyDataState>
    </div>
  );
}

function PlayerExplorerCard({ player }: { player: PlayerProfile }) {
  const averageChanceQuality = averageXgPerShot(player);
  const hasHistoricalSample = player.statsbomb_shots > 0;
  const position = player.position_group ?? player.position ?? "Position unknown";
  const clubLine = [player.club ?? "Club unavailable", player.league ? shortLeagueName(player.league) : null]
    .filter(Boolean)
    .join(" - ");

  return (
    <article className="rounded-lg border border-white/10 bg-white/[0.04] p-4 shadow-card transition hover:border-grass-400/40 hover:bg-white/[0.06]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-pitch-700 text-sm font-semibold text-white">
            {initials(player.player)}
          </div>
          <div className="min-w-0">
            <p className="stat-label text-grass-400">{player.world_cup_team}</p>
            <h3 className="mt-1 truncate text-lg font-semibold text-white">{player.player}</h3>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="rounded-md border border-white/10 bg-white/[0.045] px-2 py-1 text-xs font-semibold text-slate-300">
                {position}
              </span>
              <EvidenceBadge
                level={player.data_confidence}
                hasHistoricalSample={hasHistoricalSample}
                hasExternalContext={playerHasExternalContext(player)}
              />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-300">{clubLine}</p>
          </div>
        </div>

        <div className="flex shrink-0 flex-col gap-3 lg:items-end">
          <SourceAvailabilityStrip
            compact
            statsbombShots={player.statsbomb_shots}
            fbrefAvailable={player.fbref_available}
            understatAvailable={Boolean(player.understat_available)}
            understatModelAvailable={Boolean(player.understat_model_available)}
            datambAvailable={Boolean(player.datamb_25_26?.available)}
          />
          <Link
            href={`/players/${slugPath(player.player)}`}
            className="inline-flex w-fit items-center rounded-lg border border-grass-400/40 bg-grass-400/10 px-3 py-2 text-sm font-semibold text-grass-400 transition hover:bg-grass-400/15"
          >
            Open full player profile
          </Link>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <CompactMetric label="Past sample shots" value={formatNumber(player.statsbomb_shots)} detail="StatsBomb" />
        <CompactMetric label="Goals" value={formatNumber(player.statsbomb_goals)} detail="Past sample" />
        <CompactMetric label="Past sample xG" value={formatNumber(player.total_xg, 2)} detail="Not a 2026 forecast" />
        <CompactMetric label="Finishing vs expected" value={formatSigned(player.goals_minus_xg)} detail="Goals minus xG" />
        <CompactMetric
          label="Average chance quality"
          value={averageChanceQuality === null ? "N/A" : formatNumber(averageChanceQuality, 3)}
          detail="xG per shot"
        />
      </div>
    </article>
  );
}

function CompactMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-white/10 bg-black/15 p-3">
      <p className="stat-label leading-5">{label}</p>
      <p className="mt-2 break-words text-xl font-semibold tracking-tight text-white">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-400">{detail}</p>
    </div>
  );
}

function uniqueSorted(values: Array<string | null | undefined>) {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort((a, b) => a.localeCompare(b));
}

function averageXgPerShot(player: PlayerProfile) {
  if (player.statsbomb_shots <= 0) {
    return null;
  }

  return player.total_xg / player.statsbomb_shots;
}

function sortValue(player: PlayerProfile, sortKey: SortKey) {
  if (sortKey === "xg") {
    return player.total_xg;
  }

  if (sortKey === "goals") {
    return player.statsbomb_goals;
  }

  if (sortKey === "finishing") {
    return player.goals_minus_xg;
  }

  return player.statsbomb_shots;
}

function formatSigned(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "N/A";
  }

  const numericValue = Number(value);
  return `${numericValue > 0 ? "+" : ""}${formatNumber(numericValue, 2)}`;
}
