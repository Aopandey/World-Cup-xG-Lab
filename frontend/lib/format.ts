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
