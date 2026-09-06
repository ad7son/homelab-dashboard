import { useCallback, useEffect, useRef, useState } from 'react';
import { getSystemOverview } from '../services/api';
import type { RealtimeSample } from '../types/realtime';
import type { ConnectionStatus, Overview } from '../types/system';
import { useRealtimeSamples } from './useRealtimeSamples';

const POLL_INTERVAL_MS = 3000;

interface UseSystemOverviewResult {
  data: Overview | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  status: ConnectionStatus;
  refresh: () => void;
  samples: RealtimeSample[];
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export function useSystemOverview(): UseSystemOverviewResult {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('offline');
  const failureCountRef = useRef(0);
  const mountedRef = useRef(true);
  const inFlightRef = useRef(false);
  const { samples, appendSample } = useRealtimeSamples();

  const fetchOverview = useCallback(async () => {
    if (inFlightRef.current) {
      return;
    }

    inFlightRef.current = true;

    try {
      const overview = await getSystemOverview();
      if (!mountedRef.current) return;

      const updatedAt = new Date();
      setData(overview);
      setLastUpdated(updatedAt);
      setError(null);
      setStatus('online');
      failureCountRef.current = 0;
      appendSample(overview, updatedAt.getTime());
    } catch (err) {
      if (!mountedRef.current) return;

      const message =
        err instanceof Error ? err.message : 'Failed to fetch system overview';
      setError(message);
      failureCountRef.current += 1;

      if (failureCountRef.current >= 3) {
        setStatus('offline');
      } else {
        setStatus('unstable');
      }
    } finally {
      inFlightRef.current = false;
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [appendSample]);

  const refresh = useCallback(() => {
    void fetchOverview();
  }, [fetchOverview]);

  useEffect(() => {
    let cancelled = false;
    mountedRef.current = true;

    const poll = async () => {
      while (!cancelled) {
        await fetchOverview();
        if (cancelled) break;
        await delay(POLL_INTERVAL_MS);
      }
    };

    void poll();

    return () => {
      cancelled = true;
      mountedRef.current = false;
    };
  }, [fetchOverview]);

  return {
    data,
    loading,
    error,
    lastUpdated,
    status,
    refresh,
    samples,
  };
}
