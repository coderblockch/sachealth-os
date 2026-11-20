import { useBeds, usePatients } from "../api/hooks";
import { BED_STATUSES, type BedStatus } from "../api/types";
import { BedCard } from "../components/BedCard";
import { EmptyState, ErrorState, LoadingState } from "../components/QueryState";
import { BED_STATUS_INFO } from "../lib/format";
import { useSearchParams } from "react-router-dom";

export function BedsPage() {
  const [params, setParams] = useSearchParams();
  const raw = params.get("status");
  const status = BED_STATUSES.includes(raw as BedStatus) ? (raw as BedStatus) : undefined;
  const beds = useBeds(status);
  const patients = usePatients({ limit: 200, offset: 0 });

  const assignedIds = new Set((beds.data ?? []).map((b) => b.patient_id).filter((id) => id !== null));
  const unassigned = (patients.data?.items ?? []).filter((p) => !assignedIds.has(p.id));

  return (
    <section aria-labelledby="beds-title">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 id="beds-title" className="page-title">
            Beds board
          </h1>
          <p className="text-sm text-slate-400">Assign registered patients to available beds, or discharge them.</p>
        </div>
        <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-1">
          {[undefined, ...BED_STATUSES].map((s) => (
            <button
              key={s ?? "all"}
              type="button"
              aria-pressed={status === s}
              onClick={() => setParams(s ? { status: s } : {}, { replace: true })}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${status === s ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"}`}
            >
              {s ? BED_STATUS_INFO[s].label : "All"}
            </button>
          ))}
        </div>
      </div>

      {beds.isPending ? (
        <LoadingState label="Loading beds…" />
      ) : beds.isError ? (
        <ErrorState error={beds.error} onRetry={() => beds.refetch()} />
      ) : beds.data.length === 0 ? (
        <EmptyState title="No beds with this status" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {beds.data.map((bed) => (
            <BedCard key={bed.id} bed={bed} unassigned={unassigned} />
          ))}
        </div>
      )}
    </section>
  );
}
