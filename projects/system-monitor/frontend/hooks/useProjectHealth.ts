import { useCallback, useEffect, useState } from 'react';
import type { ProjectHealthReport } from '../types/health';

function validReport(value: unknown): value is ProjectHealthReport {
  if (!value || typeof value !== 'object') return false;
  const report = value as ProjectHealthReport;
  return typeof report.project_id === 'string' && typeof report.project_name === 'string'
    && Number.isFinite(report.checked_at_ms) && Array.isArray(report.features)
    && report.features.every((feature) => typeof feature.id === 'string'
      && ['healthy', 'issues', 'unavailable', 'unknown'].includes(feature.status));
}

/** 總覽查詢全部專案；詳情維持手動更新的同一份證據快照。 */
export function useProjectHealth(refreshToken = 0, projectId?: string, poll = true) {
  const [projects, setProjects] = useState<ProjectHealthReport[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const refresh = useCallback(() => setAttempt((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    let pending = false;
    let controller: AbortController | null = null;
    const load = async () => {
      if (pending) return;
      pending = true;
      setLoading(true);
      controller = new AbortController();
      const request = controller;
      const timeout = window.setTimeout(() => request.abort(), 15_000);
      try {
        const path = projectId ? `/api/project-health/${encodeURIComponent(projectId)}` : '/api/project-health';
        const response = await fetch(path, { signal: request.signal, cache: 'no-store' });
        if (!response.ok) throw new Error(response.status === 404 ? '找不到此專案。' : `健康報告 API 回傳 HTTP ${response.status}`);
        const body: unknown = await response.json();
        const reports = projectId ? [body] : (body as { projects?: unknown })?.projects;
        if (!Array.isArray(reports) || !reports.every(validReport) ||
            (projectId && (reports.length !== 1 || reports[0].project_id !== projectId))) {
          throw new Error('健康報告回應格式不正確');
        }
        if (active) { setProjects(reports); setError(null); }
      } catch (failure) {
        if (active) setError(request.signal.aborted ? '健康報告超過 15 秒，請重試。' : failure instanceof Error ? failure.message : '無法取得健康報告');
      } finally {
        window.clearTimeout(timeout);
        pending = false;
        if (active) setLoading(false);
      }
    };
    void load();
    const timer = poll ? window.setInterval(() => { void load(); }, 30_000) : null;
    return () => { active = false; controller?.abort(); if (timer !== null) window.clearInterval(timer); };
  }, [refreshToken, attempt, projectId, poll]);

  return {
    projects, data: projectId ? projects.find((report) => report.project_id === projectId) ?? null : null,
    error, loading, refresh,
  };
}
