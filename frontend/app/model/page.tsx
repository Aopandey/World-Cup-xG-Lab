import DataStateCallout from "@/components/DataStateCallout";
import ErrorState from "@/components/ErrorState";
import BuildPipelineDiagram from "@/components/BuildPipelineDiagram";
import PageHeader from "@/components/PageHeader";
import SourceBadge from "@/components/SourceBadge";
import SourceLegend from "@/components/SourceLegend";
import StatCard from "@/components/StatCard";
import XGExplainerCards from "@/components/XGExplainerCards";
import { getModelSummary } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import type { ModelMetric } from "@/lib/types";

export default async function ModelPage() {
  try {
    const modelSummary = await getModelSummary();
    const productionModels = modelSummary.production_models ?? modelSummary.models;
    const researchModels = modelSummary.research_source_models ?? [];
    const featureExperiments = modelSummary.feature_missingness_experiments ?? [];
    const bestProductionModel =
      productionModels.find((model) => (model.model_label ?? model.model_name) === modelSummary.best_model_by_log_loss) ??
      productionModels.find((model) => model.model_name === modelSummary.best_model_by_log_loss) ??
      productionModels[0];

    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Model performance"
          title="Expected Goals Model"
          subtitle="A practical view of how the historical StatsBomb shot model scores chance quality, with source context kept separate."
          contentClassName="max-w-6xl"
          subtitleClassName="max-w-none xl:whitespace-nowrap"
        />

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.85fr)]">
          <div className="surface-card p-5">
            <div className="flex items-center gap-2">
              <SourceBadge source="statsbomb" />
              <h2 className="text-xl font-semibold text-white">What xG Means Here</h2>
            </div>
            <p className="mt-3 text-sm leading-7 text-slate-300">
              Expected goals estimates the chance that a shot becomes a goal based on the shot context. A 0.10 xG shot
              means similar shots are scored about 10% of the time.
            </p>
            <p className="mt-3 text-sm leading-7 text-slate-300">
              The model describes shot quality in available historical data. It does not claim a player will score from a
              future location.
            </p>
          </div>
          <div className="surface-hero p-5">
            <p className="stat-label">Production model</p>
            <p className="mt-3 text-3xl font-semibold text-grass-400">
              {modelSummary.best_model_by_log_loss ?? "N/A"}
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              XGBoost was selected as the production StatsBomb xG model because it performed best on log loss among the
              production candidates.
            </p>
          </div>
        </section>

        <section className="surface-card p-5">
          <h2 className="text-xl font-semibold text-white">Why this matters for the World Cup dashboard</h2>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            World Cup squads mix players from many leagues, competitions, and data sources. Training an xG model gives the
            dashboard one consistent way to translate historical shot locations and shot context into chance quality. For
            fans, that means the site can compare whether a player or team generated high-quality chances in available
            data, then clearly separate that model output from recent club context like FBref, Understat, and percentile
            profiles.
          </p>
        </section>

        <XGExplainerCards />

        {bestProductionModel ? (
          <section className="surface-card p-5">
            <h2 className="text-xl font-semibold text-white">Production model summary</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              These are the headline validation metrics for the model used by the dashboard's historical xG layer.
            </p>
            <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <StatCard label="Log loss" value={formatNumber(bestProductionModel.log_loss, 3)} detail="Rewards calibrated probabilities" accent="statsbomb" />
              <StatCard label="Brier score" value={formatNumber(bestProductionModel.brier_score, 3)} detail="Measures probability error" accent="statsbomb" />
              <StatCard label="ROC-AUC" value={formatNumber(bestProductionModel.roc_auc, 3)} detail="Ranks goals above non-goals" accent="statsbomb" />
              <StatCard label="Accuracy" value={formatNumber(bestProductionModel.accuracy_at_0_5, 3)} detail="Secondary for xG" accent="statsbomb" />
            </div>
          </section>
        ) : null}

        <MetricTable
          title="Production Model Comparison"
          subtitle="These are the dashboard's original StatsBomb model candidates. The XGBoost model remains the production xG layer."
          rows={productionModels}
          bestModelName={modelSummary.best_model_by_log_loss}
        />

        <MetricTable
          title="Research: Source Model Comparison"
          subtitle={modelSummary.research_explanation ?? "Experimental comparisons across StatsBomb-only, Understat-only, and combined-source models."}
          rows={researchModels}
          bestModelName={modelSummary.best_research_model_by_log_loss}
          research
        />

        <MetricTable
          title="Research: Feature Availability Experiment"
          subtitle="This tests your friend's idea directly: richer features versus reduced or missing event context. Accuracy barely moves, so calibration metrics matter more."
          rows={featureExperiments}
          missingness
        />

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Log loss" value="Lower" detail="Sensitive to confident wrong probabilities." accent="statsbomb" />
          <StatCard label="Brier score" value="Lower" detail="Average squared probability error." accent="statsbomb" />
          <StatCard label="ROC-AUC" value="Higher" detail="Ranks goals above non-goals across thresholds." accent="statsbomb" />
          <StatCard label="Accuracy" value="Secondary" detail="Can be misleading because most shots are not goals." accent="statsbomb" />
        </section>

        <section className="surface-card p-5">
          <h2 className="text-xl font-semibold text-white">Features Used</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {[
              "Shot location",
              "Distance to goal",
              "Angle to goal",
              "Body part",
              "Shot type",
              "Under pressure",
              "Play pattern",
              "Minute and period"
            ].map((feature) => (
              <div key={feature} className="surface-inset p-3 text-sm font-medium text-slate-200">
                {feature}
              </div>
            ))}
          </div>
        </section>

        <BuildPipelineDiagram />

        <SourceLegend />

        <DataStateCallout title="Known model limits" tone="neutral">
          <details>
            <summary className="cursor-pointer text-white">Show limitations</summary>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
              {modelSummary.limitations.map((limitation) => (
                <li key={limitation}>- {limitation}</li>
              ))}
              <li>- This dashboard is not a guaranteed 2026 World Cup prediction model.</li>
            </ul>
          </details>
        </DataStateCallout>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        title="Could not load model summary"
        message={error instanceof Error ? error.message : "Start the FastAPI backend and try again."}
      />
    );
  }
}

