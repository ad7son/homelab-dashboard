import type { ConnectionStatus } from '../../types/system';
import { formatClockTime } from '../../utils/format';

interface ConnectionBannerProps {
  status: Extract<ConnectionStatus, 'stale' | 'unstable' | 'offline'>;
  lastUpdated: Date | null;
}

export function ConnectionBanner({
  status,
  lastUpdated,
}: ConnectionBannerProps) {
  const lastSuccessful = formatClockTime(lastUpdated);

  if (status === 'stale') {
    return (
      <div className="connection-banner connection-banner-unstable" role="status">
        <p className="connection-banner-title">Monitoring data is stale</p>
        <p className="connection-banner-body">The latest sample is not current. The collector may have stopped or its clock may be incorrect.</p>
        <p className="connection-banner-meta">Last sampled at {lastSuccessful}</p>
      </div>
    );
  }

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
            Last sampled at {lastSuccessful}
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
        sample at {lastSuccessful}.
      </p>
    </div>
  );
}
