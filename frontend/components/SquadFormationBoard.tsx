"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import EmptyDataState from "@/components/EmptyDataState";
import EvidenceBadge from "@/components/EvidenceBadge";
import SourceAvailabilityStrip from "@/components/SourceAvailabilityStrip";
import SourceBadge from "@/components/SourceBadge";
import {
  evidenceLabel,
  formatNumber,
  getEvidenceScore,
  normalizePositionGroup,
  playerHasExternalContext,
  playerRecentMinutes,
  shortLeagueName,
  slugPath
} from "@/lib/format";
import type { PlayerProfile } from "@/lib/types";

type SquadFormationBoardProps = {
  players: PlayerProfile[];
  teamName: string;
};

type BoardMode = "data" | "manual";
type SlotGroup = "goalkeeper" | "defender" | "midfielder" | "forward";

type FormationSlot = {
  id: string;
  label: string;
  group: SlotGroup;
};

const formationRows: FormationSlot[][] = [
  [
    { id: "lw", label: "LW", group: "forward" },
    { id: "st", label: "ST", group: "forward" },
    { id: "rw", label: "RW", group: "forward" }
  ],
  [
    { id: "lcm", label: "LCM", group: "midfielder" },
    { id: "cm", label: "CM", group: "midfielder" },
    { id: "rcm", label: "RCM", group: "midfielder" }
  ],
  [
    { id: "lb", label: "LB", group: "defender" },
    { id: "lcb", label: "LCB", group: "defender" },
    { id: "rcb", label: "RCB", group: "defender" },
    { id: "rb", label: "RB", group: "defender" }
  ],
  [{ id: "gk", label: "GK", group: "goalkeeper" }]
];

const slots = formationRows.flat();

