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
          <p>Historical model and shot-location layer from available open event data.</p>
        </div>
        <div className="space-y-2">
          <SourceBadge source="datamb" />
          <p>25/26 player percentile context. It is not used by the trained xG model.</p>
        </div>
        <div className="space-y-2">
          <SourceBadge source="fbref" />
          <p>Recent aggregate player context. It is not used by the trained xG model.</p>
        </div>
        <div className="space-y-2">
          <SourceBadge source="understat" />
          <p>Club xG context from covered leagues, plus an experimental shot-model layer where clearly labeled.</p>
        </div>
      </div>
    </div>
  );
}
