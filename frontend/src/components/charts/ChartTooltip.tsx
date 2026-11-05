interface Row {
  label: string
  value: string
  color?: string
}

/** Shared tooltip body: text in ink tokens, series identified by a colour swatch. */
export function TooltipBox({ title, rows }: { title: string; rows: Row[] }) {
  return (
    <div className="rounded-md border border-line bg-navy-900/95 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1 font-semibold text-ink">{title}</p>
      {rows.map((r) => (
        <p key={r.label} className="flex items-center gap-2 text-ink-muted">
          {r.color && <span className="inline-block size-2.5 rounded-sm" style={{ background: r.color }} />}
          <span>{r.label}</span>
          <span className="ml-auto pl-3 font-semibold text-ink tabular-nums">{r.value}</span>
        </p>
      ))}
    </div>
  )
}
