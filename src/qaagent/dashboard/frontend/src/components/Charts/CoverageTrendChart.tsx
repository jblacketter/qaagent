import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from "recharts";

export interface CoverageTrendPoint {
  runId: string;
  createdAt: string;
  averageCoverage: number | null;
  highRiskCount: number;
}

export interface CoverageTrendChartProps {
  data: CoverageTrendPoint[];
}

export function CoverageTrendChart({ data }: CoverageTrendChartProps) {
  const chartData = data
    .map((point) => ({
      date: new Date(point.createdAt).toLocaleDateString(),
      coverage: point.averageCoverage !== null ? Math.round(point.averageCoverage * 100) : null,
    }))
    .filter((point) => point.coverage !== null);

  if (chartData.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Coverage data unavailable.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={chartData}>
        <XAxis dataKey="date" stroke="#64748b" />
        <YAxis stroke="#64748b" unit="%" />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} />
        <Line type="monotone" dataKey="coverage" stroke="#22c55e" strokeWidth={2} dot />
      </LineChart>
    </ResponsiveContainer>
  );
}
