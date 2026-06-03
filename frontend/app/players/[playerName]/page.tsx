import DataConfidenceBadge from "@/components/DataConfidenceBadge";
import ErrorState from "@/components/ErrorState";
import PageHeader from "@/components/PageHeader";
import PitchShotMap from "@/components/PitchShotMap";
import SampleWarning from "@/components/SampleWarning";
import StatCard from "@/components/StatCard";
import { getPlayerProfile } from "@/lib/api";
import { formatDateRange, formatNumber, initials } from "@/lib/format";

type PlayerPageProps = {
  params: {
    playerName: string;
  };
};

export default async function PlayerPage({ params }: PlayerPageProps) {
  const playerName = decodeURIComponent(params.playerName);

  try {
    const player = await getPlayerProfile(playerName);
    const weakStatsBombSample = player.statsbomb_shots < 20;

    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow={player.world_cup_team}
          title={player.player}
          subtitle="Player profile combining historical StatsBomb xG metrics with recent FBref and Understat club context where available."
        />

        <section className="rounded-lg border border-white/10 bg-white/[0.045] p-5 shadow-card">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-lg border border-white/10 bg-pitch-700 text-xl font-black text-white">
                {initials(player.player)}
              </div>
              <div>
                <h2 className="text-2xl font-black text-white">{player.player}</h2>
                <p className="mt-1 text-sm text-slate-400">
                  {player.position ?? "Position unknown"} - {player.club ?? "Club unknown"} - {player.league ?? "League unknown"}
                </p>
              </div>
            </div>
            <DataConfidenceBadge value={player.data_confidence} />
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <StatCard label="Shots" value={formatNumber(player.statsbomb_shots)} />
            <StatCard label="Goals" value={formatNumber(player.statsbomb_goals)} />
            <StatCard label="Total xG" value={formatNumber(player.total_xg, 2)} />
            <StatCard label="Goals minus xG" value={formatNumber(player.goals_minus_xg, 2)} />
            <StatCard label="Avg xG per Shot" value={formatNumber(player.avg_xg_per_shot, 3)} />
          </div>
          <p className="mt-4 text-sm text-slate-400">StatsBomb sample date range: {formatDateRange(player.statsbomb_date_range)}</p>
        </section>

        {weakStatsBombSample ? (
          <SampleWarning>
            This player is in the official World Cup squad, but the available historical StatsBomb data has too few shot events to create a reliable scoring-zone profile. FBref and Understat add club context where available.
          </SampleWarning>
        ) : null}

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <h2 className="text-2xl font-bold text-white">Recent Club/League Shooting Context from FBref</h2>
          <p className="mt-2 text-sm text-slate-400">
            FBref adds recent aggregate player context where available, especially when the historical shot sample is small.
          </p>

          {player.fbref_available && player.fbref_recent_rows.length ? (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="py-2 pr-4">Season</th>
                    <th className="py-2 pr-4">League</th>
                    <th className="py-2 pr-4">Team</th>
                    <th className="py-2 pr-4">Minutes</th>
                    <th className="py-2 pr-4">Goals</th>
                    <th className="py-2 pr-4">Assists</th>
                    <th className="py-2 pr-4">Shots</th>
                    <th className="py-2 pr-4">xG</th>
                    <th className="py-2">xG/90</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10 text-slate-200">
                  {player.fbref_recent_rows.map((row, index) => (
                    <tr key={`${row.season}-${row.team}-${index}`}>
                      <td className="py-3 pr-4">{row.season ?? "N/A"}</td>
                      <td className="py-3 pr-4">{row.league ?? "N/A"}</td>
                      <td className="py-3 pr-4">{row.team ?? "N/A"}</td>
                      <td className="py-3 pr-4">{formatNumber(row.minutes)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.goals)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.assists)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.shots)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.xg, 2)}</td>
                      <td className="py-3">{formatNumber(row.xg_per_90, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-300">
              FBref aggregate context is not available for this player with the currently supported/pulled leagues.
            </div>
          )}
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <h2 className="text-2xl font-bold text-white">Club xG Context from Understat</h2>
          <p className="mt-2 text-sm text-slate-400">
            Understat adds club-season xG, xA, key-pass, xGChain, and shot-volume context from major European leagues and RFPL. This is dashboard context only; it has not been used to retrain the xG model.
          </p>

          {player.understat_available && player.understat_recent_rows?.length ? (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[980px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="py-2 pr-4">Season</th>
                    <th className="py-2 pr-4">League</th>
                    <th className="py-2 pr-4">Club</th>
                    <th className="py-2 pr-4">Minutes</th>
                    <th className="py-2 pr-4">Goals</th>
                    <th className="py-2 pr-4">Assists</th>
                    <th className="py-2 pr-4">Shots</th>
                    <th className="py-2 pr-4">xG</th>
                    <th className="py-2 pr-4">npxG</th>
                    <th className="py-2 pr-4">xA</th>
                    <th className="py-2 pr-4">Key Passes</th>
                    <th className="py-2 pr-4">xGChain</th>
                    <th className="py-2">Avg Shot xG</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10 text-slate-200">
                  {player.understat_recent_rows.map((row, index) => (
                    <tr key={`${row.season}-${row.team}-${index}`}>
                      <td className="py-3 pr-4">{row.season ?? "N/A"}</td>
                      <td className="py-3 pr-4">{row.league ?? "N/A"}</td>
                      <td className="py-3 pr-4">{row.team ?? "N/A"}</td>
                      <td className="py-3 pr-4">{formatNumber(row.minutes)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.goals)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.assists)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.shots)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.xg, 2)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.npxg, 2)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.xa, 2)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.key_passes)}</td>
                      <td className="py-3 pr-4">{formatNumber(row.xg_chain, 2)}</td>
                      <td className="py-3">{formatNumber(row.avg_shot_xg, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-300">
              Understat club xG context is not available for this player in the current top-league/RFPL archive.
            </div>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-2xl font-bold text-white">Shot-Location Profile</h2>
          <p className="text-sm text-slate-400">
            Some players have limited or no historical shot-location data. The pitch component will render shot dots once shot-level coordinates are exposed in the API artifacts.
          </p>
          <PitchShotMap emptyMessage="No reliable shot-location data available for this player." />
        </section>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        title="Player not found"
        message={error instanceof Error ? error.message : "No player profile was found for this route."}
      />
    );
  }
}
