import { Link } from 'react-router'

import { EmptyState } from '../components/ui/EmptyState'

export function NotFound() {
  return (
    <div className="space-y-4">
      <EmptyState title="Pagina non trovata" message="L'indirizzo richiesto non esiste." />
      <Link to="/" className="text-sm text-accent hover:underline">
        Torna alla panoramica
      </Link>
    </div>
  )
}
