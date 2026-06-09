const steps = [
  {
    title: "StatsBomb Open Data",
    detail: "Historical shot events"
  },
  {
    title: "Pandas cleaning + feature engineering",
    detail: "Shot coordinates, distance, angle, context"
  },
  {
    title: "scikit-learn / XGBoost model training",
    detail: "Chance-quality probability model"
  },
  {
    title: "MLflow experiment tracking",
    detail: "Metrics, model runs, artifacts"
  },
  {
    title: "Dashboard JSON artifacts",
    detail: "Precomputed team and player profiles"
  },
  {
    title: "FastAPI backend",
    detail: "Clean API layer for the frontend"
  },
  {
    title: "Docker deployment",
    detail: "Portable app runtime"
  },
  {
    title: "AWS S3 / EC2",
    detail: "Portfolio deployment target"
  },
  {
    title: "Next.js + Tailwind frontend",
    detail: "Fan-friendly scouting dashboard"
  }
];

export default function BuildPipelineDiagram() {
  const rows = [steps.slice(0, 3), steps.slice(3, 6), steps.slice(6, 9)];

  return (
    <div className="surface-card p-5">
      <h2 className="text-xl font-semibold text-white">How this was built</h2>
      <p className="mt-2 text-sm leading-6 text-slate-400">
        Streamlit was used as an early prototype for model exploration and validation. The production portfolio path is
        a precomputed artifact pipeline served through FastAPI and rendered in Next.js.
      </p>
      <div className="mt-6 lg:hidden">
        {steps.map((step, index) => (
          <div key={step.title}>
            <PipelineStep step={step} index={index} />
            {index < steps.length - 1 ? <div className="py-2 text-center text-sm font-semibold text-grass-400">v</div> : null}
          </div>
        ))}
      </div>

      <div className="mt-6 hidden space-y-3 lg:block">
        {rows.map((row, rowIndex) => (
          <div key={`row-${rowIndex}`}>
            <div className="grid items-stretch gap-3 lg:grid-cols-[minmax(0,1fr)_2rem_minmax(0,1fr)_2rem_minmax(0,1fr)]">
              {row.map((step, index) => {
                const absoluteIndex = rowIndex * 3 + index;
                return (
                  <div key={step.title} className="contents">
                    <PipelineStep step={step} index={absoluteIndex} />
                    {index < row.length - 1 ? (
                      <div className="flex items-center justify-center text-lg font-semibold text-grass-400">-&gt;</div>
                    ) : null}
                  </div>
                );
              })}
            </div>
            {rowIndex < rows.length - 1 ? (
              <div className="py-2 text-center text-lg font-semibold text-grass-400">v</div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function PipelineStep({
  step,
  index
}: {
  step: {
    title: string;
    detail: string;
  };
  index: number;
}) {
  return (
    <div className="relative rounded-lg border border-white/10 bg-white/[0.04] p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-grass-400">Step {index + 1}</p>
      <p className="mt-2 text-sm font-semibold text-white">{step.title}</p>
      <p className="mt-2 text-xs leading-5 text-slate-400">{step.detail}</p>
    </div>
  );
}
