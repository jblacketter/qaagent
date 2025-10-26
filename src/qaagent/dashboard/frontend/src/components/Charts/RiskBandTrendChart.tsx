import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, Legend } from "recharts";
import type { RunTrendPoint } from "../../types";

interface RiskBandTrendChartProps {
  data: RunTrendPoint[];
}

const COLORS: Record<string, string> = {
  P0: "#dc2626",
  P1: "#f97316",
  P2: "#eab308",
  P3: "#22c55e",
};

const ORDER: Array<keyof typeof COLORS> = ["P3", "P2", "P1", "P0"];

export function RiskBandTrendChart({ data }: RiskBandTrendChartProps) {
  const chartData = data.map((point) => {
    const counts = point.risk_counts || {};
    return {
      date: new Date(point.created_at).toLocaleDateString(),
      ...ORDER.reduce((acc, band) => {
        acc[band] = counts[band] ?? counts[band.toLowerCase()] ?? 0;
        return acc;
      }, {} as Record<string, number>),
    };
  });

  if (!chartData.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Run multiple analyses to populate trend data.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={chartData}>
        <XAxis dataKey="date" stroke="#64748b" />
        <YAxis stroke="#64748b" allowDecimals={false} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} />
        <Legend />
        {ORDER.map((band) => (
          <Area
            key={band}
            type="monotone"
            dataKey={band}
            stackId="risks"
            stroke={COLORS[band]}
            fill={COLORS[band]}
            fillOpacity={0.6}
            name={band}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
