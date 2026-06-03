export default function Loading() {
  return (
    <div className="space-y-4">
      <div className="h-10 w-72 animate-pulse rounded-lg bg-white/[0.08]" />
      <div className="h-28 animate-pulse rounded-lg bg-white/[0.05]" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-44 animate-pulse rounded-lg bg-white/[0.05]" />
        ))}
      </div>
    </div>
  );
}
