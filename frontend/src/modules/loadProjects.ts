import { isAllowedProjectIcon } from './icons'
import type {
  DiscoveredProject,
  ProjectFrontendModule,
  ProjectManifest,
  ProjectNavLink,
  ProjectNavSection,
} from './types'

/**
 * Vite rewrites these literals at build time. Patterns must stay relative
 * string literals and use forward slashes, including on Windows.
 * An empty projects directory produces an empty map.
 */
const manifestModules = import.meta.glob('../../../projects/*/project.json', {
  eager: true,
  import: 'default',
})

const frontendModules = import.meta.glob(
  '../../../projects/*/frontend/index.tsx',
)

const MANIFEST_KEY = /\/projects\/([^/]+)\/project\.json$/
const FRONTEND_KEY = /\/projects\/([^/]+)\/frontend\/index\.tsx$/

const ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const PACKAGE_PATTERN = /^[a-z][a-z0-9_]*$/
const ROUTE_BASE_PATTERN =
  /^\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*$/
const API_PREFIX_PATTERN =
  /^\/api\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*$/
const NAV_PATH_PATTERN =
  /^(?:[a-z0-9]+(?:-[a-z0-9]+)*)(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*$/

const RESERVED_ROUTE_BASES = ['/settings']
const RESERVED_API_PREFIXES = ['/api/health']
const LEGACY_API_ROOT = '/api'
const LEGACY_API_ROOT_PROJECT_ID = 'system-monitor'
const MANIFEST_FIELDS = new Set([
  'schemaVersion',
  'id',
  'name',
  'description',
  'pythonPackage',
  'routeBase',
  'apiPrefix',
  'legacyRouteBases',
  'legacyApiPrefix',
  'enabled',
  'nav',
])

const PYTHON_KEYWORDS = new Set([
  'false',
  'none',
  'true',
  'and',
  'as',
  'assert',
  'async',
  'await',
  'break',
  'class',
  'continue',
  'def',
  'del',
  'elif',
  'else',
  'except',
  'finally',
  'for',
  'from',
  'global',
  'if',
  'import',
  'in',
  'is',
  'lambda',
  'nonlocal',
  'not',
  'or',
  'pass',
  'raise',
  'return',
  'try',
  'while',
  'with',
  'yield',
])

export class ProjectModuleError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ProjectModuleError'
  }
}

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
export function loadProjects(): DiscoveredProject[] {
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
export function loadDiscoveredProjects(): ProjectDiscoveryResult {
  try {
    return { projects: loadProjects(), error: null }
  } catch (error) {
    console.error(error)
    return {
      projects: [],
      error: error instanceof Error ? error.message : String(error),
    }
  }
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

function validateManifest(
  raw: unknown,
  directoryName: string,
  source: string,
): ProjectManifest {
  if (raw == null || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new ProjectModuleError(
      `${source}: project manifest must be a JSON object`,
    )
  }
  const record = raw as Record<string, unknown>
  const unknownField = Object.keys(record).find((key) => !MANIFEST_FIELDS.has(key))
  if (unknownField != null) {
    throw new ProjectModuleError(`${source}: unknown manifest field '${unknownField}'`)
  }
  const schemaVersion = record.schemaVersion
  if (typeof schemaVersion !== 'number' || !Number.isInteger(schemaVersion)) {
    throw new ProjectModuleError(`${source}: schemaVersion must be the integer 1`)
  }
  if (schemaVersion !== 1) {
    throw new ProjectModuleError(`${source}: schemaVersion must be 1`)
  }
  const id = requiredString(record.id, source, 'id')
  if (!ID_PATTERN.test(id)) {
    throw new ProjectModuleError(
      `${source}: id must be lowercase kebab-case (for example 'system-monitor')`,
    )
  }
  if (id !== directoryName) {
    throw new ProjectModuleError(
      `${source}: id '${id}' does not match project directory name '${directoryName}'`,
    )
  }
  const name = requiredString(record.name, source, 'name')
  const description = record.description == null ? '' : record.description
  if (typeof description !== 'string') {
    throw new ProjectModuleError(`${source}: description must be a string`)
  }
  const pythonPackage = requiredString(record.pythonPackage, source, 'pythonPackage')
  if (!PACKAGE_PATTERN.test(pythonPackage) || PYTHON_KEYWORDS.has(pythonPackage)) {
    throw new ProjectModuleError(
      `${source}: pythonPackage must be a lowercase Python package name ` +
        "(for example 'system_monitor')",
    )
  }
  const routeBase = requiredString(record.routeBase, source, 'routeBase')
  validatePublicRoute(routeBase, source, 'routeBase')
  const apiPrefix = requiredString(record.apiPrefix, source, 'apiPrefix')
  validateApiPrefix(apiPrefix, source, 'apiPrefix')
  const legacyRouteBases = validateLegacyRouteBases(record.legacyRouteBases, source)
  const legacyApiPrefix = validateLegacyApiPrefix(
    record.legacyApiPrefix,
    id,
    apiPrefix,
    source,
  )
  assertNoRouteOverlap(routeBase, legacyRouteBases, source)
  const enabled = record.enabled == null ? true : record.enabled
  if (typeof enabled !== 'boolean') {
    throw new ProjectModuleError(`${source}: enabled must be a boolean`)
  }
  const nav = validateNav(record.nav, source)
  return {
    schemaVersion: 1,
    id,
    name,
    description,
    pythonPackage,
    routeBase,
    apiPrefix,
    legacyRouteBases,
    legacyApiPrefix,
    enabled,
    nav,
  }
}

function validatePublicRoute(route: string, source: string, fieldName: string): void {
  if (
    containsUnsafePath(route) ||
    route === '/' ||
    isReservedPath(route, RESERVED_ROUTE_BASES) ||
    !ROUTE_BASE_PATTERN.test(route)
  ) {
    throw new ProjectModuleError(
      `${source}: ${fieldName} must be an absolute kebab-case path such as ` +
        "'/system-monitor' and cannot be '/' or '/settings'",
    )
  }
}

function validateApiPrefix(apiPrefix: string, source: string, fieldName: string): void {
  if (apiPrefix === '/api' || apiPrefix === '/api/') {
    throw new ProjectModuleError(
      `${source}: ${fieldName} must name a project namespace and cannot be '/api'`,
    )
  }
  if (isReservedPath(apiPrefix, RESERVED_API_PREFIXES)) {
    throw new ProjectModuleError(
      `${source}: ${fieldName} '/api/health' is reserved by the platform`,
    )
  }
  if (containsUnsafePath(apiPrefix) || !API_PREFIX_PATTERN.test(apiPrefix)) {
    throw new ProjectModuleError(
      `${source}: ${fieldName} must start with '/api/' and use kebab-case segments ` +
        "such as '/api/system-monitor'",
    )
  }
}

function validateLegacyRouteBases(raw: unknown, source: string): string[] {
  if (raw == null) return []
  if (!Array.isArray(raw)) {
    throw new ProjectModuleError(`${source}: legacyRouteBases must be an array of absolute paths`)
  }
  const routes = raw.map((item) => {
    if (typeof item !== 'string') {
      throw new ProjectModuleError(`${source}: legacyRouteBases must contain only strings`)
    }
    validatePublicRoute(item, source, 'legacyRouteBases')
    return item
  })
  if (new Set(routes).size !== routes.length) {
    throw new ProjectModuleError(`${source}: legacyRouteBases must not contain duplicate paths`)
  }
  return routes
}

function validateLegacyApiPrefix(
  raw: unknown,
  projectId: string,
  apiPrefix: string,
  source: string,
): string | null {
  if (raw == null) return null
  if (typeof raw !== 'string') {
    throw new ProjectModuleError(`${source}: legacyApiPrefix must be a string`)
  }
  if (raw === apiPrefix) {
    throw new ProjectModuleError(`${source}: legacyApiPrefix must differ from apiPrefix`)
  }
  if (raw === LEGACY_API_ROOT) {
    if (projectId !== LEGACY_API_ROOT_PROJECT_ID) {
      throw new ProjectModuleError(
        `${source}: legacyApiPrefix '/api' is reserved for project 'system-monitor'`,
      )
    }
    return raw
  }
  validateApiPrefix(raw, source, 'legacyApiPrefix')
  return raw
}

function assertNoRouteOverlap(
  routeBase: string,
  legacyRouteBases: readonly string[],
  source: string,
): void {
  const labeled: Array<[string, string]> = [['routeBase', routeBase]]
  for (const legacy of legacyRouteBases) {
    labeled.push(['legacyRouteBases', legacy])
  }
  for (let index = 0; index < labeled.length; index += 1) {
    for (let other = index + 1; other < labeled.length; other += 1) {
      const [leftField, left] = labeled[index]
      const [rightField, right] = labeled[other]
      if (left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`)) {
        throw new ProjectModuleError(
          `${source}: ${leftField} '${left}' overlaps ${rightField} '${right}'`,
        )
      }
    }
  }
}

function validateNav(raw: unknown, source: string): ProjectManifest['nav'] {
  if (raw == null || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new ProjectModuleError(`${source}: nav must be an object`)
  }
  const nav = raw as Record<string, unknown>
  const section = requiredString(nav.section, source, 'nav.section')
  if (typeof nav.order !== 'number' || !Number.isInteger(nav.order)) {
    throw new ProjectModuleError(`${source}: nav.order must be an integer`)
  }
  if (!Array.isArray(nav.items) || nav.items.length === 0) {
    throw new ProjectModuleError(`${source}: nav.items must contain at least one item`)
  }
  const seen = new Set<string>()
  const items = nav.items.map((item) => {
    if (item == null || typeof item !== 'object' || Array.isArray(item)) {
      throw new ProjectModuleError(`${source}: nav.items entries must be objects`)
    }
    const record = item as Record<string, unknown>
    if (typeof record.path !== 'string') {
      throw new ProjectModuleError(`${source}: nav.items.path must be a string`)
    }
    if (
      record.path !== '' &&
      (record.path.startsWith('/') ||
        containsUnsafePath(record.path) ||
        !NAV_PATH_PATTERN.test(record.path))
    ) {
      throw new ProjectModuleError(
        `${source}: nav path '${record.path}' must be a relative kebab-case path`,
      )
    }
    if (seen.has(record.path)) {
      throw new ProjectModuleError(
        `${source}: duplicate nav path '${record.path}'`,
      )
    }
    seen.add(record.path)
    const label = requiredString(record.label, source, 'nav.items.label')
    if (typeof record.icon !== 'string' || !isAllowedProjectIcon(record.icon)) {
      throw new ProjectModuleError(
        `${source}: nav icon '${String(record.icon)}' is not in the allowed icon list`,
      )
    }
    const end = record.end == null ? false : record.end
    if (typeof end !== 'boolean') {
      throw new ProjectModuleError(`${source}: nav.items.end must be a boolean`)
    }
    const documentTitle = requiredString(
      record.documentTitle,
      source,
      'nav.items.documentTitle',
    )
    return {
      path: record.path,
      label,
      icon: record.icon,
      end,
      documentTitle,
    }
  })
  return { section, order: nav.order, items }
}

function rejectDuplicates(manifests: readonly ProjectManifest[]): void {
  const ids = new Map<string, string>()
  const routes = new Map<string, string>()
  const prefixes = new Map<string, string>()
  const packages = new Map<string, string>()
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
    claim(packages, manifest.pythonPackage, manifest.id, 'pythonPackage')
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

function joinRoute(routeBase: string, path: string): string {
  if (path === '') return routeBase
  return `${routeBase}/${path}`
}

function requiredString(value: unknown, source: string, fieldName: string): string {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new ProjectModuleError(`${source}: ${fieldName} must be a non-empty string`)
  }
  return value
}

function containsUnsafePath(value: string): boolean {
  if (value.includes('\\') || value.includes('\0') || value.includes('%')) {
    return true
  }
  return value.split('/').some((segment) => segment === '.' || segment === '..')
}

function isReservedPath(value: string, reserved: readonly string[]): boolean {
  return reserved.some((item) => value === item || value.startsWith(`${item}/`))
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error)
}
