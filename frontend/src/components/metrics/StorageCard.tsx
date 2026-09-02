import type { DiskInfo } from '../../types/system';
import { formatBytes, formatPercent } from '../../utils/format';

interface StorageCardProps {
  disks: DiskInfo[];
}

function findPrimaryDisk(disks: DiskInfo[]): DiskInfo | null {
  const root = disks.find((d) => d.mount_point === '/');
  if (root) return root;

  const dataDisk = disks.find(
    (d) => d.total_bytes > 0 && !d.mount_point.startsWith('/System/Volumes'),
  );
  if (dataDisk) return dataDisk;

  return disks.length > 0 ? disks[0] : null;
}

export function StorageCard({ disks }: StorageCardProps) {
  const primary = findPrimaryDisk(disks);

  if (!primary) {
    return (
      <article className="metric-card">
        <h2>Storage</h2>
        <p className="metric-primary">N/A</p>
        <div className="metric-secondary">
          <span>No filesystem data available</span>
        </div>
      </article>
    );
  }

  return (
    <article className="metric-card">
      <h2>Storage</h2>
      <p className="metric-primary">{formatPercent(primary.usage_percent)}</p>
      <div className="metric-secondary">
        <span>
          Used: {formatBytes(primary.used_bytes)} /{' '}
          {formatBytes(primary.total_bytes)}
        </span>
        <span>Mount: {primary.mount_point}</span>
      </div>
      <div
        className="usage-bar"
        role="progressbar"
        aria-valuenow={primary.usage_percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="usage-bar-fill usage-bar-storage"
          style={{ width: `${primary.usage_percent}%` }}
        />
      </div>
    </article>
  );
}
