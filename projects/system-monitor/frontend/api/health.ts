import { ApiError, requestJson } from './client';

/** 狀態與原始證據由平台依同一份事件快照判定，前端只負責呈現與統計。 */
export type FeatureStatus = 'healthy' | 'issues' | 'unavailable' | 'unknown';
export interface FeatureHealth {
  id: string;
  name: string;
  description: string;
  criteria: string;
  status: FeatureStatus;
  message: string;
  checked_at_ms: number;
  last_success_at_ms: number | null;
  duration_ms: number | null;
  source: string;
  raw_data: unknown;
  error: { type: string; message: string; traceback: string | null } | null;
}
export interface ProjectHealthReport {
  project_id: string;
  project_name: string;
  checked_at_ms: number;
  features: FeatureHealth[];
}

function nullableNumber(value: unknown): boolean {
  return value === null || (typeof value === 'number' && Number.isFinite(value) && value >= 0);
}

function validFeature(value: unknown): value is FeatureHealth {
  if (!value || typeof value !== 'object') return false;
  const feature = value as FeatureHealth;
  return ['id', 'name', 'description', 'criteria', 'message', 'source'].every(
    (key) => typeof feature[key as keyof FeatureHealth] === 'string',
  ) && ['healthy', 'issues', 'unavailable', 'unknown'].includes(feature.status)
    && Number.isFinite(feature.checked_at_ms)
    && nullableNumber(feature.last_success_at_ms) && nullableNumber(feature.duration_ms)
    && 'raw_data' in feature
    && (feature.error === null || (typeof feature.error === 'object'
      && typeof feature.error.type === 'string' && typeof feature.error.message === 'string'
      && (feature.error.traceback === null || typeof feature.error.traceback === 'string')));
}

function validReport(value: unknown): value is ProjectHealthReport {
  if (!value || typeof value !== 'object') return false;
  const report = value as ProjectHealthReport;
  return typeof report.project_id === 'string' && typeof report.project_name === 'string'
    && Number.isFinite(report.checked_at_ms) && Array.isArray(report.features)
    && report.features.every(validFeature);
}

/** 總覽查詢全部專案；指定 ID 則回傳單一專案，統一包成清單。 */
export async function getProjectHealth(projectId?: string, signal?: AbortSignal): Promise<ProjectHealthReport[]> {
  try {
    const path = projectId ? `/api/project-health/${encodeURIComponent(projectId)}` : '/api/project-health';
    const body = await requestJson(path, { signal });
    const reports = projectId ? [body] : (body as { projects?: unknown } | null)?.projects;
    if (!Array.isArray(reports) || !reports.every(validReport) ||
        (projectId && (reports.length !== 1 || reports[0].project_id !== projectId))) {
      throw new ApiError('健康報告回應格式不正確');
    }
    return reports;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) throw new ApiError('找不到此專案。', 404);
    throw error;
  }
}
