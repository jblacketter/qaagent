import type { FC, ReactNode } from "react";

interface MetricCardProps {
  title: string;
  value: number | string;
  subtitle: string;
  variant?: "default" | "critical" | "warning" | "success";
  icon?: ReactNode;
}

const variants: Record<Required<MetricCardProps>["variant"], {
  border: string;
  bg: string;
  iconBg: string;
  iconColor: string;
  valueColor: string;
}> = {
  default: {
    border: "border-slate-200 dark:border-slate-700",
    bg: "bg-white dark:bg-slate-900",
    iconBg: "bg-blue-100 dark:bg-blue-900/30",
    iconColor: "text-blue-600 dark:text-blue-400",
    valueColor: "text-slate-900 dark:text-slate-100",
  },
  critical: {
    border: "border-red-200 dark:border-red-900/50",
    bg: "bg-gradient-to-br from-red-50 to-white dark:from-red-950/20 dark:to-slate-900",
    iconBg: "bg-red-100 dark:bg-red-900/30",
    iconColor: "text-red-600 dark:text-red-400",
    valueColor: "text-red-600 dark:text-red-400",
  },
  warning: {
    border: "border-orange-200 dark:border-orange-900/50",
    bg: "bg-gradient-to-br from-orange-50 to-white dark:from-orange-950/20 dark:to-slate-900",
    iconBg: "bg-orange-100 dark:bg-orange-900/30",
    iconColor: "text-orange-600 dark:text-orange-400",
    valueColor: "text-orange-600 dark:text-orange-400",
  },
  success: {
    border: "border-green-200 dark:border-green-900/50",
    bg: "bg-gradient-to-br from-green-50 to-white dark:from-green-950/20 dark:to-slate-900",
    iconBg: "bg-green-100 dark:bg-green-900/30",
    iconColor: "text-green-600 dark:text-green-400",
    valueColor: "text-green-600 dark:text-green-400",
  },
};

export const MetricCard: FC<MetricCardProps> = ({ title, value, subtitle, variant = "default", icon }) => {
  const style = variants[variant];

  return (
    <div className={`rounded-xl border-2 ${style.border} ${style.bg} p-6 shadow-sm transition-all hover:shadow-md`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">{title}</p>
          <p className={`mt-2 truncate text-3xl font-bold ${style.valueColor}`}>{value}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">{subtitle}</p>
        </div>
        {icon && (
          <div className={`rounded-lg p-3 ${style.iconBg}`}>
            <div className={style.iconColor}>{icon}</div>
          </div>
        )}
      </div>
    </div>
  );
};
