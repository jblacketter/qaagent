import type { FC } from "react";

interface CoverageBarProps {
  value: number; // 0 - 1
  target?: number; // optional target 0 - 1
}

const getColor = (value: number): string => {
  if (value >= 0.8) return "bg-green-500";
  if (value >= 0.6) return "bg-yellow-500";
  if (value >= 0.4) return "bg-orange-500";
  return "bg-red-500";
};

export const CoverageBar: FC<CoverageBarProps> = ({ value, target }) => {
  const safeValue = Math.max(0, Math.min(1, value));
  const width = `${Math.round(safeValue * 100)}%`;
  const barColor = getColor(safeValue);

  return (
    <div className="relative h-3 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
      <div className={`h-full transition-all ${barColor}`} style={{ width }} />
      {typeof target === "number" && (
        <div
          className="absolute inset-y-0 w-0.5 bg-slate-900/50 dark:bg-slate-100/50"
          style={{ left: `${Math.max(0, Math.min(100, target * 100))}%` }}
        />
      )}
    </div>
  );
};
