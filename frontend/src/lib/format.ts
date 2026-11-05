const TZ = 'Europe/Rome'

const dateFmt = new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: 'short', year: 'numeric', timeZone: TZ })
const shortDateFmt = new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: 'short', timeZone: TZ })
const dateTimeFmt = new Intl.DateTimeFormat('it-IT', {
  weekday: 'short',
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: TZ,
})

export const formatDate = (iso: string) => dateFmt.format(new Date(iso))
export const formatShortDate = (iso: string) => shortDateFmt.format(new Date(iso))
export const formatDateTime = (iso: string) => dateTimeFmt.format(new Date(iso))

/** Numbers in Italian format; `null` renders as an em dash (= not available). */
export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '—'
  return value.toLocaleString('it-IT', { maximumFractionDigits: digits, minimumFractionDigits: 0 })
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  return value === null || value === undefined ? '—' : `${formatNumber(value, digits)}%`
}

export const RESULT_LABEL: Record<string, { short: string; long: string }> = {
  W: { short: 'V', long: 'Vittoria' },
  D: { short: 'N', long: 'Pareggio' },
  L: { short: 'P', long: 'Sconfitta' },
}

export const STATUS_LABEL: Record<string, string> = {
  scheduled: 'In programma',
  live: 'In corso',
  finished: 'Terminata',
  postponed: 'Rinviata',
  cancelled: 'Annullata',
}

export const POSITION_LABEL: Record<string, string> = {
  GK: 'Portiere',
  DEF: 'Difensore',
  MID: 'Centrocampista',
  FWD: 'Attaccante',
}

export const AVAILABILITY_LABEL: Record<string, string> = {
  injury: 'Infortunio',
  suspension: 'Squalifica',
  international_duty: 'Impegno con la nazionale',
  doubtful: 'In dubbio',
  other: 'Altro',
}

/** Capitalise a label, leaving metric abbreviations such as 'xG' untouched. */
export const capitalize = (s: string) => (/^x[A-Z]/.test(s) ? s : s.charAt(0).toUpperCase() + s.slice(1))

export const teamLabel = (t: { name: string; short_name?: string | null }) => t.short_name ?? t.name
