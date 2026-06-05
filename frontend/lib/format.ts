import type { UnderstatRecentRow } from "./types";

export function formatNumber(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "N/A";
  }

  return Number(value).toLocaleString("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  });
}

export function formatPercent(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "N/A";
  }

  return `${(Number(value) * 100).toFixed(digits)}%`;
}

export function formatDateRange(range?: { earliest: string | null; latest: string | null }) {
  if (!range?.earliest || !range?.latest) {
    return "No match dates available";
  }

  return `${range.earliest} to ${range.latest}`;
}

export function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function flagLabel(flagCode: string | null | undefined) {
  if (!flagCode) {
    return "WC";
  }

  if (/^[A-Z]{2}$/.test(flagCode)) {
    const codePoints = [...flagCode].map((char) => 127397 + char.charCodeAt(0));
    return String.fromCodePoint(...codePoints);
  }

  return flagCode;
}

export function slugPath(value: string) {
  return encodeURIComponent(value);
}

export function assetUrl(path: string | null | undefined) {
  if (!path) {
    return null;
  }

  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  return new URL(path, apiBaseUrl).toString();
}

export function hasValue(value: unknown) {
  return value !== null && value !== undefined && value !== "" && value !== "N/A";
}

export function normalizeSeasonLabel(value: number | string | null | undefined) {
  if (!hasValue(value)) {
    return "N/A";
  }

  const raw = String(value).trim();
  const compactSeason = raw.match(/^(\d{2})(\d{2})$/);
  if (compactSeason) {
    return `20${compactSeason[1]}/${compactSeason[2]}`;
  }

  const longSeason = raw.match(/^(\d{4})[-/](\d{2}|\d{4})$/);
  if (longSeason) {
    return `${longSeason[1]}/${longSeason[2].slice(-2)}`;
  }

  return raw;
}

export function seasonSortValue(value: number | string | null | undefined) {
  if (!hasValue(value)) {
    return 0;
  }

  const label = normalizeSeasonLabel(value);
  const startYear = label.match(/^(\d{4})/);
  if (startYear) {
    return Number(startYear[1]);
  }

  return Number(String(value).replace(/\D/g, "")) || 0;
}

export function shortLeagueName(value: string | null | undefined) {
  if (!value) {
    return "League unknown";
  }

  const cleaned = value
    .replace(/\s*\/\s*.*football league system/i, "")
    .replace(/\s+/g, " ")
    .trim();

  const lower = cleaned.toLowerCase();
  const leagueMap: Record<string, string> = {
    "eng-premier league": "Premier League",
    "english premier league": "Premier League",
    "premier league": "Premier League",
    "esp-la liga": "La Liga",
    laliga: "La Liga",
    "la liga": "La Liga",
    "ger-bundesliga": "Bundesliga",
    bundesliga: "Bundesliga",
    "ita-serie a": "Serie A",
    "serie a": "Serie A",
    "fra-ligue 1": "Ligue 1",
    "ligue 1": "Ligue 1",
    "por-primeira liga": "Primeira Liga",
    "primeira liga": "Primeira Liga",
    "ned-eredivisie": "Eredivisie",
    eredivisie: "Eredivisie",
    "bel-pro league": "Belgian Pro League",
    "belgian pro league": "Belgian Pro League",
    "usa-mls": "MLS",
    "major league soccer": "MLS",
    mls: "MLS",
    "mex-liga mx": "Liga MX",
    "liga mx": "Liga MX",
    "bra-serie a": "Brazil Serie A",
    "campeonato brasileiro serie a": "Brazil Serie A",
    "arg-primera division": "Argentina Primera Division",
    "argentina primera division": "Argentina Primera Division",
    "tur-super lig": "Super Lig",
    "turkish super lig": "Super Lig",
    "turkish süper lig": "Super Lig",
    "ksa-saudi pro league": "Saudi Pro League",
    "saudi pro league": "Saudi Pro League",
    "sco-premiership": "Scottish Premiership",
    "scottish premiership": "Scottish Premiership",
    "rfpl": "Russian Premier League",
    "russian premier league": "Russian Premier League"
  };

  return leagueMap[lower] ?? cleaned.replace(/^[A-Z]{3}-/, "");
}

export function sourceTakeaway({
  statsbombShots,
  fbrefAvailable,
  understatAvailable
}: {
  statsbombShots: number;
  fbrefAvailable?: boolean;
  understatAvailable?: boolean;
}) {
  if (statsbombShots >= 250) {
    return "Historical sample strong";
  }

  if (statsbombShots >= 50) {
    return "Historical sample moderate";
  }

  if (statsbombShots > 0) {
    return "Limited historical sample";
  }

  if (fbrefAvailable || understatAvailable) {
    return "Club context only";
  }

  return "Coverage unavailable";
}

function understatRichness(row: UnderstatRecentRow) {
  return [
    row.league ? 12 : 0,
    row.shot_data_shots ? 8 : 0,
    row.shot_data_xg ? 8 : 0,
    row.avg_shot_xg ? 5 : 0,
    row.xg ? 4 : 0,
    row.npxg ? 3 : 0,
    row.xa ? 3 : 0,
    row.shots ? 2 : 0,
    row.minutes ? 1 : 0
  ].reduce((sum, score) => sum + score, 0);
}

export function dedupeUnderstatRows(rows: UnderstatRecentRow[] = []) {
  const bestRows = new Map<string, UnderstatRecentRow>();

  rows.forEach((row, index) => {
    const key = [
      normalizeSeasonLabel(row.season),
      row.team?.toLowerCase().trim() ?? ""
    ];

    const duplicateKey = key.join("|");
    const current = bestRows.get(duplicateKey);
    if (!current || understatRichness(row) > understatRichness(current)) {
      bestRows.set(duplicateKey, row);
    }
  });

  return [...bestRows.values()].sort((a, b) => seasonSortValue(b.season) - seasonSortValue(a.season));
}

export function latestSeasonRows<T extends { season?: number | string | null }>(rows: T[] = [], count = 3) {
  return [...rows]
    .sort((a, b) => seasonSortValue(b.season) - seasonSortValue(a.season))
    .slice(0, count);
}

export function rowsHaveValue<T extends Record<string, unknown>>(rows: T[], keys: Array<keyof T>) {
  return keys.some((key) => rows.some((row) => hasValue(row[key])));
}
