import {
  Bot,
  FileText,
  FlaskConical,
  LayoutDashboard,
  type LucideIcon,
  Settings,
  Shield,
  Trophy,
  User,
} from 'lucide-react'

export interface NavItem {
  path: string
  label: string
  description: string
  icon: LucideIcon
  /** Roadmap phase in which the page receives real content. */
  phase: number
}

export const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Panoramica', description: 'Riepilogo di campionati, partite e analisi recenti.', icon: LayoutDashboard, phase: 3 },
  { path: '/partite', label: 'Centro Partite', description: 'Calendario, risultati e dettaglio delle partite.', icon: Trophy, phase: 3 },
  { path: '/squadre', label: 'Analisi Squadre', description: 'Forma, rendimento casa/trasferta, xG e statistiche di squadra.', icon: Shield, phase: 3 },
  { path: '/giocatori', label: 'Analisi Giocatori', description: 'Prestazioni individuali e metriche per 90 minuti.', icon: User, phase: 3 },
  { path: '/agenti', label: 'Agenti AI', description: 'Stato e report dei cinque agenti di analisi.', icon: Bot, phase: 6 },
  { path: '/simulazioni', label: 'Laboratorio Simulazioni', description: 'Scenari tattici virtuali basati su dati storici. Le simulazioni non sono risultati reali.', icon: FlaskConical, phase: 5 },
  { path: '/report', label: 'Report', description: 'Report finali generati dal Master Analyst.', icon: FileText, phase: 6 },
  { path: '/impostazioni', label: 'Impostazioni', description: 'Fonti dati, limiti di utilizzo AI e preferenze.', icon: Settings, phase: 7 },
]
