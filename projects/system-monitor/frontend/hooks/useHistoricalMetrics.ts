import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, getHistoricalMetrics } from '../api';
import type {
  HistoricalMetricsResponse,
  HistoricalRange,
} from '../types/history';

const DEFAULT_RANGE: HistoricalRange = '1h';
const HISTORY_REFRESH_INTERVAL_MS = 30_000;

interface UseHistoricalMetricsOptions {
  enabled: boolean;
  refreshToken: number;
}

interface UseHistoricalMetricsResult {
  range: HistoricalRange;
  setRange: (range: HistoricalRange) => void;
  data: HistoricalMetricsResponse | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

export function useHistoricalMetrics({
  enabled,
  refreshToken,
}: UseHistoricalMetricsOptions): UseHistoricalMetricsResult {
  const [range, setRangeState] = useState<HistoricalRange>(DEFAULT_RANGE);
  const [data, setData] = useState<HistoricalMetricsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  const setRange = useCallback((nextRange: HistoricalRange) => {
    setRangeState(nextRange);
    setData(null);
    setError(null);
  }, []);

  const retry = useCallback(() => {
    setReloadToken((token) => token + 1);
  }, []);

  // 即時與歷史資料皆由同一採集器寫入；開啟 History 時定時查詢新樣本。
  // 離開歷史模式或頁面後清除計時器，避免背景持續發送查詢。
  useEffect(() => {
    if (!enabled) return;
    const timer = window.setInterval(retry, HISTORY_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [enabled, retry]);

  useEffect(() => {
    if (!enabled) {
      abortRef.current?.abort();
      abortRef.current = null;
      return;
    }

    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    void (async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await getHistoricalMetrics(range, controller.signal);
        if (
          requestId !== requestIdRef.current ||
          controller.signal.aborted
        ) {
          return;
        }
        setData(response);
        setError(null);
      } catch (err) {
        if (
          requestId !== requestIdRef.current ||
          controller.signal.aborted ||
          isAbortError(err)
        ) {
          return;
        }
        setError(
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Failed to load historical metrics',
        );
      } finally {
        if (
          requestId === requestIdRef.current &&
          !controller.signal.aborted
        ) {
          setLoading(false);
        }
      }
    })();

    return () => {
      controller.abort();
    };
  }, [enabled, range, reloadToken, refreshToken]);

  return {
    range,
    setRange,
    data,
    loading,
    error,
    retry,
  };
}
