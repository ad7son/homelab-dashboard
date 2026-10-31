import projectManifest from '../project.json'

export interface ShowcaseInfo {
  id: string
  name: string
  description: string
  status: 'ok'
  message: string
}

const REQUEST_TIMEOUT_MS = 5000

function readApiPrefix(manifest: { apiPrefix?: unknown }): string {
  if (typeof manifest.apiPrefix !== 'string' || manifest.apiPrefix.length === 0) {
    throw new Error('project-showcase project.json is missing apiPrefix')
  }
  return manifest.apiPrefix
}

export const SHOWCASE_API_PREFIX = readApiPrefix(projectManifest)

export class ShowcaseApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ShowcaseApiError'
  }
}

function isShowcaseInfo(value: unknown): value is ShowcaseInfo {
  if (value == null || typeof value !== 'object') {
    return false
  }
  const record = value as Record<string, unknown>
  return (
    typeof record.id === 'string' &&
    typeof record.name === 'string' &&
    typeof record.description === 'string' &&
    record.status === 'ok' &&
    typeof record.message === 'string'
  )
}

export async function getShowcaseInfo(signal: AbortSignal): Promise<ShowcaseInfo> {
  const response = await fetch(`${SHOWCASE_API_PREFIX}/info`, { signal })
  if (!response.ok) {
    throw new ShowcaseApiError(`Request failed with status ${response.status}`)
  }
  const payload: unknown = await response.json()
  if (!isShowcaseInfo(payload)) {
    throw new ShowcaseApiError('Response did not match the showcase info shape')
  }
  return payload
}

export function showcaseRequestTimeoutMs(): number {
  return REQUEST_TIMEOUT_MS
}
