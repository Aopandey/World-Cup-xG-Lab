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
        `In the matches covered by this dashboard, ${name} took ${formatNumber(shots)} shots. xG estimates how many goals a team would usually score from the chances they created. The model estimated those chances were worth about ${formatNumber(profile.total_xg, 1)} goals, and ${name} actually scored ${formatNumber(profile.statsbomb_goals)}.`,
        `${finishingSentence(profile.goals_minus_xg)} ${chanceQualitySentence(profile.avg_xg_per_shot)} Match dates in this sample: ${dateRange}.`
      ],
      takeaway:
        `Takeaway: this profile is useful for understanding ${name}'s past chance creation and finishing in the available data. It does not predict how many goals they will score in 2026.`,
      tone: "default"
    };
  }

  if (shots >= 50) {
    return {
      title: `${name} has some historical shot evidence.`,
      paragraphs: [
        `In the matches covered by this dashboard, ${name} took ${formatNumber(shots)} shots. xG estimates how many goals those chances were usually worth. The model estimated about ${formatNumber(profile.total_xg, 1)} goals from those shots, and ${name} actually scored ${formatNumber(profile.statsbomb_goals)}.`,
        `${finishingSentence(profile.goals_minus_xg)} ${chanceQualitySentence(profile.avg_xg_per_shot)} Use the club and league context to round out the scouting picture.`
      ],
      takeaway:
        "Takeaway: the past chance-quality layer gives useful context, but it is still a historical sample rather than a 2026 tournament projection.",
      tone: "default"
    };
  }

  if (hasHistoricalSample) {
    return {
      title: `${name} has a small historical shot sample.`,
      paragraphs: [
        `This team has only ${formatNumber(shots)} shots in the current historical open-data sample. That means the expected-goals numbers are less reliable and can move around more than they would with a larger sample.`,
        hasClubContext
          ? `Club and league context from ${clubSources.join(" and ")} can still help describe the squad, but it is separate from the trained xG model.`
          : "There is limited matched club context in this build, so the page is mainly a data-availability view."
      ],
      takeaway:
        "Takeaway: use this page more as a data-availability and scouting-context profile than as a firm judgment of team strength.",
      tone: "warning"
    };
  }

  if (hasClubContext) {
    return {
      title: `${name} is a club-context-only profile right now.`,
      paragraphs: [
        `We do not have a historical StatsBomb shot sample for ${name} yet. That does not mean the team is weak; it only means this dashboard cannot show a strong historical expected-goals profile for them.`,
        `For now, this profile relies more on squad information plus club and league context from ${clubSources.join(" and ")} where available.`
      ],
      takeaway:
        "Takeaway: focus on available club, league, and squad context instead of historical model totals.",
      tone: "warning"
    };
  }

  return {
    title: `${name} has no matched data yet.`,
    paragraphs: [
      `This team is included in the 2026 squad layer, but the current dashboard build does not expose a matched past shot sample, recent league-form profile, or club xG profile.`,
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
        `In the available historical sample, ${player.player} took ${formatNumber(player.statsbomb_shots)} shots. xG estimates how many goals those chances were usually worth. The model estimated those shots were worth about ${formatNumber(player.total_xg, 2)} goals, and ${player.player} scored ${formatNumber(player.statsbomb_goals)}.`,
        `${playerFinishingSentence(player.goals_minus_xg)} ${chanceQualitySentence(player.avg_xg_per_shot)} ${
          sources.length
            ? `Recent club and scouting context is also available from ${sources.join(", ")}.`
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
        `This player has only ${formatNumber(player.statsbomb_shots)} historical shots in the dashboard, so the expected-goals model has limited evidence.`,
        hasExternal
          ? `Recent club, league, and scouting context from ${sources.join(", ")} can still help describe their current role and shooting volume where available.`
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
        "There are no matched historical open-data shot samples for this player in the current dashboard build.",
        `Available external layers from ${sources.join(", ")} can still help describe recent club form, league role, or scouting percentiles, but they are not inputs to the trained xG model.`
      ],
      takeaway:
        "Takeaway: read this as a club-context scouting page, not as a historical model profile.",
      tone: "warning"
    };
  }

  return {
    title: `${player.player} has no matched data yet.`,
    paragraphs: [
      "This player exists in the World Cup squad layer, but we do not currently have a matched past shot sample, recent league-form profile, club xG profile, or percentile scouting profile.",
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
    return `They scored about ${formatNumber(value, 1)} more goals than expected from the chances in this sample.`;
  }

  if (value < -2) {
    return `They scored about ${formatNumber(Math.abs(value), 1)} fewer goals than expected from the chances in this sample.`;
  }

  return "They scored roughly in line with what the model expected from the chances in this sample.";
}

function playerFinishingSentence(goalsMinusXg: number | null | undefined) {
  const value = Number(goalsMinusXg ?? 0);

  if (value > 2) {
    return `He scored about ${formatNumber(value, 1)} more goals than expected from the chances in this sample.`;
  }

  if (value < -2) {
    return `He scored about ${formatNumber(Math.abs(value), 1)} fewer goals than expected from the chances in this sample.`;
  }

  return "He scored roughly in line with what the model expected from the chances in this sample.";
}

function chanceQualitySentence(avgXgPerShot: number | null | undefined) {
  if (!avgXgPerShot || Number.isNaN(Number(avgXgPerShot))) {
    return "Average shot quality is not available for this sample.";
  }

  return `The average shot was worth about ${formatNumber(avgXgPerShot, 3)} xG, or roughly a ${formatNumber(Number(avgXgPerShot) * 100, 0)}% chance of becoming a goal.`;
}

function teamClubSources(team: Team | null) {
  const sources: string[] = [];
  if ((team?.fbref_players_matched ?? 0) > 0) {
    sources.push("recent league form (FBref)");
  }
  if ((team?.understat_players_matched ?? 0) > 0) {
    sources.push("club xG context (Understat)");
  }
  return sources;
}

function playerClubSources(player: PlayerProfile) {
  const sources: string[] = [];
  if (player.datamb_25_26?.available) {
    sources.push("percentile scouting profile (DataMB)");
  }
  if (player.fbref_available) {
    sources.push("recent league form (FBref)");
  }
  if (player.understat_available) {
    sources.push("club xG context (Understat)");
  }
  if (player.understat_model_available) {
    sources.push("experimental xG check");
  }
  return sources;
}
