export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="size-8" aria-hidden="true">
        <rect x="1" y="1" width="30" height="30" rx="8" className="fill-pitch-dim" />
        <rect x="6" y="8" width="20" height="16" rx="1.5" fill="none" className="stroke-pitch" strokeWidth="1.5" />
        <line x1="16" y1="8" x2="16" y2="24" className="stroke-pitch" strokeWidth="1.5" />
        <circle cx="16" cy="16" r="3.5" fill="none" className="stroke-pitch" strokeWidth="1.5" />
      </svg>
      <div className="leading-tight">
        <p className="text-sm font-bold tracking-wide">FOOTBALL AI</p>
        <p className="text-[11px] font-medium tracking-[0.2em] text-ink-faint">ANALYST</p>
      </div>
    </div>
  )
}
