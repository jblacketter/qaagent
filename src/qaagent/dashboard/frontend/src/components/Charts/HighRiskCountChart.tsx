import { ResponsiveContainer, LineChart, XAxis, YAxis, Tooltip, Line } from "recharts";
import type { RunTrendPoint } from "../../types";

interface HighRiskCountChartProps {
  data: RunTrendPoint[];
}

export function HighRiskCountChart({ data }: HighRiskCountChartProps) {
  const chartData = data.map((point) => ({
    date: new Date(point.created_at).toLocaleDateString(),
    highRisks: point.high_risk_count,
  }));

  if (!chartData.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Collect additional runs to visualize high-risk trends.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={chartData}>
        <XAxis dataKey="date" stroke="#64748b" />
        <YAxis stroke="#64748b" allowDecimals={false} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} />
        <Line type="monotone" dataKey="highRisks" stroke="#dc2626" strokeWidth={2} dot />
      </LineChart>
    </ResponsiveContainer>
  );
}
