type ErrorStateProps = {
  title?: string;
  message: string;
};

export default function ErrorState({ title = "Something went wrong", message }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-amber-400/30 bg-amber-400/10 p-6 shadow-card">
      <p className="stat-label text-amber-200">Dashboard data unavailable</p>
      <h2 className="mt-2 text-lg font-semibold text-white">{title}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-amber-50/85">{message}</p>
    </div>
  );
}
