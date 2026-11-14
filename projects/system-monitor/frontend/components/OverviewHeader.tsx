import { Activity, RefreshCw } from 'lucide-react';
import type { ConnectionStatus } from '../hooks/useOverview';
import { formatClockTime } from '../utils/format';
import { PageHeader } from '@shell/components/layout/PageHeader';
import projectManifest from '../../project.json';

interface OverviewHeaderProps {
  status: ConnectionStatus;
  lastUpdated: Date | null;
  onRefresh: () => void;
  loading: boolean;
  error: string | null;
}

const STATUS_LABELS: Record<ConnectionStatus, string> = {
  online: 'Online',
  stale: 'Stale',
  unstable: 'Unstable',
  offline: 'Offline',
};

export function OverviewHeader({
  status,
  lastUpdated,
  onRefresh,
  loading,
  error,
}: OverviewHeaderProps) {
  const actions = (
    <div className="homelab-header-meta">
      {/* 連線狀態與更新時間上下排列，刷新按鈕獨立置於右側。 */}
      <div className="homelab-header-status">
        <span className={`homelab-status homelab-status-${status}`}>
          <span className="homelab-status-dot" aria-hidden="true" />
          {loading && !lastUpdated ? 'Loading' : STATUS_LABELS[status]}
        </span>
        <span className="homelab-last-updated">
          {lastUpdated ? `Sampled at ${formatClockTime(lastUpdated)}` : 'No samples yet'}
        </span>
        {error ? <span className="homelab-header-error" role="alert">{error}</span> : null}
      </div>
      <button
        type="button"
        className="homelab-refresh-button homelab-refresh-icon-button"
        onClick={onRefresh}
        aria-label="Refresh System Monitor"
        title="Refresh all monitoring data"
      >
        <RefreshCw size={18} aria-hidden="true" />
      </button>
    </div>
  );

  return (
    <PageHeader
      className="monitor-page-header"
      title={projectManifest.name}
      icon={<Activity className="monitor-title-icon" size={28} strokeWidth={1.75} aria-hidden="true" />}
      actions={actions}
    />
  );
}
