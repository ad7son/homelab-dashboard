import { parseOverview } from './utils/overview';
import type { Overview } from './types/system';
import type {
  HistoricalMetricsResponse,
  HistoricalRange,
} from './types/history';

import projectManifest from '../project.json'

function readApiPrefix(manifest: { apiPrefix?: unknown }): string {
  if (typeof manifest.apiPrefix !== 'string' || manifest.apiPrefix.length === 0) {
    throw new Error('system-monitor project.json is missing apiPrefix')
  }
  return manifest.apiPrefix
}

const API_PREFIX = readApiPrefix(projectManifest)

const REQUEST_TIMEOUT_MS = 5000;
const HISTORY_REQUEST_TIMEOUT_MS = 15000;

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

export async function getSystemOverview(externalSignal?: AbortSignal): Promise<Overview> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (externalSignal?.aborted) controller.abort();
  externalSignal?.addEventListener('abort', abort);
  const timeoutId = setTimeout(abort, REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_PREFIX}/overview`, {
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiError(response.status === 503
        ? '尚無可用的監測資料，請確認採集器與資料庫是否正常。'
        : `Request failed with status ${response.status}`);
    }

    return parseOverview(await response.json());
  } catch (error) {
    if (isAbortError(error)) {
      throw new ApiError('Request timed out after 5 seconds');
    }
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Unknown request error',
    );
  } finally {
    clearTimeout(timeoutId);
    externalSignal?.removeEventListener('abort', abort);
  }
}

export async function getHistoricalMetrics(
  range: HistoricalRange,
  externalSignal?: AbortSignal,
): Promise<HistoricalMetricsResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    HISTORY_REQUEST_TIMEOUT_MS,
  );

  const abortFromExternal = () => {
    controller.abort();
  };

  if (externalSignal) {
    if (externalSignal.aborted) {
      clearTimeout(timeoutId);
      throw new DOMException('Aborted', 'AbortError');
    }
    externalSignal.addEventListener('abort', abortFromExternal);
  }

  try {
    const response = await fetch(
      `${API_PREFIX}/history?range=${encodeURIComponent(range)}`,
      { signal: controller.signal },
    );

    if (!response.ok) {
      throw new ApiError(response.status === 503
        ? '尚無可用的監測資料，請確認採集器與資料庫是否正常。'
        : `Request failed with status ${response.status}`);
    }

    const data = await response.json() as HistoricalMetricsResponse;
    if (!Array.isArray(data.samples) || !Number.isFinite(data.start_ms) ||
        !Number.isFinite(data.end_ms) || !Number.isFinite(data.interval_seconds) ||
        data.interval_seconds <= 0) {
      throw new ApiError('歷史資料回應格式不正確');
    }
    return data;
  } catch (error) {
    if (isAbortError(error)) {
      if (externalSignal?.aborted) {
        throw error;
      }
      throw new ApiError('Request timed out after 15 seconds');
    }
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Unknown request error',
    );
  } finally {
    clearTimeout(timeoutId);
    externalSignal?.removeEventListener('abort', abortFromExternal);
  }
}
