import { useState } from "react";

import { useAssignBed, useDischargeBed } from "../api/hooks";
import type { Bed } from "../api/types";
import { BedStatusBadge } from "./Badges";
import { PatientPicker } from "./PatientPicker";

interface Props {
  bed: Bed;
  /** Patients already in a bed (from the unfiltered board); they are not offered. */
  assignedIds: ReadonlySet<number>;
}

export function BedCard({ bed, assignedIds }: Props) {
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
          className="flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (patientId) assign.mutate({ bedId: bed.id, patientId: Number(patientId) }, { onSuccess: () => setPatientId("") });
          }}
        >
          <label htmlFor={selectId} className="sr-only">
            Patient for bed {bed.num}
          </label>
          <PatientPicker
            id={selectId}
            className="input py-1 text-sm"
            value={patientId}
            onChange={setPatientId}
            exclude={assignedIds}
            searchLabel={`Search patients for bed ${bed.num}`}
            placeholder="Choose patient…"
          />
          <button type="submit" className="btn-primary self-start px-3 py-1 text-sm" disabled={!patientId || assign.isPending}>
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
