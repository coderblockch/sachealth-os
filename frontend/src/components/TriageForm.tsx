import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";
import { Link } from "react-router-dom";
import type { z } from "zod";

import { useCreateTriage, usePatients } from "../api/hooks";
import { toTriageRequest, triageSchema, type TriageFormValues } from "../lib/triageForm";
import { PriorityBadge } from "./Badges";
import { FormField } from "./FormField";

export function TriageForm() {
  const createTriage = useCreateTriage();
  const patients = usePatients({ limit: 100, offset: 0 });
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<TriageFormValues, unknown, z.output<typeof triageSchema>>({
    resolver: zodResolver(triageSchema),
    defaultValues: { mode: "new", patientName: "", patientId: "", age: "", oxygen: "", symptoms: "" },
  });
  const mode = useWatch({ control, name: "mode" });

  const onSubmit = handleSubmit((values) =>
    createTriage.mutate(toTriageRequest(values), {
      onSuccess: () => reset({ mode: values.mode, patientName: "", patientId: "", age: "", oxygen: "", symptoms: "" }),
    }),
  );

  const result = createTriage.data;

  return (
    <div className="card">
      <h2 className="mb-4 text-lg font-semibold text-white">New triage</h2>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4" aria-describedby="triage-help">
        <p id="triage-help" className="text-xs text-slate-500">
          Rules: O₂ &lt; 90% or chest pain → P1 · age &gt; 70 with cough → P2 · fever or headache → P3 · otherwise P4.
        </p>
        <fieldset className="flex gap-4 text-sm">
          <legend className="sr-only">Patient</legend>
          <label className="flex items-center gap-2">
            <input type="radio" value="new" {...register("mode")} /> New patient
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" value="existing" {...register("mode")} /> Existing patient
          </label>
        </fieldset>

        {mode === "new" ? (
          <FormField label="Patient name" error={errors.patientName?.message}>
            <input className="input" autoComplete="off" {...register("patientName")} />
          </FormField>
        ) : (
          <FormField label="Patient" error={errors.patientId?.message}>
            <select className="input" {...register("patientId")}>
              <option value="">Select a patient…</option>
              {patients.data?.items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.full_name} (#{p.id}, {p.age} y)
                </option>
              ))}
            </select>
          </FormField>
        )}

        <div className="grid grid-cols-2 gap-4">
          <FormField label="Age" error={errors.age?.message}>
            <input type="number" inputMode="numeric" className="input" {...register("age")} />
          </FormField>
          <FormField label="O₂ saturation (%)" error={errors.oxygen?.message}>
            <input type="number" inputMode="numeric" className="input" {...register("oxygen")} />
          </FormField>
        </div>
        <FormField label="Symptoms" error={errors.symptoms?.message} hint="e.g. chest pain, cough, fever">
          <textarea rows={3} className="input" {...register("symptoms")} />
        </FormField>

        {createTriage.isError && (
          <p role="alert" className="rounded-lg bg-red-500/10 p-3 text-sm text-red-200">
            {createTriage.error.message}
          </p>
        )}
        <button type="submit" className="btn-primary" disabled={createTriage.isPending}>
          {createTriage.isPending ? "Analyzing…" : "Analyze & save"}
        </button>
      </form>

      {result && (
        <div role="status" aria-live="polite" className="mt-5 rounded-xl border border-slate-700 bg-slate-800/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">CDSS recommendation</p>
          <p className="mt-1 text-xl font-bold text-white">{result.recommendation}</p>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
            <PriorityBadge priority={result.priority} />
            <Link className="text-blue-300 hover:underline" to={`/patients/${result.patient_id}`}>
              View patient #{result.patient_id}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
