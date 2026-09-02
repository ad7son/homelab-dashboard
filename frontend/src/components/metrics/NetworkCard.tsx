import type { NetworkInfo } from '../../types/system';
import { formatBytesPerSecond, formatNullable } from '../../utils/format';

interface NetworkCardProps {
  network: NetworkInfo;
}

export function NetworkCard({ network }: NetworkCardProps) {
  return (
    <article className="metric-card">
      <h2>Network</h2>
      <div className="network-rates">
        <div>
          <span className="rate-label">↓ Download</span>
          <span className="metric-primary metric-primary-sm">
            {formatNullable(network.download_rate, formatBytesPerSecond)}
          </span>
        </div>
        <div>
          <span className="rate-label">↑ Upload</span>
          <span className="metric-primary metric-primary-sm">
            {formatNullable(network.upload_rate, formatBytesPerSecond)}
          </span>
        </div>
      </div>
      <div className="metric-secondary">
        <span>Interface: {network.interface ?? 'N/A'}</span>
        <span>IPv4: {network.ip_address ?? 'N/A'}</span>
      </div>
    </article>
  );
}
