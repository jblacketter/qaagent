import type { RiskRecord } from "../../types";

interface RiskHeatmapProps {
  risks: RiskRecord[];
}

type Level = "low" | "medium" | "high";

const levelLabel: Record<Level, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

const background: Record<Level, string> = {
  low: "bg-green-100 dark:bg-green-900/20",
  medium: "bg-yellow-100 dark:bg-yellow-900/20",
  high: "bg-red-100 dark:bg-red-900/20",
};

function classify(value: number): Level {
  if (value >= 4) return "high";
  if (value >= 2) return "medium";
  return "low";
}

export function RiskHeatmap({ risks }: RiskHeatmapProps) {
  if (!risks.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Run risk aggregation to populate heatmap.</p>;
  }

  const matrix: Record<Level, Record<Level, number>> = {
    high: { high: 0, medium: 0, low: 0 },
    medium: { high: 0, medium: 0, low: 0 },
    low: { high: 0, medium: 0, low: 0 },
  };

  risks.forEach((risk) => {
    const coverage = classify(risk.factors.coverage ?? 0);
    const churn = classify(risk.factors.churn ?? 0);
    matrix[churn][coverage] += 1;
  });

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="w-24" />
            {(["low", "medium", "high"] as Level[]).map((coverage) => (
              <th key={coverage} className="p-2 text-slate-600 dark:text-slate-300">
                Coverage {levelLabel[coverage]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(["high", "medium", "low"] as Level[]).map((churn) => (
            <tr key={churn}>
              <th className="p-2 text-left text-slate-600 dark:text-slate-300">Churn {levelLabel[churn]}</th>
              {(["low", "medium", "high"] as Level[]).map((coverage) => (
                <td
                  key={coverage}
                  className={`p-3 text-center ${
                    matrix[churn][coverage] > 0 ? background[coverage] : "bg-slate-100 dark:bg-slate-800"
                  }`}
                >
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                    {matrix[churn][coverage]}
                  </span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
