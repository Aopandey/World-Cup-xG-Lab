import { formatDateRange, formatNumber, playerHasExternalContext } from "@/lib/format";
import type { PlayerProfile, Team, TeamProfile } from "@/lib/types";

export type GeneratedSummary = {
  title: string;
  paragraphs: string[];
  takeaway: string;
  tone: "default" | "warning" | "quiet";
};

export function buildTeamSummary(profile: TeamProfile, team: Team | null): GeneratedSummary {
  const name = profile.world_cup_team;
  const shots = profile.statsbomb_shots;
  const hasHistoricalSample = shots > 0;
  const clubSources = teamClubSources(team);
  const hasClubContext = clubSources.length > 0;
  const dateRange = formatDateRange(profile.statsbomb_date_range);

  if (shots >= 100) {
    return {
      title: `${name} has a useful historical shot sample.`,
      paragraphs: [
        `${name}'s available historical sample includes ${formatNumber(shots)} past sample shots, ${formatNumber(profile.total_xg, 1)} model xG, and ${formatNumber(profile.statsbomb_goals)} goals in the StatsBomb open-data matches covered.`,
        `${finishingSentence(profile.goals_minus_xg)} ${shotDangerSentence(profile.avg_xg_per_shot)} Match dates in this sample: ${dateRange}.`
      ],
      takeaway:
        "Takeaway: this profile is useful for understanding past chance creation in available data, but it should not be read as a 2026 scoring forecast.",
      tone: "default"
    };
  }

  if (shots >= 50) {
    return {
      title: `${name} has some historical shot evidence.`,
      paragraphs: [
        `The available sample includes ${formatNumber(shots)} past sample shots, ${formatNumber(profile.total_xg, 1)} model xG, and ${formatNumber(profile.statsbomb_goals)} goals in covered matches.`,
        `${finishingSentence(profile.goals_minus_xg)} ${shotDangerSentence(profile.avg_xg_per_shot)} Use the club-context sources to round out the scouting picture.`
      ],
      takeaway:
        "Takeaway: the historical xG layer gives useful context, but the evidence is still a past sample rather than a 2026 tournament projection.",
      tone: "default"
    };
  }

  if (hasHistoricalSample) {
    return {
      title: `${name} has a small historical shot sample.`,
      paragraphs: [
        `This team has ${formatNumber(shots)} past sample shots in the current StatsBomb open-data archive, so model totals can move around more than they would with a larger sample.`,
        hasClubContext
          ? `Club context from ${clubSources.join(" and ")} can help provide extra scouting context, but it is separate from the trained StatsBomb xG model.`
          : "There is limited matched club context in this build, so the page is mainly a data-availability view."
      ],
      takeaway:
        "Takeaway: treat this as directional evidence and source transparency, not as a firm judgment of team strength.",
      tone: "warning"
    };
  }

  if (hasClubContext) {
    return {
      title: `${name} is a club-context-only profile right now.`,
      paragraphs: [
        `We do not have a historical StatsBomb shot sample for ${name} in the current dashboard artifacts.`,
        `That does not mean the team is weak. It means this profile relies more on squad information and club-context matches from ${clubSources.join(" and ")} where available.`
      ],
      takeaway:
        "Takeaway: focus on source coverage and squad context here instead of historical model totals.",
      tone: "warning"
    };
  }

  return {
    title: `${name} has no matched data yet.`,
    paragraphs: [
      `This team is included in the 2026 squad layer, but the current dashboard build does not expose a matched StatsBomb, FBref, or Understat team profile.`,
      "Missing data is a coverage limitation, not a statement about team quality."
    ],
    takeaway:
      "Takeaway: use the coverage page to understand which sources are currently missing for this team.",
    tone: "quiet"
  };
}

