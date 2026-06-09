"use client";

import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";
import type { ReactNode } from "react";

import { search } from "@/lib/api";
import { evidenceLabel, playerHasExternalContext, slugPath, teamHasExternalContext } from "@/lib/format";
import type { SearchResponse } from "@/lib/types";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();

    if (!trimmed) {
      setResults(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      setResults(await search(trimmed));
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "Search failed.");
      setResults(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-white/10 bg-pitch-900/50 p-3 shadow-card">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
        <label htmlFor="dashboard-search" className="sr-only">
          Search teams and players
        </label>
        <input
          id="dashboard-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search a national team, player, or club"
          className="min-h-12 flex-1 rounded-md border border-white/10 bg-black/20 px-4 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-grass-400/70"
        />
        <button
          type="submit"
          className="min-h-12 rounded-md bg-grass-500 px-5 text-sm font-semibold text-pitch-900 transition hover:bg-grass-400"
        >
          {loading ? "Searching" : "Search"}
        </button>
      </form>

      {error ? <p className="mt-3 text-sm text-rose-200">{error}</p> : null}

      {results ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <SearchResultGroup title={`Teams (${results.team_count})`}>
            {results.teams.slice(0, 5).map((team) => (
              <Link
                key={team.world_cup_team}
                href={`/teams/${slugPath(team.world_cup_team)}`}
                className="flex items-center justify-between rounded-md bg-white/[0.045] px-3 py-2 text-sm text-white transition hover:bg-white/[0.08]"
              >
                <span>{team.world_cup_team}</span>
                <span className="text-xs text-slate-400">
                  {evidenceLabel(team.data_confidence, {
                    hasHistoricalSample: team.statsbomb_shots > 0,
                    hasExternalContext: teamHasExternalContext(team)
                  })}
                </span>
              </Link>
            ))}
            {!results.team_count ? <p className="text-sm text-slate-400">No teams found.</p> : null}
          </SearchResultGroup>

          <SearchResultGroup title={`Players (${results.player_count})`}>
            {results.players.slice(0, 5).map((player) => (
              <Link
                key={`${player.world_cup_team}-${player.player}`}
                href={`/players/${slugPath(player.player)}`}
                className="block rounded-md bg-white/[0.045] px-3 py-2 text-sm text-white transition hover:bg-white/[0.08]"
              >
                <span>{player.player}</span>
                <span className="ml-2 text-xs text-slate-400">
                  {player.world_cup_team} - {evidenceLabel(player.data_confidence, {
                    hasHistoricalSample: player.statsbomb_shots > 0,
                    hasExternalContext: playerHasExternalContext(player)
                  })}
                </span>
              </Link>
            ))}
            {!results.player_count ? <p className="text-sm text-slate-400">No players found.</p> : null}
          </SearchResultGroup>
        </div>
      ) : null}
    </div>
  );
}

function SearchResultGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="surface-inset p-3">
      <p className="stat-label">{title}</p>
      <div className="mt-2 space-y-2">{children}</div>
    </div>
  );
}
