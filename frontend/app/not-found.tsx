import Link from "next/link";

import ErrorState from "@/components/ErrorState";

export default function NotFound() {
  return (
    <div className="space-y-4">
      <ErrorState title="Page not found" message="The requested dashboard page does not exist." />
      <Link
        href="/"
        className="inline-flex rounded-lg bg-grass-500 px-4 py-2 text-sm font-bold text-pitch-900 transition hover:bg-grass-400"
      >
        Back to teams
      </Link>
    </div>
  );
}
