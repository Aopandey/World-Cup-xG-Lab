"use client";

type FanAdvancedToggleProps = {
  value: "fan" | "advanced";
  onChange: (value: "fan" | "advanced") => void;
};

export default function FanAdvancedToggle({ value, onChange }: FanAdvancedToggleProps) {
  return (
    <div className="inline-flex rounded-lg border border-white/10 bg-white/[0.035] p-1">
      {[
        ["fan", "Fan mode"],
        ["advanced", "Advanced mode"]
      ].map(([mode, label]) => {
        const selected = value === mode;
        return (
          <button
            key={mode}
            type="button"
            onClick={() => onChange(mode as "fan" | "advanced")}
            className={`rounded-md px-3 py-2 text-sm transition ${
              selected ? "bg-grass-400/15 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
