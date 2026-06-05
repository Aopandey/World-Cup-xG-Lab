import { formatNumber, hasValue } from "@/lib/format";

export type CompactColumn<T extends object> = {
  key: keyof T;
  label: string;
  digits?: number;
  formatter?: (value: T[keyof T], row: T) => string;
  hideWhenEmpty?: boolean;
};

type CompactSeasonTableProps<T extends object> = {
  rows: T[];
  columns: CompactColumn<T>[];
  emptyMessage: string;
};

export default function CompactSeasonTable<T extends object>({
  rows,
  columns,
  emptyMessage
}: CompactSeasonTableProps<T>) {
  const visibleColumns = columns.filter((column) => {
    if (!column.hideWhenEmpty) {
      return true;
    }

    return rows.some((row) => hasValue(row[column.key]));
  });

  if (!rows.length) {
    return <div className="surface-inset p-4 text-sm text-slate-300">{emptyMessage}</div>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10 bg-pitch-900/55">
      <table className="w-full min-w-[680px] text-left text-sm">
        <thead className="bg-white/[0.035] text-[0.68rem] uppercase tracking-[0.14em] text-slate-400">
          <tr>
            {visibleColumns.map((column) => (
              <th key={String(column.key)} className="px-3 py-3 font-semibold">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10 text-slate-200">
          {rows.map((row, index) => (
            <tr key={index} className="transition hover:bg-white/[0.025]">
              {visibleColumns.map((column) => {
                const rawValue = row[column.key];
                const value = column.formatter
                  ? column.formatter(rawValue, row)
                  : typeof rawValue === "number"
                    ? formatNumber(rawValue, column.digits ?? 0)
                    : hasValue(rawValue)
                      ? String(rawValue)
                      : "N/A";

                return (
                  <td key={String(column.key)} className="px-3 py-3">
                    {value}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
