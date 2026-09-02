import type { ConnectionStatus, SystemInfo } from '../../types/system';
import {
  formatRelativeTime,
  formatUptime,
} from '../../utils/format';

interface HeaderProps {
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

export function Header({
  system,
  status,
  lastUpdated,
  onRefresh,
}: HeaderProps) {
  return (
    <header className="dashboard-header">
      <div className="header-main">
        <h1>Home Lab Dashboard</h1>
        {system && (
          <p className="header-subtitle">
            {system.hostname} · {system.operating_system} · Uptime{' '}
            {formatUptime(system.uptime)}
          </p>
        )}
      </div>
      <div className="header-meta">
        <span className={`status-badge status-${status}`}>
          {STATUS_LABELS[status]}
        </span>
        <span className="last-updated">
          Last updated: {formatRelativeTime(lastUpdated)}
        </span>
        <button type="button" className="refresh-button" onClick={onRefresh}>
          Refresh
        </button>
      </div>
    </header>
  );
}
