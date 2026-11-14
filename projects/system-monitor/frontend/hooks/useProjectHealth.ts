import { useEffect, useState } from 'react';
import projectManifest from '../../project.json';
import type { ProjectHealthReport } from '../types/health';

// 健康檢測等待共用 log 系統，保留 UI 與串接程式但不呼叫已移除的 API。
const PROJECT_HEALTH_AVAILABLE = false;

/**
 * 首次載入後每 30 秒更新整份報告，手動刷新強制重新檢查。
 * 失敗保留上次報告並明確提示，取消請求後不更新狀態。
 * 詳情頁暫停自動更新，讓排錯時的狀態與原始證據維持同一快照。
 */
export function useProjectHealth(refreshToken = 0, enabled = true, poll = true) {
  const [data, setData] = useState<ProjectHealthReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(PROJECT_HEALTH_AVAILABLE && enabled);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!enabled || !PROJECT_HEALTH_AVAILABLE) return;
    let active = true;
    let pending = false;
    let controller: AbortController | null = null;
    const load = async (force: boolean) => {
      if (pending) return;
      pending = true;
      setLoading(true);
      controller = new AbortController();
      const timeout = window.setTimeout(() => controller?.abort(), 15_000);
      try {
        const response = await fetch(`${projectManifest.apiPrefix}/feature-health?force=${force}`, {
          signal: controller.signal, cache: 'no-store',
        });
        if (!response.ok) throw new Error(`健康檢查 API 回傳 HTTP ${response.status}`);
        const report = await response.json() as ProjectHealthReport;
        if (report.project_id !== projectManifest.id || !Array.isArray(report.features)) {
          throw new Error('健康檢查回應格式或專案識別碼不正確');
        }
        if (active) { setData(report); setError(null); }
      } catch (failure) {
        if (active) setError(controller.signal.aborted ? '健康檢查超過 15 秒，請重試。' : failure instanceof Error ? failure.message : '無法取得健康檢查');
      } finally {
        window.clearTimeout(timeout);
        pending = false;
        if (active) setLoading(false);
      }
    };
    void load(attempt > 0 || refreshToken > 0);
    const interval = poll ? window.setInterval(() => { void load(false); }, 30_000) : null;
    return () => { active = false; controller?.abort(); if (interval !== null) window.clearInterval(interval); };
  }, [refreshToken, attempt, enabled, poll]);
  return { available: PROJECT_HEALTH_AVAILABLE, data, error, loading, refresh: () => setAttempt((value) => value + 1) };
}
