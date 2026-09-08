import { useCallback, useEffect, useRef, useState } from 'react';
import { getServices } from '../services/api';
import type { ServicesResponse } from '../types/services';

const POLL_INTERVAL_MS = 15_000;

interface UseServicesResult {
  data: ServicesResponse | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => void;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

export function useServices(): UseServicesResult {
  const [data, setData] = useState<ServicesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const mountedRef = useRef(true);
  const inFlightRef = useRef(false);
  const requestIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const hasDataRef = useRef(false);

  const fetchServices = useCallback(async () => {
    if (inFlightRef.current) {
      return;
    }

    inFlightRef.current = true;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    if (hasDataRef.current) {
      setRefreshing(true);
    }

    try {
      const response = await getServices(controller.signal);
      if (!mountedRef.current || requestId !== requestIdRef.current) {
        return;
      }

      hasDataRef.current = true;
      setData(response);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      if (isAbortError(err)) {
        return;
      }
      if (!mountedRef.current || requestId !== requestIdRef.current) {
        return;
      }

      const message =
        err instanceof Error ? err.message : 'Failed to fetch services';
      setError(message);
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
      inFlightRef.current = false;
      if (mountedRef.current && requestId === requestIdRef.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  const refresh = useCallback(() => {
    void fetchServices();
  }, [fetchServices]);

  useEffect(() => {
    let cancelled = false;
    mountedRef.current = true;

    const poll = async () => {
      while (!cancelled) {
        await fetchServices();
        if (cancelled) {
          break;
        }
        await delay(POLL_INTERVAL_MS);
      }
    };

    void poll();

    return () => {
      cancelled = true;
      mountedRef.current = false;
      abortRef.current?.abort();
      abortRef.current = null;
      inFlightRef.current = false;
    };
  }, [fetchServices]);

  return {
    data,
    loading,
    refreshing,
    error,
    lastUpdated,
    refresh,
  };
}
