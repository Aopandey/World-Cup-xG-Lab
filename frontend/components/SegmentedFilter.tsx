"use client";

type SegmentedOption = {
  label: string;
  value: string;
  count?: number;
};

type SegmentedFilterProps = {
  label: string;
  options: SegmentedOption[];
  value: string;
  onChange: (value: string) => void;
};

export default function SegmentedFilter({ label, options, value, onChange }: SegmentedFilterProps) {
  return (
    <div className="space-y-2">
      <p className="stat-label">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const selected = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              className={`rounded-md border px-3 py-2 text-sm transition ${
                selected
                  ? "border-grass-400/70 bg-grass-400/15 text-white"
                  : "border-white/10 bg-white/[0.035] text-slate-300 hover:border-white/25 hover:bg-white/[0.065]"
              }`}
            >
              <span className="font-medium">{option.label}</span>
              {typeof option.count === "number" ? (
                <span className="ml-2 text-xs text-slate-400">{option.count}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}

