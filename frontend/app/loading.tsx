export default function Loading() {
  return (
    <div className="space-y-5" aria-label="Loading dashboard data">
      <div className="surface-hero p-5">
        <div className="h-4 w-36 animate-pulse rounded bg-grass-400/30" />
        <div className="mt-4 h-10 w-72 max-w-full animate-pulse rounded-lg bg-white/[0.08]" />
        <div className="mt-4 h-5 w-full max-w-2xl animate-pulse rounded bg-white/[0.06]" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-44 animate-pulse rounded-lg border border-white/10 bg-white/[0.045]" />
        ))}
      </div>
    </div>
  );
}
