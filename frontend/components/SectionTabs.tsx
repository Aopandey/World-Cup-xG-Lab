"use client";

type TabOption = {
  label: string;
  value: string;
};

type SectionTabsProps = {
  options: TabOption[];
  value: string;
  onChange: (value: string) => void;
};

export default function SectionTabs({ options, value, onChange }: SectionTabsProps) {
  return (
    <div className="sticky top-0 z-20 -mx-5 border-y border-white/10 bg-pitch-900/92 px-5 py-3 backdrop-blur md:static md:mx-0 md:rounded-lg md:border md:bg-white/[0.035]">
      <div className="flex gap-2 overflow-x-auto">
        {options.map((option) => {
          const selected = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              className={`whitespace-nowrap rounded-md border px-3 py-2 text-sm transition ${
                selected
                  ? "border-grass-400/70 bg-grass-400/15 text-white"
                  : "border-transparent text-slate-300 hover:border-white/10 hover:bg-white/[0.055] hover:text-white"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

