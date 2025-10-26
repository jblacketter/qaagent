import { ResponsiveContainer, BarChart, XAxis, YAxis, Tooltip, Bar, Cell } from "recharts";
import type { RiskRecord } from "../../types";

const colors: Record<string, string> = {
  P0: "#dc2626",
  P1: "#f97316",
  P2: "#facc15",
  P3: "#22c55e",
};

export interface RiskDistributionChartProps {
  risks: RiskRecord[];
}

export function RiskDistributionChart({ risks }: RiskDistributionChartProps) {
  const counts = risks.reduce<Record<string, number>>((acc, risk) => {
    acc[risk.band] = (acc[risk.band] ?? 0) + 1;
    return acc;
  }, {});

  const data = ["P0", "P1", "P2", "P3"].map((band) => ({ band, count: counts[band] ?? 0 }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <XAxis dataKey="band" stroke="#64748b" />
        <YAxis allowDecimals={false} stroke="#64748b" />
        <Tooltip cursor={{ fill: "rgba(148, 163, 184, 0.12)" }} />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.band} fill={colors[entry.band] ?? "#64748b"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
