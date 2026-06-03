"use client";

import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";

import { search } from "@/lib/api";
import { slugPath } from "@/lib/format";
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
    <div className="rounded-lg border border-white/10 bg-white/[0.045] p-4 shadow-card">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
        <label htmlFor="dashboard-search" className="sr-only">
          Search teams and players
        </label>
        <input
          id="dashboard-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search teams, players, or clubs"
          className="min-h-11 flex-1 rounded-lg border border-white/10 bg-pitch-900 px-4 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-grass-400/70"
        />
        <button
          type="submit"
          className="min-h-11 rounded-lg bg-grass-500 px-5 text-sm font-bold text-pitch-900 transition hover:bg-grass-400"
        >
          Search
        </button>
      </form>

      {loading ? <p className="mt-3 text-sm text-slate-300">Searching...</p> : null}
      {error ? <p className="mt-3 text-sm text-rose-200">{error}</p> : null}

      {results ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Teams ({results.team_count})
            </p>
            <div className="mt-2 space-y-2">
              {results.teams.slice(0, 6).map((team) => (
                <Link
                  key={team.world_cup_team}
                  href={`/teams/${slugPath(team.world_cup_team)}`}
                  className="block rounded-lg bg-white/[0.05] px-3 py-2 text-sm text-white hover:bg-white/[0.08]"
                >
                  {team.world_cup_team}
                </Link>
              ))}
              {!results.team_count ? <p className="text-sm text-slate-400">No teams found.</p> : null}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Players ({results.player_count})
            </p>
            <div className="mt-2 space-y-2">
              {results.players.slice(0, 6).map((player) => (
                <Link
                  key={`${player.world_cup_team}-${player.player}`}
                  href={`/players/${slugPath(player.player)}`}
                  className="block rounded-lg bg-white/[0.05] px-3 py-2 text-sm text-white hover:bg-white/[0.08]"
                >
                  {player.player}
                  <span className="ml-2 text-slate-400">{player.world_cup_team}</span>
                </Link>
              ))}
              {!results.player_count ? <p className="text-sm text-slate-400">No players found.</p> : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