function MetricTable({
  title,
  subtitle,
  rows,
  bestModelName,
  research = false,
  missingness = false
}: {
  title: string;
  subtitle: string;
  rows: ModelMetric[];
  bestModelName?: string | null;
  research?: boolean;
  missingness?: boolean;
}) {
  return (
    <section className="surface-card p-5">
      <h2 className="text-xl font-semibold text-white">{title}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{subtitle}</p>
      {rows.length ? (
        <div className="mt-4 overflow-x-auto rounded-lg border border-white/10 bg-pitch-900/55">
          <table className="w-full min-w-[880px] text-left text-sm">
            <thead className="bg-white/[0.035] text-[0.68rem] uppercase tracking-[0.14em] text-slate-400">
              <tr>
                <th className="px-3 py-3">Model</th>
                {research ? <th className="px-3 py-3">Test Source</th> : null}
                {missingness ? <th className="px-3 py-3">Missing Ref Features</th> : null}
                <th className="px-3 py-3">Log loss</th>
                <th className="px-3 py-3">Brier</th>
                <th className="px-3 py-3">ROC-AUC</th>
                <th className="px-3 py-3">Accuracy</th>
                <th className="px-3 py-3">Rows</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10 text-slate-200">
              {rows.map((model, index) => {
                const label = model.model_label ?? model.model_name;
                const best = label === bestModelName || model.model_name === bestModelName;
                return (
                  <tr key={`${label}-${model.test_source ?? model.dataset_name ?? index}`} className={best ? "bg-grass-400/[0.06]" : undefined}>
                    <td className="px-3 py-3 font-semibold text-white">
                      {label}
                      {best ? <span className="ml-2 text-xs text-grass-400">Best</span> : null}
                      {model.training_source ? <p className="mt-1 text-xs font-normal text-slate-500">{model.training_source}</p> : null}
                    </td>
                    {research ? <td className="px-3 py-3">{model.test_source ?? "N/A"}</td> : null}
                    {missingness ? (
                      <td className="px-3 py-3">
                        {typeof model.reference_features_missing_pct === "number"
                          ? `${formatNumber(model.reference_features_missing_pct * 100, 0)}%`
                          : "N/A"}
                      </td>
                    ) : null}
                    <td className="px-3 py-3">{formatNumber(model.log_loss, 3)}</td>
                    <td className="px-3 py-3">{formatNumber(model.brier_score, 3)}</td>
                    <td className="px-3 py-3">{formatNumber(model.roc_auc, 3)}</td>
                    <td className="px-3 py-3">{formatNumber(model.accuracy_at_0_5, 3)}</td>
                    <td className="px-3 py-3">{formatNumber(model.rows ?? model.test_rows)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-400">No metrics are available for this section yet.</p>
      )}
    </section>
  );
}
