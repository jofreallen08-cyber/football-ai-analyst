import { FlaskConical } from 'lucide-react'

/** Persistent label shown wherever simulated (hypothetical) content appears. */
export function SimulationBanner() {
  return (
    <div
      role="note"
      className="mb-6 flex items-start gap-3 rounded-lg border border-sim/40 bg-sim/10 p-4 text-sm"
    >
      <FlaskConical className="mt-0.5 size-5 shrink-0 text-sim" aria-hidden="true" />
      <p>
        <strong className="text-sim">SIMULAZIONE</strong> — scenari ipotetici basati su dati storici.
        Non sono risultati reali né garantiti.
      </p>
    </div>
  )
}
