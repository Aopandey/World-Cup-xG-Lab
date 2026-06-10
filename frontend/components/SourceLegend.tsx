import SourceBadge from "@/components/SourceBadge";

type SourceLegendProps = {
  compact?: boolean;
};

export default function SourceLegend({ compact = false }: SourceLegendProps) {
  return (
    <div className={compact ? "" : "surface-inset p-4"}>
      <p className="stat-label">How to read this dashboard</p>
      <div className="mt-3 grid gap-3 text-sm text-slate-300 lg:grid-cols-4">
        <div className="space-y-2">
          <SourceBadge source="statsbomb" />
          <p>Past shot samples used by the expected-goals model. Not a 2026 prediction.</p>
        </div>
        <div className="space-y-2">
          <SourceBadge source="datamb" />
          <p>25/26 percentile scouting profiles. Percentiles are not raw stats and are not model inputs.</p>
        </div>
        <div className="space-y-2">
          <SourceBadge source="fbref" />
          <p>Recent club and league form context. Not used by the trained expected-goals model.</p>
        </div>
        <div className="space-y-2">
          <SourceBadge source="understat" />
          <p>Club expected-goals context from covered leagues, plus a separate experimental xG check where clearly labeled.</p>
        </div>
      </div>
    </div>
  );
}
