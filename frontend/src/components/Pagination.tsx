interface Props {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}

/** Offset/limit pagination that matches the API's Page response. */
export function Pagination({ total, limit, offset, onChange }: Props) {
  if (total <= limit) return null;
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.ceil(total / limit);
  return (
    <nav aria-label="Pagination" className="mt-4 flex items-center justify-between text-sm text-slate-400">
      <span>
        Page {page} of {pages} · {total} results
      </span>
      <div className="flex gap-2">
        <button type="button" className="btn-secondary" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
          Previous
        </button>
        <button type="button" className="btn-secondary" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
          Next
        </button>
      </div>
    </nav>
  );
}
