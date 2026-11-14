/** 共用 HTTP 請求；資料驗證由各 API 模組負責。 */
export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

export async function requestJson(
  path: string,
  { signal, timeoutMs = 15000 }: RequestOptions = {},
): Promise<unknown> {
  const controller = new AbortController();
  let timedOut = false;
  const abort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  try {
    if (controller.signal.aborted) throw new DOMException('Aborted', 'AbortError');
    const response = await fetch(path, { signal: controller.signal, cache: 'no-store' });
    if (!response.ok) throw new ApiError(`Request failed with status ${response.status}`, response.status);
    return await response.json();
  } catch (error) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    if (timedOut) throw new ApiError(`Request timed out after ${timeoutMs / 1000} seconds`);
    if (error instanceof ApiError) throw error;
    throw new ApiError(error instanceof Error ? error.message : 'Unknown request error');
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}
