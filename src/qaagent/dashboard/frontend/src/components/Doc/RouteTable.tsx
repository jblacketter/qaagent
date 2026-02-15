import type { RouteDoc } from "../../types";

const methodStyles: Record<string, string> = {
  GET: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  POST: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  PUT: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  PATCH: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  DELETE: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

interface RouteTableProps {
  routes: RouteDoc[];
}

export function RouteTable({ routes }: RouteTableProps) {
  if (!routes.length) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">No routes.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-700">
            <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
              Method
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
              Path
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
              Auth
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
              Summary
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {routes.map((route, idx) => (
            <tr
              key={`${route.method}-${route.path}-${idx}`}
              className="hover:bg-slate-50 dark:hover:bg-slate-800/50"
            >
              <td className="px-3 py-2">
                <span
                  className={`inline-block rounded px-2 py-0.5 text-xs font-bold ${methodStyles[route.method] ?? "bg-slate-100 text-slate-600"}`}
                >
                  {route.method}
                </span>
              </td>
              <td className="px-3 py-2 font-mono text-xs text-slate-700 dark:text-slate-300">
                {route.path}
              </td>
              <td className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                {route.auth_required ? "Yes" : "No"}
              </td>
              <td className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                {route.summary ?? "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
