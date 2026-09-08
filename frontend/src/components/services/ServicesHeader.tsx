import { formatClockTime } from '../../utils/format';
import { PageHeader } from '../layout/PageHeader';

interface ServicesHeaderProps {
  lastUpdated: Date | null;
  refreshing: boolean;
  refreshDisabled?: boolean;
  onRefresh: () => void;
}

export function ServicesHeader({
  lastUpdated,
  refreshing,
  refreshDisabled = false,
  onRefresh,
}: ServicesHeaderProps) {
  const actions = (
    <div className="homelab-header-meta">
      <span className="homelab-last-updated">
        Last checked {formatClockTime(lastUpdated)}
      </span>
      <button
        type="button"
        className="homelab-refresh-button"
        onClick={onRefresh}
        disabled={refreshDisabled || refreshing}
        aria-busy={refreshing}
      >
        {refreshing ? 'Refreshing…' : 'Refresh'}
      </button>
    </div>
  );

  return (
    <PageHeader
      title="Services"
      description="Read-only monitoring for Home Lab systemd services."
      actions={actions}
    />
  );
}
