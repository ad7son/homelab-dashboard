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
