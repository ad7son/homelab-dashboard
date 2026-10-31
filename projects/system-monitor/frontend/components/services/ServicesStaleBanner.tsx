import { formatClockTime } from '../../utils/format';

interface ServicesStaleBannerProps {
  lastUpdated: Date | null;
  error: string | null;
}

export function ServicesStaleBanner({
  lastUpdated,
  error,
}: ServicesStaleBannerProps) {
  return (
    <div
      className="connection-banner connection-banner-unstable"
      role="status"
    >
      <p className="connection-banner-title">Service status could not be refreshed</p>
      <p className="connection-banner-body">
        Showing last known service data. Automatic polling will recover when the
        API is available again.
      </p>
      {lastUpdated ? (
        <p className="connection-banner-meta">
          Last successful check {formatClockTime(lastUpdated)}
        </p>
      ) : null}
      {error ? <p className="connection-banner-meta">{error}</p> : null}
    </div>
  );
}
