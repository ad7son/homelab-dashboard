import { useState } from 'react';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { PageContainer } from '@shell/components/layout/PageContainer';
import projectManifest from '../../project.json';
import { HealthSummary } from '../components/health/HealthSummary';
import { HealthFeatureList } from '../components/health/HealthFeatureList';
import type { FeatureStatus } from '../types/health';
import { useProjectHealth } from '../hooks/useProjectHealth';
import { usePageScrollPosition } from '../hooks/usePageScrollPosition';

/** 詳情顯示單一專案的完整檢查快照；手動更新時同步替換狀態與證據。 */
export function ProjectHealthPage() {
  const { projectId } = useParams();
  const [filter, setFilter] = useState<FeatureStatus | 'all'>('all');
  const health = useProjectHealth(0, projectId, false);
  const features = health.data?.features ?? [];
  usePageScrollPosition(health.data !== null || !health.loading);
  const filters: Array<{ value: FeatureStatus | 'all'; label: string }> = [
    { value: 'all', label: 'All' },
    { value: 'healthy', label: 'Healthy' },
    { value: 'issues', label: 'Issues' },
    { value: 'unavailable', label: 'Unavailable' },
    { value: 'unknown', label: 'Unknown' },
  ];
  const visible = features.filter((feature) => filter === 'all' || feature.status === filter);

  return (
    <PageContainer>
      {/* 明確指定總覽路徑，直接開啟詳情網址時也能返回，不依賴瀏覽紀錄。 */}
      <header className="health-detail-header">
        <Link
          className="health-back-link"
          to={projectManifest.routeBase}
          aria-label="返回 System Monitor 總覽"
          title="返回總覽"
        >
          <ArrowLeft size={20} aria-hidden="true" />
        </Link>
        <h1>{health.data?.project_name ?? 'Project Health'}</h1>
        <button type="button" className="health-diagnostic-button" onClick={health.refresh} disabled={health.loading} aria-label="刷新專案健康檢查" title="刷新專案健康檢查"><RefreshCw size={18} /></button>
      </header>
      <>
          {health.error ? <p role="alert" className="health-diagnostic-error">{health.error}{health.data ? '；目前顯示上次成功取得的報告。' : ''}</p> : null}
          {!health.data ? <p role="status">{health.loading ? '正在檢查專案功能…' : '尚無可顯示的健康報告。'}</p> : <>
          <HealthSummary features={features} />
          <div className="health-detail-filters segmented-control" role="group" aria-label="依功能狀態篩選">
            {filters.map((item) => (
              <button
                type="button"
                key={item.value}
                className={`segmented-control-button${filter === item.value ? ' segmented-control-button-active' : ''}`}
                aria-pressed={filter === item.value}
                onClick={() => setFilter(item.value)}
              >{item.label}</button>
            ))}
          </div>
          <div className="health-project">
            <HealthFeatureList features={visible} report={health.data} onRefresh={health.refresh} refreshing={health.loading} />
            {visible.length === 0 ? <p className="health-feature-detail">{features.length ? '沒有符合此狀態的功能。' : '此專案尚未宣告監測功能。'}</p> : null}
          </div>
          </>}
      </>
    </PageContainer>
  );
}
