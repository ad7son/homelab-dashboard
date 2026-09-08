import type { Overview } from '../types/system';
import type {
  HistoricalMetricsResponse,
  HistoricalRange,
} from '../types/history';
import type { ServicesResponse } from '../types/services';

const REQUEST_TIMEOUT_MS = 5000;
const HISTORY_REQUEST_TIMEOUT_MS = 15000;
const SERVICES_REQUEST_TIMEOUT_MS = 5000;

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

export async function getSystemOverview(): Promise<Overview> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch('/api/overview', {
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiError(`Request failed with status ${response.status}`);
    }

    return (await response.json()) as Overview;
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
      `/api/history?range=${encodeURIComponent(range)}`,
      { signal: controller.signal },
    );

    if (!response.ok) {
      throw new ApiError(`Request failed with status ${response.status}`);
    }

    return (await response.json()) as HistoricalMetricsResponse;
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

export async function getServices(
  externalSignal?: AbortSignal,
): Promise<ServicesResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    SERVICES_REQUEST_TIMEOUT_MS,
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
    const response = await fetch('/api/services', {
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiError(`Request failed with status ${response.status}`);
    }

    return (await response.json()) as ServicesResponse;
  } catch (error) {
    if (isAbortError(error)) {
      if (externalSignal?.aborted) {
        throw error;
      }
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
    externalSignal?.removeEventListener('abort', abortFromExternal);
  }
}
