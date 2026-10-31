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
        <div className="network-rate">
          <span className="rate-label">Download</span>
          <span className="metric-primary metric-primary-sm">
            ↓ {formatNullable(network.download_rate, formatBytesPerSecond)}
          </span>
        </div>
        <div className="network-rate">
          <span className="rate-label">Upload</span>
          <span className="metric-primary metric-primary-sm">
            ↑ {formatNullable(network.upload_rate, formatBytesPerSecond)}
          </span>
        </div>
      </div>
      <p className="metric-secondary-line metric-secondary-line-quiet">
        {network.interface ?? 'N/A'}
        {network.ip_address ? ` · ${network.ip_address}` : ''}
      </p>
    </article>
  );
}
