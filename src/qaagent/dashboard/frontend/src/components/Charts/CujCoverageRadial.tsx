import { ResponsiveContainer, RadialBarChart, RadialBar, PolarAngleAxis } from "recharts";
import type { CujCoverageRecord } from "../../types";

interface CujCoverageRadialProps {
  data: CujCoverageRecord[];
}

export function CujCoverageRadial({ data }: CujCoverageRadialProps) {
  const chartData = data.slice(0, 6).map((item) => ({
    name: item.name,
    coverage: Math.round(item.coverage * 100),
  }));

  if (!chartData.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Map CUJs in `cuj.yaml` to view coverage gauges.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadialBarChart data={chartData} innerRadius="20%" outerRadius="90%" startAngle={90} endAngle={-270}>
        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
        <RadialBar dataKey="coverage" label={{ position: "insideStart", fill: "#334155", formatter: (value: number) => `${value}%` }} fill="#0ea5e9" cornerRadius={8} />
      </RadialBarChart>
    </ResponsiveContainer>
  );
}
