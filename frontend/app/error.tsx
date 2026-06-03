"use client";

import ErrorState from "@/components/ErrorState";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="space-y-4">
      <ErrorState message={error.message} />
      <button
        onClick={reset}
        className="rounded-lg bg-grass-500 px-4 py-2 text-sm font-bold text-pitch-900 transition hover:bg-grass-400"
      >
        Try again
      </button>
    </div>
  );
}
