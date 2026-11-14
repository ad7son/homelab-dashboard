import type { ReactNode } from 'react';
import { ProjectModuleError, validateManifest } from './manifest';
import type { ProjectManifest } from './manifest';

/** One page inside a project, relative to manifest.routeBase. */
export interface ProjectRouteDefinition {
  index?: boolean
  path?: string
  element: ReactNode
}

/**
 * Default export of projects/{id}/frontend/index.tsx.
 * A project may expose several pages, for example /system-monitor
 * and /system-monitor/health/system-monitor.
 */
export interface ProjectFrontendModule {
  routes: ProjectRouteDefinition[]
}

export interface DiscoveredProject {
  manifest: ProjectManifest
  loadFrontend: () => Promise<ProjectFrontendModule>
}


const MANIFEST_KEY = /\/projects\/([^/]+)\/project\.json$/;
const FRONTEND_KEY = /\/projects\/([^/]+)\/frontend\/index\.tsx$/;

interface FrontendLoader {
  (this: void): Promise<unknown>
}

export interface ProjectDiscoveryResult {
  projects: DiscoveredProject[]
  error: string | null
}

/**
 * Read manifests from projects/{id}/project.json.
 * Enabled projects are returned in nav.order, then id order.
 * The shell turns the result into routes. This function does not mount them.
 */
export function loadProjects(
  manifestModules: Record<string, unknown>,
  frontendModules: Record<string, unknown>,
): DiscoveredProject[] {
  const frontendById = indexFrontendLoaders(frontendModules)
  const errors: string[] = []
  const manifests: ProjectManifest[] = []

  for (const [key, raw] of Object.entries(manifestModules)) {
    const directoryName = projectIdFromKey(key, MANIFEST_KEY, 'project.json')
    try {
      manifests.push(validateManifest(unwrapModule(raw), directoryName, key))
    } catch (error) {
      errors.push(errorMessage(error))
    }
  }
  if (errors.length > 0) {
    throw new ProjectModuleError(errors.join('\n'))
  }

  const enabled = manifests.filter((manifest) => manifest.enabled)
  rejectDuplicates(enabled)
  for (const manifest of enabled) {
    if (!frontendById.has(manifest.id)) {
      errors.push(
        `project '${manifest.id}': missing frontend/index.tsx ` +
          `(expected projects/${manifest.id}/frontend/index.tsx)`,
      )
    }
  }
  if (errors.length > 0) {
    throw new ProjectModuleError(errors.join('\n'))
  }

  enabled.sort((left, right) => {
    if (left.nav.order !== right.nav.order) {
      return left.nav.order - right.nav.order
    }
    if (left.id < right.id) return -1
    if (left.id > right.id) return 1
    return 0
  })

  return enabled.map((manifest) => {
    const load = frontendById.get(manifest.id)
    if (load == null) {
      throw new ProjectModuleError(
        `project '${manifest.id}': missing frontend/index.tsx`,
      )
    }
    return {
      manifest,
      loadFrontend: () =>
        load().then((imported) => unwrapFrontendModule(imported, manifest.id)),
    }
  })
}

/** Load projects for the shell. A discovery failure is reported, not hidden. */
export function loadDiscoveredProjects(
  manifests?: Record<string, unknown>,
  frontends?: Record<string, unknown>,
): ProjectDiscoveryResult {
  try {
    // Vite 需要字面值路徑；延後到呼叫時收集，純載入邏輯可獨立驗證。
    const manifestModules = manifests ?? import.meta.glob('../../../projects/*/project.json', {
      eager: true, import: 'default',
    });
    const frontendModules = frontends ?? import.meta.glob('../../../projects/*/frontend/index.tsx');
    return { projects: loadProjects(manifestModules, frontendModules), error: null }
  } catch (error) {
    console.error(error)
    return {
      projects: [],
      error: error instanceof Error ? error.message : String(error),
    }
  }
}

function indexFrontendLoaders(
  modules: Record<string, unknown>,
): Map<string, FrontendLoader> {
  const loaders = new Map<string, FrontendLoader>()
  for (const [key, loader] of Object.entries(modules)) {
    if (typeof loader !== 'function') {
      throw new ProjectModuleError(
        `project frontend entry '${key}' was not loaded as a lazy module`,
      )
    }
    const directoryName = projectIdFromKey(key, FRONTEND_KEY, 'frontend/index.tsx')
    loaders.set(directoryName, loader as FrontendLoader)
  }
  return loaders
}

function projectIdFromKey(key: string, pattern: RegExp, label: string): string {
  const match = key.replaceAll('\\', '/').match(pattern)
  const directoryName = match?.[1]
  if (directoryName == null || directoryName === '') {
    throw new ProjectModuleError(
      `unable to read project id from ${label} path '${key}'`,
    )
  }
  return directoryName
}

function rejectDuplicates(manifests: readonly ProjectManifest[]): void {
  const ids = new Map<string, string>()
  const routes = new Map<string, string>()
  const prefixes = new Map<string, string>()
  for (const manifest of manifests) {
    claim(ids, manifest.id, manifest.id, 'id')
    claim(routes, manifest.routeBase, manifest.id, 'routeBase')
    for (const legacyRoute of manifest.legacyRouteBases) {
      claim(routes, legacyRoute, manifest.id, 'legacyRouteBases')
    }
    claim(prefixes, manifest.apiPrefix, manifest.id, 'apiPrefix')
    if (manifest.legacyApiPrefix != null) {
      claim(prefixes, manifest.legacyApiPrefix, manifest.id, 'legacyApiPrefix')
    }
  }
}

function claim(
  seen: Map<string, string>,
  value: string,
  projectId: string,
  fieldName: string,
): void {
  const previous = seen.get(value)
  if (previous != null) {
    throw new ProjectModuleError(
      `duplicate ${fieldName} '${value}' used by projects '${previous}' and '${projectId}'`,
    )
  }
  seen.set(value, projectId)
}

function unwrapFrontendModule(
  imported: unknown,
  projectId: string,
): ProjectFrontendModule {
  const candidate = unwrapModule(imported)
  if (
    candidate == null ||
    typeof candidate !== 'object' ||
    !('routes' in candidate) ||
    !Array.isArray((candidate as { routes: unknown }).routes)
  ) {
    throw new ProjectModuleError(
      `project '${projectId}': frontend/index.tsx must default-export { routes }`,
    )
  }
  return candidate as ProjectFrontendModule
}

function unwrapModule(value: unknown): unknown {
  if (
    value != null &&
    typeof value === 'object' &&
    'default' in value &&
    !('schemaVersion' in value)
  ) {
    return (value as { default: unknown }).default
  }
  return value
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error)
}
