import type { BedStatus, Priority } from "../api/types";
import { BED_STATUS_INFO, PRIORITY_INFO } from "../lib/format";

const base = "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset";

export function PriorityBadge({ priority }: { priority: Priority }) {
  const info = PRIORITY_INFO[priority];
  return <span className={`${base} ${info.className}`}>P{priority} · {info.label}</span>;
}

export function BedStatusBadge({ status }: { status: BedStatus }) {
  const info = BED_STATUS_INFO[status];
  return (
    <span className={`${base} ${info.className}`}>
      <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${info.dot}`} />
      {info.label}
    </span>
  );
}
