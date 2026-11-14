import { useCallback, useEffect, useState } from 'react';
import { getProjectHealth, type ProjectHealthReport } from '../api/health';

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
      try {
        const reports = await getProjectHealth(projectId, request.signal);
        if (active) { setProjects(reports); setError(null); }
      } catch (failure) {
        if (active) setError(request.signal.aborted ? '健康報告超過 15 秒，請重試。' : failure instanceof Error ? failure.message : '無法取得健康報告');
      } finally {
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
