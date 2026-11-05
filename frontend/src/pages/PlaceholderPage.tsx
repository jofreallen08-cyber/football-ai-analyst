import { Construction } from 'lucide-react'

import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import { SimulationBanner } from '../components/ui/SimulationBanner'
import type { NavItem } from '../lib/navigation'

/** Temporary page body until the page's roadmap phase delivers real content. */
export function PlaceholderPage({ item, simulation = false }: { item: NavItem; simulation?: boolean }) {
  return (
    <>
      <PageHeader title={item.label} description={item.description} />
      {simulation && <SimulationBanner />}
      <EmptyState
        icon={Construction}
        title="Sezione in costruzione"
        message={`Questa pagina riceverà contenuti reali nella Fase ${item.phase} della roadmap.`}
      />
    </>
  )
}
