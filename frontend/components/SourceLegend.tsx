import SourceBadge from "@/components/SourceBadge";

export default function SourceLegend() {
  return (
    <div className="surface-inset p-4">
      <p className="stat-label">Source Boundaries</p>
      <div className="mt-3 grid gap-3 text-sm text-slate-300 lg:grid-cols-3">
        <div className="space-y-2">
          <SourceBadge source="statsbomb" />
          <p>Historical model and shot-location layer from available open event data.</p>
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
