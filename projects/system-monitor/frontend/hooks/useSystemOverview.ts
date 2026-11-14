import { useCallback, useEffect, useRef, useState } from 'react';
import { getSystemOverview } from '../api';
import type { ConnectionStatus, Overview } from '../types/system';
import { sampleStatus } from '../utils/overview';
import { useRealtimeSamples } from './useRealtimeSamples';

const POLL_INTERVAL_MS = 3000;

export function useSystemOverview() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('offline');
  const failureCount = useRef(0);
  const mounted = useRef(false);
  const request = useRef<AbortController | null>(null);
  const { samples, appendSample } = useRealtimeSamples();

  const fetchOverview = useCallback(async () => {
    if (!mounted.current || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    try {
      const overview = await getSystemOverview(controller.signal);
      if (controller.signal.aborted || !mounted.current) return;
      setData(overview);
      setError(null);
      setStatus(sampleStatus(overview.timestamp_ms));
      failureCount.current = 0;
      appendSample(overview);
    } catch (failure) {
      if (controller.signal.aborted || !mounted.current) return;
      setError(failure instanceof Error ? failure.message : '無法取得主機資訊');
      failureCount.current += 1;
      setStatus(failureCount.current >= 3 ? 'offline' : 'unstable');
    } finally {
      if (request.current === controller) {
        request.current = null;
        if (mounted.current) setLoading(false);
      }
    }
  }, [appendSample]);

  useEffect(() => {
    mounted.current = true;
    void fetchOverview();
    const timer = window.setInterval(() => { void fetchOverview(); }, POLL_INTERVAL_MS);
    return () => {
      mounted.current = false;
      window.clearInterval(timer);
      request.current?.abort();
      request.current = null;
    };
  }, [fetchOverview]);

  useEffect(() => {
    if (!data) return;
    const timer = window.setInterval(() => {
      setStatus((current) => current === 'online' || current === 'stale'
        ? sampleStatus(data.timestamp_ms) : current);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [data]);

  return {
    data, loading, error, status, samples,
    lastUpdated: data ? new Date(data.timestamp_ms) : null,
    refresh: fetchOverview,
  };
}
