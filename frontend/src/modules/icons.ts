import type { LucideIcon } from 'lucide-react'
import {
  Activity,
  Bot,
  Boxes,
  Database,
  Folder,
  LayoutDashboard,
  Server,
} from 'lucide-react'

/**
 * Icons a project manifest is allowed to name.
 * Keep this list identical to ALLOWED_PROJECT_ICONS in
 * backend/app/modules/manifest.py.
 */
export const PROJECT_ICONS = {
  activity: Activity,
  bot: Bot,
  boxes: Boxes,
  database: Database,
  folder: Folder,
  'layout-dashboard': LayoutDashboard,
  server: Server,
} as const satisfies Record<string, LucideIcon>

export type ProjectIconName = keyof typeof PROJECT_ICONS

export function isAllowedProjectIcon(icon: string): icon is ProjectIconName {
  return Object.prototype.hasOwnProperty.call(PROJECT_ICONS, icon)
}

export function resolveProjectIcon(icon: ProjectIconName): LucideIcon {
  return PROJECT_ICONS[icon]
}
