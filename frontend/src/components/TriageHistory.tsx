import { Link, useSearchParams } from "react-router-dom";

import { useTriageHistory } from "../api/hooks";
import type { Priority } from "../api/types";
import { PriorityBadge } from "./Badges";
import { Pagination } from "./Pagination";
import { EmptyState, ErrorState, LoadingState } from "./QueryState";
import { formatDateTime } from "../lib/format";

const PAGE_SIZE = 10;

/** Triage history with filters kept in the URL (?priority=1&page=2), so views are shareable. */
export function TriageHistory() {
  const [params, setParams] = useSearchParams();
  const priority = params.get("priority") ? (Number(params.get("priority")) as Priority) : undefined;
  const offset = Number(params.get("offset") ?? 0);
  const history = useTriageHistory({ priority, limit: PAGE_SIZE, offset });

  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    setParams(next, { replace: true });
  };

  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold text-white">Triage history</h2>
        <label className="flex items-center gap-2 text-sm text-slate-400">
          Priority
          <select
            className="input w-auto py-1"
            value={priority ?? ""}
            onChange={(e) => update({ priority: e.target.value || null, offset: null })}
          >
            <option value="">All</option>
            <option value="1">P1 Critical</option>
            <option value="2">P2 High</option>
            <option value="3">P3 Moderate</option>
            <option value="4">P4 Low</option>
          </select>
        </label>
      </div>

      {history.isPending ? (
        <LoadingState />
      ) : history.isError ? (
        <ErrorState error={history.error} onRetry={() => history.refetch()} />
      ) : history.data.items.length === 0 ? (
        <EmptyState title="No triage records">Try another filter or run a new triage.</EmptyState>
      ) : (
        <>
          <ul className="divide-y divide-slate-800" aria-busy={history.isFetching}>
            {history.data.items.map((record) => (
              <li key={record.id} className="flex flex-wrap items-center gap-3 py-3 text-sm">
                <PriorityBadge priority={record.priority} />
                <Link to={`/patients/${record.patient_id}`} className="font-medium text-blue-300 hover:underline">
                  Patient #{record.patient_id}
                </Link>
                <span className="text-slate-300">{record.recommendation}</span>
                <span className="text-slate-500">O₂ {record.oxygen_level}% · age {record.age}</span>
                <time className="ml-auto text-xs text-slate-500" dateTime={record.created_at}>
                  {formatDateTime(record.created_at)}
                </time>
              </li>
            ))}
          </ul>
          <Pagination
            total={history.data.total}
            limit={PAGE_SIZE}
            offset={offset}
            onChange={(next) => update({ offset: next ? String(next) : null })}
          />
        </>
      )}
    </div>
  );
}
