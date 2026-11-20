import { useState } from "react";

import { useAssignBed, useDischargeBed } from "../api/hooks";
import type { Bed, Patient } from "../api/types";
import { BedStatusBadge } from "./Badges";

interface Props {
  bed: Bed;
  /** Patients who are not in a bed yet (candidates for assignment). */
  unassigned: Patient[];
}

export function BedCard({ bed, unassigned }: Props) {
  const [patientId, setPatientId] = useState("");
  const assign = useAssignBed();
  const discharge = useDischargeBed();
  const error = assign.error ?? discharge.error;
  const selectId = `assign-${bed.id}`;

  return (
    <article className="card flex flex-col gap-3" aria-labelledby={`bed-${bed.id}-title`}>
      <div className="flex items-start justify-between gap-2">
        <h2 id={`bed-${bed.id}-title`} className="text-lg font-semibold text-white">
          Bed {bed.num}
        </h2>
        <BedStatusBadge status={bed.status} />
      </div>
      <p className="text-sm text-slate-400">{bed.patient ?? "Empty"}</p>

      {bed.status === "Available" && (
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (patientId) assign.mutate({ bedId: bed.id, patientId: Number(patientId) }, { onSuccess: () => setPatientId("") });
          }}
        >
          <label htmlFor={selectId} className="sr-only">
            Patient for bed {bed.num}
          </label>
          <select id={selectId} className="input py-1 text-sm" value={patientId} onChange={(e) => setPatientId(e.target.value)}>
            <option value="">{unassigned.length ? "Choose patient…" : "No unassigned patients"}</option>
            {unassigned.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name}
              </option>
            ))}
          </select>
          <button type="submit" className="btn-primary px-3 py-1 text-sm" disabled={!patientId || assign.isPending}>
            {assign.isPending ? "Assigning…" : "Assign"}
          </button>
        </form>
      )}

      {(bed.status === "Occupied" || bed.status === "Pending_Discharge") && (
        <button
          type="button"
          className="btn-secondary self-start"
          disabled={discharge.isPending}
          onClick={() => discharge.mutate(bed.id)}
        >
          {discharge.isPending ? "Discharging…" : `Discharge bed ${bed.num}`}
        </button>
      )}

      {error && (
        <p role="alert" className="text-sm text-red-300">
          {error.message}
        </p>
      )}
    </article>
  );
}
