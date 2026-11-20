import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";
import { z } from "zod";
import { useEffect, useState } from "react";

import { useCreatePatient, usePatients } from "../api/hooks";
import { FormField } from "../components/FormField";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../components/QueryState";
import { formatDateTime } from "../lib/format";
import { integerField } from "../lib/triageForm";
import { useDebouncedValue } from "../lib/useDebouncedValue";

const PAGE_SIZE = 10;

const patientSchema = z.object({
  full_name: z.string().trim().min(1, "Name is required").max(120, "Max 120 characters"),
  age: integerField("Age", 0, 130, "Age must be 0–130"),
});

function NewPatientForm() {
  const createPatient = useCreatePatient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<z.input<typeof patientSchema>, unknown, z.output<typeof patientSchema>>({
    resolver: zodResolver(patientSchema),
    defaultValues: { full_name: "", age: "" },
  });
  const onSubmit = handleSubmit((values) => createPatient.mutate(values, { onSuccess: () => reset() }));

  return (
    <form onSubmit={onSubmit} noValidate className="card flex flex-col gap-4" aria-label="Register patient">
      <h2 className="text-lg font-semibold text-white">Register patient</h2>
      <FormField label="Full name" error={errors.full_name?.message}>
        <input className="input" autoComplete="off" {...register("full_name")} />
      </FormField>
      <FormField label="Age" error={errors.age?.message}>
        <input type="number" inputMode="numeric" className="input" {...register("age")} />
      </FormField>
      {createPatient.isError && (
        <p role="alert" className="text-sm text-red-300">
          {createPatient.error.message}
        </p>
      )}
      {createPatient.isSuccess && (
        <p role="status" className="text-sm text-emerald-300">
          Registered {createPatient.data.full_name}.
        </p>
      )}
      <button type="submit" className="btn-primary" disabled={createPatient.isPending}>
        {createPatient.isPending ? "Saving…" : "Register"}
      </button>
    </form>
  );
}

export function PatientsPage() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("q") ?? "");
  const q = useDebouncedValue(search.trim(), 300);
  const offset = Number(params.get("offset") ?? 0);
  // A new search always starts from the first page.
  const effectiveOffset = q === (params.get("q") ?? "") ? offset : 0;
  const patients = usePatients({ q: q || undefined, limit: PAGE_SIZE, offset: effectiveOffset });

  // Once the search settles, put it in the URL (and go back to page 1) so a
  // reload or a shared link shows the same results.
  useEffect(() => {
    if (q === (params.get("q") ?? "")) return;
    const nextParams = new URLSearchParams();
    if (q) nextParams.set("q", q);
    setParams(nextParams, { replace: true });
  }, [q, params, setParams]);

  const setOffset = (next: number) => {
    const nextParams = new URLSearchParams();
    if (q) nextParams.set("q", q);
    if (next) nextParams.set("offset", String(next));
    setParams(nextParams, { replace: true });
  };

  return (
    <section aria-labelledby="patients-title">
      <h1 id="patients-title" className="page-title">
        Patients
      </h1>
      <p className="mb-6 text-sm text-slate-400">Search, browse and open a patient to see their triage history.</p>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="card">
          <label className="mb-4 block">
            <span className="sr-only">Search patients by name</span>
            <input
              type="search"
              className="input"
              placeholder="Search by name…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          {patients.isPending ? (
            <LoadingState />
          ) : patients.isError ? (
            <ErrorState error={patients.error} onRetry={() => patients.refetch()} />
          ) : patients.data.items.length === 0 ? (
            <EmptyState title={q ? `No patients match “${q}”` : "No patients yet"}>
              Register one with the form or run a triage.
            </EmptyState>
          ) : (
            <>
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th scope="col" className="py-2">Name</th>
                    <th scope="col">Age</th>
                    <th scope="col" className="hidden sm:table-cell">Registered</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {patients.data.items.map((p) => (
                    <tr key={p.id}>
                      <td className="py-2">
                        <Link to={`/patients/${p.id}`} className="font-medium text-blue-300 hover:underline">
                          {p.full_name}
                        </Link>
                      </td>
                      <td>{p.age}</td>
                      <td className="hidden text-slate-500 sm:table-cell">{formatDateTime(p.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <Pagination total={patients.data.total} limit={PAGE_SIZE} offset={effectiveOffset} onChange={setOffset} />
            </>
          )}
        </div>
        <NewPatientForm />
      </div>
    </section>
  );
}
