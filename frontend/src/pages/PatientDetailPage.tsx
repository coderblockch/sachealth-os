import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { usePatient } from "../api/hooks";
import { PriorityBadge } from "../components/Badges";
import { EmptyState, ErrorState, LoadingState } from "../components/QueryState";
import { formatDateTime } from "../lib/format";

export function PatientDetailPage() {
  const id = Number(useParams().patientId);
  const patient = usePatient(id);

  if (patient.isPending) return <LoadingState label="Loading patient…" />;
  if (patient.isError) {
    if (patient.error instanceof ApiError && patient.error.status === 404) {
      return <EmptyState title="Patient not found"><Link to="/patients" className="text-blue-300">Back to patients</Link></EmptyState>;
    }
    return <ErrorState error={patient.error} onRetry={() => patient.refetch()} />;
  }

  const p = patient.data;
  return (
    <section aria-labelledby="patient-title">
      <Link to="/patients" className="text-sm text-blue-300 hover:underline">
        ← Patients
      </Link>
      <h1 id="patient-title" className="page-title mt-2">
        {p.full_name}
      </h1>
      <dl className="mb-6 flex flex-wrap gap-x-8 gap-y-1 text-sm text-slate-400">
        <div><dt className="inline">Patient ID: </dt><dd className="inline text-slate-200">#{p.id}</dd></div>
        <div><dt className="inline">Age: </dt><dd className="inline text-slate-200">{p.age}</dd></div>
        <div><dt className="inline">Current bed: </dt><dd className="inline text-slate-200">{p.current_bed ?? "None"}</dd></div>
        <div><dt className="inline">Registered: </dt><dd className="inline text-slate-200">{formatDateTime(p.created_at)}</dd></div>
      </dl>

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-white">Triage history</h2>
        {p.triage_history.length === 0 ? (
          <EmptyState title="No triages yet">
            <Link to="/triage" className="text-blue-300">Run a triage</Link> for this patient.
          </EmptyState>
        ) : (
          <ol className="relative space-y-4 border-l border-slate-700 pl-5">
            {p.triage_history.map((r) => (
              <li key={r.id}>
                <span aria-hidden className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-blue-500" />
                <div className="flex flex-wrap items-center gap-3">
                  <PriorityBadge priority={r.priority} />
                  <span className="font-medium text-white">{r.recommendation}</span>
                  <time className="text-xs text-slate-500" dateTime={r.created_at}>{formatDateTime(r.created_at)}</time>
                </div>
                <p className="mt-1 text-sm text-slate-400">
                  O₂ {r.oxygen_level}% · age {r.age}{r.symptoms ? ` · “${r.symptoms}”` : ""}
                </p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
