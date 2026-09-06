import type { ConnectionStatus, SystemInfo } from '../../types/system';
import { formatClockTime, formatUptime } from '../../utils/format';
import { PageHeader } from '../layout/PageHeader';

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
  const description = system ? (
    <p className="homelab-header-subtitle">
      {system.hostname} · {system.operating_system} · Uptime{' '}
      {formatUptime(system.uptime)}
    </p>
  ) : undefined;

  const actions = (
    <div className="homelab-header-meta">
      <span className={`homelab-status homelab-status-${status}`}>
        <span className="homelab-status-dot" aria-hidden="true" />
        {STATUS_LABELS[status]}
      </span>
      <span className="homelab-last-updated">
        Last updated {formatClockTime(lastUpdated)}
      </span>
      <button
        type="button"
        className="homelab-refresh-button"
        onClick={onRefresh}
      >
        Refresh
      </button>
    </div>
  );

  return (
    <PageHeader title="Home Lab" description={description} actions={actions} />
  );
}
