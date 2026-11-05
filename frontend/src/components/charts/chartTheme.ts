/** Chart colour roles (validated categorical pair) and axis styling. */
export const SERIES = {
  one: 'var(--color-series-1)',
  two: 'var(--color-series-2)',
  three: 'var(--color-series-3)',
}

export const AXIS = {
  stroke: 'var(--color-line)',
  tick: { fill: 'var(--color-ink-faint)', fontSize: 11 },
}

/** Legend labels stay in ink tokens; the swatch carries the series colour. */
export const legendText = (value: string) => ({ value, color: 'var(--color-ink-muted)' })
