import type { ConnectionStatus, SystemInfo } from '../../types/system';
import {
  formatRelativeTime,
  formatUptime,
} from '../../utils/format';

interface HomeLabHeaderProps {
  system: SystemInfo | null;
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
  system,
  status,
  lastUpdated,
  onRefresh,
}: HomeLabHeaderProps) {
  return (
    <header className="homelab-header">
      <div className="homelab-header-main">
        <h1>Home Lab Dashboard</h1>
        {system && (
          <p className="homelab-header-subtitle">
            {system.hostname} · {system.operating_system} · Uptime{' '}
            {formatUptime(system.uptime)}
          </p>
        )}
      </div>
      <div className="homelab-header-meta">
        <span className={`status-badge status-${status}`}>
          {STATUS_LABELS[status]}
        </span>
        <span className="homelab-last-updated">
          Last updated: {formatRelativeTime(lastUpdated)}
        </span>
        <button
          type="button"
          className="homelab-refresh-button"
          onClick={onRefresh}
        >
          Refresh
        </button>
      </div>
    </header>
  );
}
