import { Activity, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { SectionHeader } from '@shell/components/layout/SectionHeader';
import projectManifest from '../../../project.json';
import { HealthSummary } from './HealthSummary';
import { summarizeFeatures } from './healthData';
import type { useProjectHealth } from '../../hooks/useProjectHealth';

/** 顯示平台登記的全部專案；新專案無需修改此元件即可出現在總覽。 */
export function ProjectHealthSection({ health }: { health: ReturnType<typeof useProjectHealth> }) {
  const features = health.projects.flatMap((project) => project.features);
  return (
    <section className="project-health" aria-labelledby="project-health-heading">
      <SectionHeader id="project-health-heading" title="Project Health" />
      {health.error ? <p role="alert" className="health-diagnostic-error">{health.error}{health.projects.length ? '；目前顯示上次成功取得的報告。' : ''}</p> : null}
      {!health.projects.length ? <p role="status">{health.loading ? '正在讀取專案健康報告…' : '尚無可顯示的專案報告。'}</p> : <>
        <HealthSummary features={features} />
        <div className="health-project-grid">
          {health.projects.map((project) => {
            const counts = summarizeFeatures(project.features);
            return (
              <Link className="health-project-card" key={project.project_id}
                to={`${projectManifest.routeBase}/health/${encodeURIComponent(project.project_id)}`}
                aria-label={`查看 ${project.project_name} 功能健康詳情`}>
                <div className="health-project-card-heading">
                  <h3><Activity size={16} aria-hidden="true" />{project.project_name}</h3>
                  <ChevronRight size={14} aria-hidden="true" />
                </div>
                {project.features.length ? <>
                  <p className="health-project-primary" aria-label={`${project.features.length} 項功能中 ${counts.healthy} 項正常`}>
                    <span className="health-tone-healthy">{counts.healthy}</span>
                    <span className="health-project-total">/ {project.features.length}</span>
                    <span className="health-project-primary-label">Healthy</span>
                  </p>
                  <dl className="health-project-counts">
                    <div className="health-tone-issues"><dt>Issues</dt><dd>{counts.issues}</dd></div>
                    <div className="health-tone-unavailable"><dt>Unavailable</dt><dd>{counts.unavailable}</dd></div>
                    <div className="health-tone-unknown"><dt>Unknown</dt><dd>{counts.unknown}</dd></div>
                  </dl>
                </> : <p className="health-feature-detail">尚未宣告監測功能</p>}
              </Link>
            );
          })}
        </div>
      </>}
    </section>
  );
}
