import type { BedStatus, Priority } from "../api/types";

export const PRIORITY_INFO: Record<Priority, { label: string; className: string }> = {
  1: { label: "Critical", className: "bg-red-500/15 text-red-300 ring-red-500/40" },
  2: { label: "High", className: "bg-amber-500/15 text-amber-300 ring-amber-500/40" },
  3: { label: "Moderate", className: "bg-sky-500/15 text-sky-300 ring-sky-500/40" },
  4: { label: "Low", className: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40" },
};

export const BED_STATUS_INFO: Record<BedStatus, { label: string; className: string; dot: string }> = {
  Available: { label: "Available", className: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40", dot: "bg-emerald-400" },
  Occupied: { label: "Occupied", className: "bg-red-500/15 text-red-300 ring-red-500/40", dot: "bg-red-400" },
  Pending_Discharge: { label: "Pending discharge", className: "bg-amber-500/15 text-amber-300 ring-amber-500/40", dot: "bg-amber-400" },
  Cleaning: { label: "Cleaning", className: "bg-sky-500/15 text-sky-300 ring-sky-500/40", dot: "bg-sky-400" },
};

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
}
