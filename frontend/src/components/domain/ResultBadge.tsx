import { RESULT_LABEL } from '../../lib/format'

const STYLE: Record<string, string> = {
  W: 'bg-pitch/15 text-pitch border-pitch/40',
  D: 'bg-ink-faint/15 text-ink-muted border-ink-faint/40',
  L: 'bg-danger/15 text-danger border-danger/40',
}

export function ResultBadge({ result, title, small = false }: { result: string; title?: string; small?: boolean }) {
  const label = RESULT_LABEL[result]
  return (
    <span
      title={title ?? label?.long}
      aria-label={label?.long}
      className={`inline-flex items-center justify-center rounded border font-bold ${small ? 'size-4 text-[9px]' : 'size-6 text-xs'} ${STYLE[result] ?? ''}`}
    >
      {label?.short ?? '?'}
    </span>
  )
}

export function FormStrip({ results, small = false }: { results: string[]; small?: boolean }) {
  if (results.length === 0) return <span className="text-sm text-ink-faint">Nessuna partita</span>
  return (
    <span className={`inline-flex ${small ? 'gap-0.5' : 'gap-1'}`}>
      {results.map((r, i) => (
        <ResultBadge key={i} result={r} small={small} />
      ))}
    </span>
  )
}
