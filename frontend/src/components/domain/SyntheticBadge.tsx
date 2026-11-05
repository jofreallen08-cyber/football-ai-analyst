export function SyntheticBadge({ className = '' }: { className?: string }) {
  return (
    <span
      title="Dati sintetici: squadre, giocatori e statistiche inventati a scopo dimostrativo"
      className={`inline-flex items-center rounded-full border border-warn/50 bg-warn/10 px-2 py-0.5 text-[11px] font-semibold tracking-wide text-warn uppercase ${className}`}
    >
      Sintetico
    </span>
  )
}
