export interface BarDatum {
  label: string;
  value: number;
  className: string;
}

/**
 * Dependency-free horizontal bar chart. Widths are relative to the largest
 * value; the numbers are also rendered as text so the chart is accessible.
 */
export function BarChart({ data, title }: { data: BarDatum[]; title: string }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <figure>
      <figcaption className="mb-3 text-sm font-semibold text-slate-300">{title}</figcaption>
      <ul className="space-y-2">
        {data.map((d) => (
          <li key={d.label} className="grid grid-cols-[8rem_1fr_2.5rem] items-center gap-3 text-sm">
            <span className="truncate text-slate-400">{d.label}</span>
            <span className="h-3 rounded-full bg-slate-800" aria-hidden>
              <span
                data-testid={`bar-${d.label}`}
                className={`block h-3 rounded-full ${d.className}`}
                style={{ width: `${(d.value / max) * 100}%` }}
              />
            </span>
            <span className="text-right font-mono text-slate-200">{d.value}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}
