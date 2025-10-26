import { ResponsiveContainer, LineChart, XAxis, YAxis, Tooltip, Line } from "recharts";
import type { RunTrendPoint } from "../../types";

interface AverageRiskScoreChartProps {
  data: RunTrendPoint[];
}

export function AverageRiskScoreChart({ data }: AverageRiskScoreChartProps) {
  const chartData = data
    .filter((point) => typeof point.average_risk_score === "number" && point.average_risk_score !== null)
    .map((point) => ({
      date: new Date(point.created_at).toLocaleDateString(),
      score: point.average_risk_score as number,
    }));

  if (!chartData.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Average risk scores appear after multiple high-quality runs.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={chartData}>
        <XAxis dataKey="date" stroke="#64748b" />
        <YAxis stroke="#64748b" domain={[0, 100]} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} />
        <Line type="monotone" dataKey="score" stroke="#0ea5e9" strokeWidth={2} dot />
      </LineChart>
    </ResponsiveContainer>
  );
}
