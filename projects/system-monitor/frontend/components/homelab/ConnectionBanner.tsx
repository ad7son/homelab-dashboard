import type { ConnectionStatus } from '../../types/system';
import { formatClockTime } from '../../utils/format';

interface ConnectionBannerProps {
  status: Extract<ConnectionStatus, 'unstable' | 'offline'>;
  lastUpdated: Date | null;
}

export function ConnectionBanner({
  status,
  lastUpdated,
}: ConnectionBannerProps) {
  const lastSuccessful = formatClockTime(lastUpdated);

  if (status === 'unstable') {
    return (
      <div
        className="connection-banner connection-banner-unstable"
        role="status"
      >
        <p className="connection-banner-title">Connection unstable</p>
        <p className="connection-banner-body">
          Some monitoring requests are failing. Showing last known data.
        </p>
        {lastUpdated ? (
          <p className="connection-banner-meta">
            Last successful update {lastSuccessful}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div
      className="connection-banner connection-banner-offline"
      role="status"
    >
      <p className="connection-banner-title">Home Lab offline</p>
      <p className="connection-banner-body">
        Unable to reach the monitoring backend. Showing data from the last
        successful update {lastSuccessful}.
      </p>
    </div>
  );
}
