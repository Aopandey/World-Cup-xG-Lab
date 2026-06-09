const examples = [
  {
    title: "Long shot",
    chance: "Low chance",
    xg: "0.03 xG",
    detail: "A hopeful shot from distance. Similar chances are rarely scored."
  },
  {
    title: "Box shot",
    chance: "Medium chance",
    xg: "0.12 xG",
    detail: "A shot inside the box with some angle or defensive pressure."
  },
  {
    title: "Big chance",
    chance: "High chance",
    xg: "0.35 xG",
    detail: "A close-range chance where similar shots are scored much more often."
  }
];

export default function XGExplainerCards() {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {examples.map((example) => (
        <div key={example.title} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
          <p className="stat-label">{example.title}</p>
          <p className="mt-2 text-xl font-semibold text-white">{example.chance}</p>
          <p className="mt-1 text-sm font-semibold text-grass-400">{example.xg}</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">{example.detail}</p>
        </div>
      ))}
    </div>
  );
}
