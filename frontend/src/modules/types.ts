import type { ReactNode } from 'react'
import type { ProjectIconName } from './icons'

/**
 * Version 1 manifest. Field names match backend/app/modules/manifest.py
 * and docs/project-module-spec.md.
 */
export interface ProjectNavItem {
  path: string
  label: string
  icon: ProjectIconName
  end: boolean
  documentTitle: string
}

export interface ProjectNav {
  section: string
  order: number
  items: ProjectNavItem[]
}

export interface ProjectManifest {
  schemaVersion: 1
  id: string
  name: string
  description: string
  pythonPackage: string
  routeBase: string
  apiPrefix: string
  enabled: boolean
  nav: ProjectNav
}

/** One page inside a project, relative to manifest.routeBase. */
export interface ProjectRouteDefinition {
  index?: boolean
  path?: string
  element: ReactNode
}

/**
 * Default export of projects/{id}/frontend/index.tsx.
 * A project may expose several pages, for example /system-monitor
 * and /system-monitor/services.
 */
export interface ProjectFrontendModule {
  routes: ProjectRouteDefinition[]
}

export interface DiscoveredProject {
  manifest: ProjectManifest
  loadFrontend: () => Promise<ProjectFrontendModule>
}

/** Absolute sidebar link derived from a manifest. The shell does not read this yet. */
export interface ProjectNavLink {
  projectId: string
  to: string
  label: string
  icon: ProjectIconName
  end: boolean
  documentTitle: string
}

export interface ProjectNavSection {
  section: string
  order: number
  links: ProjectNavLink[]
}