export default function SquadFormationBoard({ players, teamName }: SquadFormationBoardProps) {
  const [mode, setMode] = useState<BoardMode>("data");
  const dataXI = useMemo(() => buildXI(players), [players]);
  const [manualXI, setManualXI] = useState<Record<string, string>>(() => dataXI);
  const activeXI = mode === "manual" ? manualXI : dataXI;
  const selectedPlayers = useMemo(
    () => Object.fromEntries(players.map((player) => [player.player, player])),
    [players]
  );
  const firstSelected = slots.map((slot) => selectedPlayers[activeXI[slot.id]]).find(Boolean) ?? players[0] ?? null;
  const [selectedPlayerName, setSelectedPlayerName] = useState<string | null>(firstSelected?.player ?? null);
  const selectedPlayer = selectedPlayerName ? selectedPlayers[selectedPlayerName] ?? firstSelected : firstSelected;

  if (!players.length) {
    return (
      <EmptyDataState title="No squad board available yet.">
        We have this team in the dashboard, but there is not enough position-level squad data to build a formation view.
      </EmptyDataState>
    );
  }

  function handleModeChange(nextMode: BoardMode) {
    setMode(nextMode);
    const xi = nextMode === "manual" ? manualXI : dataXI;
    const nextSelected = slots.map((slot) => selectedPlayers[xi[slot.id]]).find(Boolean);
    if (nextSelected) {
      setSelectedPlayerName(nextSelected.player);
    }
  }

  function updateManualSlot(slotId: string, playerName: string) {
    setManualXI((current) => ({ ...current, [slotId]: playerName }));
    setSelectedPlayerName(playerName);
  }

  return (
    <section className="space-y-4">
      <div className="surface-card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="stat-label text-grass-400">Squad Board</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Data XI</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
              A football-shaped view of the players with the strongest available data profile. This is not a predicted starting lineup.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              ["data", "Data XI"],
              ["manual", "Manual XI"]
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => handleModeChange(value as BoardMode)}
                className={`rounded-md border px-3 py-2 text-sm transition ${
                  mode === value
                    ? "border-grass-400/70 bg-grass-400/15 text-white"
                    : "border-white/10 bg-white/[0.035] text-slate-300 hover:bg-white/[0.065]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-[1.25rem] border border-grass-400/20 bg-[radial-gradient(circle_at_50%_20%,rgba(57,210,125,0.18),transparent_22rem),linear-gradient(180deg,rgba(11,69,54,0.88),rgba(7,36,39,0.94))] p-3 shadow-premium sm:p-5">
            <div className="relative min-h-[680px] overflow-hidden rounded-2xl border border-white/10 bg-[linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(180deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:25%_25%] p-3 sm:p-5">
              <div className="pointer-events-none absolute inset-5 rounded-[50%] border border-white/10" />
              <div className="pointer-events-none absolute left-1/2 top-0 h-full border-l border-white/10" />

              <div className="relative z-10 flex h-full min-h-[640px] flex-col justify-between gap-4">
                {formationRows.map((row, rowIndex) => (
                  <div key={rowIndex} className="flex items-start justify-center gap-3 sm:gap-5">
                    {row.map((slot) => {
                      const player = selectedPlayers[activeXI[slot.id]];
                      return (
                        <FormationSlotCard
                          key={slot.id}
                          slot={slot}
                          player={player}
                          players={players}
                          selectedNames={Object.values(activeXI)}
                          manual={mode === "manual"}
                          selected={Boolean(player && selectedPlayer?.player === player.player)}
                          onSelectPlayer={(name) => setSelectedPlayerName(name)}
                          onManualChange={(name) => updateManualSlot(slot.id, name)}
                        />
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <PlayerDetailPanel player={selectedPlayer} teamName={teamName} />
        </div>
      </div>
    </section>
  );
}

function FormationSlotCard({
  slot,
  player,
  players,
  selectedNames,
  manual,
  selected,
  onSelectPlayer,
  onManualChange
}: {
  slot: FormationSlot;
  player?: PlayerProfile;
  players: PlayerProfile[];
  selectedNames: string[];
  manual: boolean;
  selected: boolean;
  onSelectPlayer: (playerName: string) => void;
  onManualChange: (playerName: string) => void;
}) {
  const options = eligiblePlayers(players, slot.group, selectedNames, player?.player);
  const broaderPool = !players.some((candidate) => playerGroup(candidate) === slot.group);
  const headline = player ? playerHeadline(player) : "No player selected";

  return (
    <div className="w-[30%] min-w-[92px] max-w-[190px] flex-1 sm:min-w-[135px]">
      <button
        type="button"
        disabled={!player}
        onClick={() => player && onSelectPlayer(player.player)}
        aria-label={player ? `Open ${player.player} squad board details` : `${slot.label} empty slot`}
        className={`w-full rounded-xl border p-3 text-left shadow-card transition ${
          selected
            ? "border-grass-400/70 bg-pitch-700/95"
            : "border-white/10 bg-pitch-900/78 hover:border-grass-400/45 hover:bg-pitch-700/90"
        }`}
      >
        <p className="text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-grass-400">{slot.label}</p>
        <p className="mt-1 line-clamp-2 text-sm font-semibold leading-5 text-white">{player?.player ?? "Open slot"}</p>
        <p className="mt-1 text-xs text-slate-300">{player?.position_group ?? player?.position ?? slot.group}</p>
        <p className="mt-2 text-xs leading-5 text-slate-300">{headline}</p>
        {player ? (
          <div className="mt-2 flex flex-wrap gap-1">
            {player.statsbomb_shots > 0 ? <MiniSource label="SB" /> : null}
            {player.fbref_available ? <MiniSource label="FB" /> : null}
            {player.understat_available ? <MiniSource label="US" /> : null}
            {player.datamb_25_26?.available ? <MiniSource label="DM" /> : null}
          </div>
        ) : null}
      </button>
      {manual ? (
        <div className="mt-2">
          <label className="sr-only" htmlFor={`slot-${slot.id}`}>
            Choose {slot.label} player
          </label>
          <select
            id={`slot-${slot.id}`}
            value={player?.player ?? ""}
            onChange={(event) => onManualChange(event.target.value)}
            className="w-full rounded-md border border-white/10 bg-pitch-900 px-2 py-2 text-xs text-white"
          >
            {options.map((option) => (
              <option key={option.player} value={option.player}>
                {option.player}
              </option>
            ))}
          </select>
          {broaderPool ? <p className="mt-1 text-[0.65rem] text-amber-100">Using broader pool</p> : null}
        </div>
      ) : null}
    </div>
  );
}

function PlayerDetailPanel({ player, teamName }: { player?: PlayerProfile | null; teamName: string }) {
  if (!player) {
    return (
      <EmptyDataState title="Select a player">
        Choose a player chip on the pitch to see the source-by-source profile.
      </EmptyDataState>
    );
  }

  const fbrefShots = player.fbref_recent_rows.reduce((sum, row) => sum + (row.shots ?? 0), 0);
  const fbrefXg = player.fbref_recent_rows.reduce((sum, row) => sum + (row.xg ?? 0), 0);
  const understatXg = player.understat_recent_rows?.reduce((sum, row) => sum + (row.xg ?? 0), 0) ?? 0;

  return (
    <aside className="surface-inset p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="stat-label text-grass-400">Selected player</p>
          <h3 className="mt-2 text-2xl font-semibold text-white">{player.player}</h3>
          <p className="mt-2 text-sm text-slate-300">
            {teamName} - {player.position_group ?? player.position ?? "Position unavailable"} - {player.club ?? "Club unavailable"}
          </p>
          {player.league ? <p className="mt-1 text-xs text-slate-500">{shortLeagueName(player.league)}</p> : null}
        </div>
        <EvidenceBadge
          level={player.data_confidence}
          hasHistoricalSample={player.statsbomb_shots > 0}
          hasExternalContext={playerHasExternalContext(player)}
        />
      </div>

      <div className="mt-4">
        <SourceAvailabilityStrip
          statsbombShots={player.statsbomb_shots}
          fbrefAvailable={player.fbref_available}
          understatAvailable={Boolean(player.understat_available)}
          understatModelAvailable={Boolean(player.understat_model_available)}
          datambAvailable={Boolean(player.datamb_25_26?.available)}
        />
      </div>

      <div className="mt-5 space-y-3 text-sm">
        <DetailRow
          source="statsbomb"
          title="Past Chance Quality"
          value={player.statsbomb_shots > 0 ? `${formatNumber(player.statsbomb_shots)} shots - ${formatNumber(player.total_xg, 2)} estimated goals` : "No past chance-quality sample"}
          muted={player.statsbomb_shots <= 0}
        />
        <DetailRow
          source="datamb"
          title="Percentile Scouting Profile"
          value={player.datamb_25_26?.available ? `${formatNumber(player.datamb_25_26.minutes, 0)} minutes - percentile profile` : "No 25/26 profile matched"}
          muted={!player.datamb_25_26?.available}
        />
        <DetailRow
          source="fbref"
          title="Recent League Form"
          value={player.fbref_available ? `${formatNumber(fbrefShots)} shots${fbrefXg ? ` - ${formatNumber(fbrefXg, 2)} xG` : ""}` : "No recent league-form match"}
          muted={!player.fbref_available}
        />
        <DetailRow
          source="understat"
          title="Club xG Context"
          value={player.understat_available ? `${formatNumber(understatXg, 2)} club xG context` : "No club xG context"}
          muted={!player.understat_available}
        />
      </div>

      <Link
        href={`/players/${slugPath(player.player)}`}
        className="mt-5 inline-flex rounded-md bg-grass-500 px-4 py-2 text-sm font-semibold text-pitch-900 transition hover:bg-grass-400"
      >
        Open full player profile
      </Link>
    </aside>
  );
}

function DetailRow({
  source,
  title,
  value,
  muted = false
}: {
  source: "statsbomb" | "fbref" | "understat" | "datamb";
  title: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div className={`rounded-lg border p-3 ${muted ? "border-white/10 bg-white/[0.025]" : "border-white/10 bg-white/[0.045]"}`}>
      <div className="flex items-center gap-2">
        <SourceBadge source={source} muted={muted} />
        <p className="font-semibold text-white">{title}</p>
      </div>
      <p className="mt-2 text-slate-300">{value}</p>
    </div>
  );
}

function MiniSource({ label }: { label: string }) {
  return (
    <span className="rounded border border-white/10 bg-white/[0.08] px-1.5 py-0.5 text-[0.58rem] font-semibold text-slate-200">
      {label}
    </span>
  );
}

function buildXI(players: PlayerProfile[]) {
  const selected = new Set<string>();
  const xi: Record<string, string> = {};

  slots.forEach((slot) => {
    const candidate = pickPlayerForSlot(players, slot.group, selected);
    if (candidate) {
      selected.add(candidate.player);
      xi[slot.id] = candidate.player;
    }
  });

  return xi;
}

function pickPlayerForSlot(
  players: PlayerProfile[],
  group: SlotGroup,
  selected: Set<string>
) {
  const groupPlayers = players.filter((player) => playerGroup(player) === group && !selected.has(player.player));
  const fallbackPlayers = players.filter((player) => playerGroup(player) !== "goalkeeper" && !selected.has(player.player));
  const pool = groupPlayers.length ? groupPlayers : fallbackPlayers;

  return [...pool].sort((a, b) => slotScore(b, group) - slotScore(a, group))[0];
}

function slotScore(player: PlayerProfile, group: SlotGroup) {
  const groupBonus = playerGroup(player) === group ? 20 : 0;
  return getEvidenceScore(player) * 10 + groupBonus + player.total_xg;
}

function playerGroup(player: PlayerProfile): SlotGroup | "unknown" {
  return normalizePositionGroup(player.position_group ?? player.position) as SlotGroup | "unknown";
}

function eligiblePlayers(
  players: PlayerProfile[],
  group: SlotGroup,
  selectedNames: string[],
  currentPlayerName?: string
) {
  const groupPlayers = players.filter((player) => playerGroup(player) === group);
  const fallbackPlayers = players.filter((player) => playerGroup(player) !== "goalkeeper");
  const pool = groupPlayers.length ? groupPlayers : fallbackPlayers;
  const selected = new Set(selectedNames.filter((name) => name !== currentPlayerName));

  return pool
    .filter((player) => !selected.has(player.player))
    .sort((a, b) => getEvidenceScore(b) - getEvidenceScore(a) || b.total_xg - a.total_xg);
}

function playerHeadline(player: PlayerProfile) {
  if (player.statsbomb_shots > 0) {
    return `${formatNumber(player.statsbomb_shots)} shots - ${evidenceLabel(player.data_confidence, {
      hasHistoricalSample: true,
      hasExternalContext: playerHasExternalContext(player)
    })}`;
  }

  if (playerHasExternalContext(player)) {
    return "Club context only";
  }

  const recentMinutes = playerRecentMinutes(player);
  if (recentMinutes > 0) {
    return `${formatNumber(recentMinutes)} recent minutes`;
  }

  return "No matched data yet";
}
