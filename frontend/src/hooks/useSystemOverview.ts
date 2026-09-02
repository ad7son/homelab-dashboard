import { useCallback, useEffect, useRef, useState } from 'react';
import { getSystemOverview } from '../services/api';
import type { ConnectionStatus, Overview } from '../types/system';

const POLL_INTERVAL_MS = 3000;

interface UseSystemOverviewResult {
  data: Overview | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  status: ConnectionStatus;
  refresh: () => void;
}

export function useSystemOverview(): UseSystemOverviewResult {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('offline');
  const failureCountRef = useRef(0);
  const mountedRef = useRef(true);
  const pollingRef = useRef(true);

  const fetchOverview = useCallback(async () => {
    try {
      const overview = await getSystemOverview();
      if (!mountedRef.current) return;

      setData(overview);
      setLastUpdated(new Date());
      setError(null);
      setStatus('online');
      failureCountRef.current = 0;
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
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  const refresh = useCallback(() => {
    void fetchOverview();
  }, [fetchOverview]);

  useEffect(() => {
    mountedRef.current = true;
    pollingRef.current = true;

    const poll = async () => {
      while (pollingRef.current) {
        await fetchOverview();
        if (!pollingRef.current) break;
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
    };

    void poll();

    return () => {
      mountedRef.current = false;
      pollingRef.current = false;
    };
  }, [fetchOverview]);

  return {
    data,
    loading,
    error,
    lastUpdated,
    status,
    refresh,
  };
}
