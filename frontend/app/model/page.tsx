import ErrorState from "@/components/ErrorState";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import { getModelSummary } from "@/lib/api";
import { formatNumber } from "@/lib/format";

export default async function ModelPage() {
  try {
    const modelSummary = await getModelSummary();

    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Model performance"
          title="Expected Goals Model"
          subtitle="A practical overview of how the World Cup xG Lab model scores shot quality from available historical shot data."
        />

        <section className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5 lg:col-span-2">
            <h2 className="text-2xl font-bold text-white">What is xG?</h2>
            <p className="mt-3 text-sm leading-7 text-slate-300">{modelSummary.xg_explanation}</p>
            <p className="mt-3 text-sm leading-7 text-slate-300">
              StatsBomb powers the historical xG model and shot-location views. The model estimates how likely a shot was to become a goal based on features available in the shot event data.
            </p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
            <h2 className="text-xl font-bold text-white">Best Model</h2>
            <p className="mt-3 text-3xl font-black text-grass-400">{modelSummary.best_model_by_log_loss ?? "N/A"}</p>
            <p className="mt-2 text-sm text-slate-400">Selected by lowest log loss when metrics are available.</p>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-white">Features Used</h2>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
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
              <div key={feature} className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm font-semibold text-slate-200">
                {feature}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <h2 className="text-2xl font-bold text-white">Baseline vs XGBoost</h2>
          {modelSummary.models.length ? (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="py-2 pr-4">Model</th>
                    <th className="py-2 pr-4">Log loss</th>
                    <th className="py-2 pr-4">Brier score</th>
                    <th className="py-2 pr-4">ROC-AUC</th>
                    <th className="py-2">Accuracy at 0.5</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10 text-slate-200">
                  {modelSummary.models.map((model) => (
                    <tr key={model.model_name}>
                      <td className="py-3 pr-4 font-semibold text-white">{model.model_name}</td>
                      <td className="py-3 pr-4">{formatNumber(model.log_loss, 3)}</td>
                      <td className="py-3 pr-4">{formatNumber(model.brier_score, 3)}</td>
                      <td className="py-3 pr-4">{formatNumber(model.roc_auc, 3)}</td>
                      <td className="py-3">{formatNumber(model.accuracy_at_0_5, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-400">No model comparison metrics are available yet.</p>
          )}
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <StatCard label="Log loss" value="Lower is better" detail="Rewards well-calibrated probabilities and punishes confident wrong predictions." />
          <StatCard label="Brier score" value="Lower is better" detail="Measures average squared error between predicted probability and outcome." />
          <StatCard label="ROC-AUC" value="Higher is better" detail="Measures ranking quality across decision thresholds." />
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <h2 className="text-2xl font-bold text-white">Limitations</h2>
          <ul className="mt-4 space-y-2 text-sm leading-6 text-slate-300">
            {modelSummary.limitations.map((limitation) => (
              <li key={limitation}>- {limitation}</li>
            ))}
            <li>- This dashboard is not a guaranteed 2026 World Cup prediction model.</li>
          </ul>
        </section>
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
