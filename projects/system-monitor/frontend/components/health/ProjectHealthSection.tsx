import { Activity, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { SectionHeader } from '@shell/components/layout/SectionHeader';
import projectManifest from '../../../project.json';
import { HealthSummary } from './HealthSummary';
import { summarizeFeatures } from './healthData';
import type { useProjectHealth } from '../../hooks/useProjectHealth';

/** 總覽只呈現專案摘要；完整功能列表移至可直接開啟的詳情路由。 */
export function ProjectHealthSection({ health }: { health: ReturnType<typeof useProjectHealth> }) {
  const features = health.data?.features ?? [];
  const counts = summarizeFeatures(features);
  return (
    <section className="project-health" aria-labelledby="project-health-heading">
      <SectionHeader
        id="project-health-heading"
        title="Project Health"
      />
      {!health.available ? (
        <div className="health-project">
          <p className="health-feature-detail">專案健康監測尚未啟用，將於共用 log 系統完成後提供。</p>
          <Link className="health-back-link" to={`${projectManifest.routeBase}/health/${projectManifest.id}`}>查看專案健康詳情 <ChevronRight size={14} aria-hidden="true" /></Link>
        </div>
      ) : <>
      {health.error ? <p role="alert" className="health-diagnostic-error">{health.error}{health.data ? '；目前顯示上次成功取得的報告。' : ''}</p> : null}
      {!health.data ? <p role="status">{health.loading ? '正在檢查專案功能…' : '尚無可顯示的健康報告。'}</p> : <>
      <HealthSummary features={features} />
      <div className="health-project-grid">
        <Link
          className="health-project-card"
          to={`${projectManifest.routeBase}/health/${projectManifest.id}`}
          aria-label="查看 System Monitor 功能健康詳情"
        >
          <div className="health-project-card-heading">
            <h3><Activity size={16} aria-hidden="true" />{projectManifest.name}</h3>
            <ChevronRight size={14} aria-hidden="true" />
          </div>
          <p className="health-project-primary" aria-label={`${features.length} 項功能中 ${counts.healthy} 項正常`}>
            <span className="health-tone-healthy">{counts.healthy}</span>
            <span className="health-project-total">/ {features.length}</span>
            <span className="health-project-primary-label">Healthy</span>
          </p>
          <dl className="health-project-counts">
            <div className="health-tone-issues"><dt>Issues</dt><dd>{counts.issues}</dd></div>
            <div className="health-tone-unavailable"><dt>Unavailable</dt><dd>{counts.unavailable}</dd></div>
            <div className="health-tone-unknown"><dt>Unknown</dt><dd>{counts.unknown}</dd></div>
          </dl>
        </Link>
      </div>
      </>}
      </>}
    </section>
  );
}
