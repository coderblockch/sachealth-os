import { useState } from "react";

import { usePatients } from "../api/hooks";
import type { Patient } from "../api/types";
import { useDebouncedValue } from "../lib/useDebouncedValue";

const PICKER_LIMIT = 20;

interface Props {
  value: string;
  onChange: (patientId: string) => void;
  /** Patients that must not be offered (e.g. already in a bed). */
  exclude?: ReadonlySet<number>;
  searchLabel?: string;
  placeholder?: string;
  className?: string;
  // Passed through to the <select> (FormField injects these).
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}

/**
 * Searchable patient selector. It asks the API for matches (q + limit) instead
 * of loading every patient, so any patient can be reached however many exist.
 */
export function PatientPicker({
  value,
  onChange,
  exclude,
  searchLabel = "Search patients",
  placeholder = "Select a patient…",
  className = "input",
  ...selectProps
}: Props) {
  const [search, setSearch] = useState("");
  const q = useDebouncedValue(search.trim(), 300);
  const result = usePatients({ q: q || undefined, limit: PICKER_LIMIT, offset: 0 });
  // Remember the chosen patient so it stays selectable after the search changes.
  const [selected, setSelected] = useState<Patient | null>(null);

  const matches = (result.data?.items ?? []).filter((p) => !exclude?.has(p.id));
  const keepSelected = selected && String(selected.id) === value && !matches.some((p) => p.id === selected.id);
  const options = keepSelected ? [selected, ...matches] : matches;
  const hasMore = (result.data?.total ?? 0) > (result.data?.items.length ?? 0);

  return (
    <div className="flex flex-col gap-2">
      <input
        type="search"
        className={className}
        aria-label={searchLabel}
        placeholder="Type a name to search…"
        autoComplete="off"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <select
        {...selectProps}
        className={className}
        value={value}
        onChange={(e) => {
          const next = e.target.value;
          setSelected(options.find((p) => String(p.id) === next) ?? null);
          onChange(next);
        }}
      >
        <option value="">
          {result.isPending ? "Loading patients…" : options.length ? placeholder : q ? `No patients match “${q}”` : "No patients available"}
        </option>
        {options.map((p) => (
          <option key={p.id} value={p.id}>
            {p.full_name} (#{p.id}, {p.age} y)
          </option>
        ))}
      </select>
      {hasMore && (
        <p className="text-xs text-slate-500">
          Showing the {PICKER_LIMIT} most recent matches. Type a name to find others.
        </p>
      )}
    </div>
  );
}
