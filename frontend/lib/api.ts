import type {
  DataCoverage,
  ModelSummary,
  PlayerFilters,
  PlayerProfile,
  PlayersResponse,
  SearchResponse,
  SquadResponse,
  Team,
  TeamProfile
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type QueryValue = string | number | boolean | null | undefined;

function buildUrl(path: string, query?: Record<string, QueryValue>) {
  const url = new URL(path, API_BASE_URL);

  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }

  return url.toString();
}

async function apiGet<T>(path: string, query?: Record<string, QueryValue>): Promise<T> {
  const response = await fetch(buildUrl(path, query), {
    cache: "no-store",
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    let message = `API request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Keep the generic message when the response body is not JSON.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function getTeams() {
  return apiGet<Team[]>("/api/teams");
}

export function getTeamProfile(teamName: string) {
  return apiGet<TeamProfile>(`/api/teams/${encodeURIComponent(teamName)}`);
}

export function getTeamSquad(teamName: string) {
  return apiGet<SquadResponse>(`/api/teams/${encodeURIComponent(teamName)}/squad`);
}

export function getPlayers(filters: PlayerFilters = {}) {
  return apiGet<PlayersResponse>("/api/players", { ...filters });
}

export function getPlayerProfile(playerName: string) {
  return apiGet<PlayerProfile>(`/api/players/${encodeURIComponent(playerName)}`);
}

export function getCoverage() {
  return apiGet<DataCoverage>("/api/coverage");
}

export function getModelSummary() {
  return apiGet<ModelSummary>("/api/model/summary");
}

export function search(q: string) {
  return apiGet<SearchResponse>("/api/search", { q });
}
