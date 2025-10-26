import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from "recharts";
import type { RiskRecord } from "../../types";

export interface RiskFactorsChartProps {
  risks: RiskRecord[];
}

export function RiskFactorsChart({ risks }: RiskFactorsChartProps) {
  const data = risks.slice(0, 5).map((risk) => ({
    component: risk.component,
    security: risk.factors.security ?? 0,
    coverage: risk.factors.coverage ?? 0,
    churn: risk.factors.churn ?? 0,
  }));

  if (data.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No risk factors available.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <XAxis dataKey="component" stroke="#64748b" tick={{ fontSize: 12 }} height={60} interval={0} angle={-20} textAnchor="end" />
        <YAxis stroke="#64748b" />
        <Legend />
        <Tooltip cursor={{ fill: "rgba(148, 163, 184, 0.12)" }} />
        <Bar dataKey="security" stackId="a" fill="#dc2626" name="Security" radius={[6, 6, 0, 0]} />
        <Bar dataKey="coverage" stackId="a" fill="#f59e0b" name="Coverage" radius={[6, 6, 0, 0]} />
        <Bar dataKey="churn" stackId="a" fill="#3b82f6" name="Churn" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
