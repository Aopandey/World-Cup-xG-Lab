type ErrorStateProps = {
  title?: string;
  message: string;
};

export default function ErrorState({ title = "Something went wrong", message }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-rose-400/35 bg-rose-400/10 p-6 text-rose-100">
      <h2 className="text-lg font-bold">{title}</h2>
      <p className="mt-2 text-sm leading-6">{message}</p>
    </div>
  );
}
