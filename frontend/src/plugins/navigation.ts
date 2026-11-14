import type { DiscoveredProject } from './loader';
import type { ProjectIconName } from './icons';

/** Absolute sidebar link derived from a manifest. */
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

/** Group enabled projects into sidebar sections. Does not render navigation. */
export function buildProjectNavigation(
  projects: readonly DiscoveredProject[],
): ProjectNavSection[] {
  const sections = new Map<string, ProjectNavSection>()
  for (const project of projects) {
    const nav = project.manifest.nav
    const existing = sections.get(nav.section)
    const section = existing ?? {
      section: nav.section,
      order: nav.order,
      links: [],
    }
    if (existing != null && nav.order < existing.order) {
      section.order = nav.order
    }
    for (const item of nav.items) {
      const link: ProjectNavLink = {
        projectId: project.manifest.id,
        to: joinRoute(project.manifest.routeBase, item.path),
        label: item.label,
        icon: item.icon,
        end: item.end,
        documentTitle: item.documentTitle,
      }
      section.links.push(link)
    }
    sections.set(nav.section, section)
  }
  return [...sections.values()].sort((left, right) => {
    if (left.order !== right.order) return left.order - right.order
    if (left.section < right.section) return -1
    if (left.section > right.section) return 1
    return 0
  })
}

function joinRoute(routeBase: string, path: string): string {
  if (path === '') return routeBase
  return `${routeBase}/${path}`
}


export function documentTitleForPath(
  pathname: string,
  links: readonly ProjectNavLink[],
  discoveryError: string | null,
): string {
  if (pathname === '/settings') {
    return 'Settings · A7LAS';
  }
  const ranked = [...links].sort((left, right) => right.to.length - left.to.length);
  const match = ranked.find((link) =>
    link.end
      ? pathname === link.to
      : pathname === link.to || pathname.startsWith(`${link.to}/`),
  );
  if (match) {
    return `${match.documentTitle} · A7LAS`;
  }
  if (pathname === '/') {
    if (discoveryError) {
      return 'Projects could not be loaded · A7LAS';
    }
    if (links[0]) {
      return `${links[0].documentTitle} · A7LAS`;
    }
    return 'No projects enabled · A7LAS';
  }
  return 'Page Not Found · A7LAS';
}

