import { RefreshCw } from 'lucide-react';
import type { ConnectionStatus } from '../../types/system';
import { formatClockTime } from '../../utils/format';
import { PageHeader } from '@shell/components/layout/PageHeader';
import projectManifest from '../../../project.json';

interface HomeLabHeaderProps {
  status: ConnectionStatus;
  lastUpdated: Date | null;
  onRefresh: () => void;
}

const STATUS_LABELS: Record<ConnectionStatus, string> = {
  online: 'Online',
  unstable: 'Unstable',
  offline: 'Offline',
};

export function HomeLabHeader({
  status,
  lastUpdated,
  onRefresh,
}: HomeLabHeaderProps) {
  const actions = (
    <div className="homelab-header-meta">
      {/* 連線狀態與更新時間上下排列，刷新按鈕獨立置於右側。 */}
      <div className="homelab-header-status">
        <span className={`homelab-status homelab-status-${status}`}>
          <span className="homelab-status-dot" aria-hidden="true" />
          {STATUS_LABELS[status]}
        </span>
        <span className="homelab-last-updated">
          Last updated {formatClockTime(lastUpdated)}
        </span>
      </div>
      <button
        type="button"
        className="homelab-refresh-button homelab-refresh-icon-button"
        onClick={onRefresh}
        aria-label="Refresh Monitor"
        title="Refresh all monitoring data"
      >
        <RefreshCw size={18} aria-hidden="true" />
      </button>
    </div>
  );

  return (
    <PageHeader className="monitor-page-header" title={projectManifest.name} actions={actions} />
  );
}
