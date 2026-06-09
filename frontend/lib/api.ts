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

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl() {
  if (typeof window === "undefined") {
    return (
      process.env.API_INTERNAL_BASE_URL ??
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      DEFAULT_API_BASE_URL
    );
  }

  return getPublicApiBaseUrl();
}

export function getPublicApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

type QueryValue = string | number | boolean | null | undefined;

function buildUrl(path: string, query?: Record<string, QueryValue>) {
  const url = buildAbsoluteUrl(path, getApiBaseUrl());

  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }

  return url.toString();
}

export function buildAbsoluteUrl(path: string, baseUrl: string) {
  if (baseUrl.startsWith("/")) {
    if (typeof window === "undefined") {
      throw new Error("A relative API base URL requires API_INTERNAL_BASE_URL during server rendering.");
    }
    return new URL(path, new URL(baseUrl, window.location.origin));
  }

  return new URL(path, baseUrl);
}

async function apiGet<T>(path: string, query?: Record<string, QueryValue>): Promise<T> {
  let response: Response;

  try {
    response = await fetch(buildUrl(path, query), {
      cache: "no-store",
      headers: {
        Accept: "application/json"
      }
    });
  } catch {
    throw new Error(
      `Could not reach the World Cup xG Lab API at ${getApiBaseUrl()}. Start the FastAPI backend and try again.`
    );
  }

  if (!response.ok) {
    let message = `The World Cup xG Lab API returned status ${response.status}.`;
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
