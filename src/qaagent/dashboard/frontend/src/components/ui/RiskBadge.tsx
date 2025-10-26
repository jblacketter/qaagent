import type { FC } from "react";

const variants: Record<"P0" | "P1" | "P2" | "P3", string> = {
  P0: "bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-200 dark:border-red-700",
  P1: "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-900/30 dark:text-orange-200 dark:border-orange-700",
  P2: "bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-200 dark:border-yellow-700",
  P3: "bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-200 dark:border-green-700",
};

const emoji: Record<"P0" | "P1" | "P2" | "P3", string> = {
  P0: "🔴",
  P1: "🟠",
  P2: "🟡",
  P3: "🟢",
};

interface RiskBadgeProps {
  band: "P0" | "P1" | "P2" | "P3";
}

export const RiskBadge: FC<RiskBadgeProps> = ({ band }) => {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${variants[band]}`}
    >
      <span>{emoji[band]}</span>
      <span>{band}</span>
    </span>
  );
};
