import { Link } from "react-router-dom";

import { useStats } from "../api/hooks";
import { BED_STATUSES } from "../api/types";
import { BarChart } from "../components/BarChart";
import { ErrorState, LoadingState } from "../components/QueryState";
import { BED_STATUS_INFO, PRIORITY_INFO } from "../lib/format";

const BAR_COLORS = {
  Available: "bg-emerald-400",
  Occupied: "bg-red-400",
  Pending_Discharge: "bg-amber-400",
  Cleaning: "bg-sky-400",
} as const;
const PRIORITY_COLORS = { 1: "bg-red-400", 2: "bg-amber-400", 3: "bg-sky-400", 4: "bg-emerald-400" } as const;

function StatCard({ label, value, hint }: { label: string; value: number | string; hint?: string }) {
  return (
    <div className="card">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-bold text-white sm:text-3xl">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export function DashboardPage() {
  const stats = useStats();

  if (stats.isPending) return <LoadingState label="Loading dashboard…" />;
  if (stats.isError) return <ErrorState error={stats.error} onRetry={() => stats.refetch()} />;

  const beds = stats.data.beds_by_status;
  const triage = stats.data.triage_by_priority;
  const totalBeds = BED_STATUSES.reduce((sum, status) => sum + beds[status], 0);
  const totalTriage = Object.values(triage).reduce((sum, n) => sum + n, 0);
  const occupancy = totalBeds ? Math.round(((beds.Occupied + beds.Pending_Discharge) / totalBeds) * 100) : 0;

  return (
    <section aria-labelledby="dashboard-title">
      <h1 id="dashboard-title" className="page-title">
        Dashboard
      </h1>
      <p className="mb-6 text-sm text-slate-400">Live numbers from the API (<code>GET /stats</code>).</p>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard label="Available beds" value={beds.Available} hint={`of ${totalBeds} beds`} />
        <StatCard label="Occupancy" value={`${occupancy}%`} hint="occupied + pending discharge" />
        <StatCard label="Critical triages" value={triage["1"]} hint="priority 1, all time" />
        <StatCard label="Triage records" value={totalTriage} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="card">
          <BarChart
            title="Beds by status"
            data={BED_STATUSES.map((status) => ({
              label: BED_STATUS_INFO[status].label,
              value: beds[status],
              className: BAR_COLORS[status],
            }))}
          />
          <Link to="/beds" className="mt-4 inline-block text-sm text-blue-300 hover:underline">
            Open beds board →
          </Link>
        </div>
        <div className="card">
          <BarChart
            title="Triage records by priority"
            data={([1, 2, 3, 4] as const).map((p) => ({
              label: `P${p} ${PRIORITY_INFO[p].label}`,
              value: triage[String(p) as "1" | "2" | "3" | "4"],
              className: PRIORITY_COLORS[p],
            }))}
          />
          <Link to="/triage" className="mt-4 inline-block text-sm text-blue-300 hover:underline">
            Run a triage →
          </Link>
        </div>
      </div>
    </section>
  );
}