export function buildPlayerSummary(player: PlayerProfile): GeneratedSummary {
  const hasHistoricalSample = player.statsbomb_shots > 0;
  const hasExternal = playerHasExternalContext(player);
  const sources = playerClubSources(player);

  if (player.statsbomb_shots >= 20) {
    return {
      title: `${player.player} has a usable historical shot sample.`,
      paragraphs: [
        `The available StatsBomb sample includes ${formatNumber(player.statsbomb_shots)} past sample shots, ${formatNumber(player.total_xg, 2)} model xG, and ${formatNumber(player.statsbomb_goals)} goals.`,
        `${finishingSentence(player.goals_minus_xg)} ${shotDangerSentence(player.avg_xg_per_shot)} ${
          sources.length
            ? `Recent club-context sources are also available from ${sources.join(", ")}.`
            : "No recent external club-context layer is matched yet."
        }`
      ],
      takeaway:
        "Takeaway: use this as a combined historical plus club-context profile, not as a guaranteed 2026 World Cup projection.",
      tone: "default"
    };
  }

  if (hasHistoricalSample) {
    return {
      title: `${player.player} has limited historical shot evidence.`,
      paragraphs: [
        `This player has ${formatNumber(player.statsbomb_shots)} past sample shots in the current StatsBomb layer, so the historical model output should be read carefully.`,
        hasExternal
          ? `The profile is more useful when combined with recent club context from ${sources.join(", ")} where available.`
          : "There is not much matched external context yet, so avoid drawing a firm scouting conclusion from this page alone."
      ],
      takeaway:
        "Takeaway: this player page is more useful for scouting context than model-based conclusions.",
      tone: "warning"
    };
  }

  if (hasExternal) {
    return {
      title: `${player.player} has club context but no historical xG sample here.`,
      paragraphs: [
        "There are no matched StatsBomb shot samples for this player in the current dashboard build.",
        `Available external layers from ${sources.join(", ")} can still help describe recent club form or percentile context, but they are not inputs to the trained StatsBomb xG model.`
      ],
      takeaway:
        "Takeaway: read this as a club-context scouting page, not as a historical model profile.",
      tone: "warning"
    };
  }

  return {
    title: `${player.player} has no matched data yet.`,
    paragraphs: [
      "This player exists in the World Cup squad layer, but we do not currently have a matched StatsBomb, FBref, Understat, or percentile profile.",
      "That does not mean the player is weak. It only means the current sources do not expose a strong profile in this dashboard."
    ],
    takeaway:
      "Takeaway: check the team coverage page or revisit after more source matching is added.",
    tone: "quiet"
  };
}

function finishingSentence(goalsMinusXg: number | null | undefined) {
  const value = Number(goalsMinusXg ?? 0);

  if (value > 2) {
    return `They scored ${formatNumber(value, 1)} more goals than model xG in the covered matches.`;
  }

  if (value < -2) {
    return `They scored ${formatNumber(Math.abs(value), 1)} fewer goals than model xG in the covered matches.`;
  }

  return "Scoring was roughly in line with model xG in the covered matches.";
}

function shotDangerSentence(avgXgPerShot: number | null | undefined) {
  if (!avgXgPerShot || Number.isNaN(Number(avgXgPerShot))) {
    return "Shot danger is not available for this sample.";
  }

  return `Shot danger is ${formatNumber(avgXgPerShot, 3)} xG per shot, which describes average chance quality in the covered matches.`;
}

function teamClubSources(team: Team | null) {
  const sources: string[] = [];
  if ((team?.fbref_players_matched ?? 0) > 0) {
    sources.push("FBref");
  }
  if ((team?.understat_players_matched ?? 0) > 0) {
    sources.push("Understat");
  }
  return sources;
}

function playerClubSources(player: PlayerProfile) {
  const sources: string[] = [];
  if (player.datamb_25_26?.available) {
    sources.push("Percentile profile");
  }
  if (player.fbref_available) {
    sources.push("FBref");
  }
  if (player.understat_available) {
    sources.push("Understat");
  }
  if (player.understat_model_available) {
    sources.push("experimental shot model");
  }
  return sources;
}
