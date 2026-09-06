import type { DiskInfo } from '../../types/system';
import { formatBytes, formatPercent } from '../../utils/format';
import { SectionHeader } from '../layout/SectionHeader';

interface StorageListProps {
  disks: DiskInfo[];
}

export function StorageList({ disks }: StorageListProps) {
  return (
    <section
      className="storage-details"
      aria-labelledby="storage-details-heading"
    >
      <SectionHeader
        id="storage-details-heading"
        title="Storage Details"
        description="Mounted filesystems"
        tone="secondary"
      />

      {disks.length === 0 ? (
        <div className="detail-section detail-section-quiet">
          <p className="empty-message">No mounted filesystems found.</p>
        </div>
      ) : (
        <div className="detail-section detail-section-quiet">
          <div className="table-wrapper">
            <table className="storage-table">
              <thead>
                <tr>
                  <th>Mount</th>
                  <th>Filesystem</th>
                  <th>Used</th>
                  <th>Total</th>
                  <th>Free</th>
                  <th>Usage %</th>
                </tr>
              </thead>
              <tbody>
                {disks.map((disk) => (
                  <tr key={`${disk.mount_point}-${disk.device ?? 'unknown'}`}>
                    <td>{disk.mount_point}</td>
                    <td>{disk.filesystem_type}</td>
                    <td>{formatBytes(disk.used_bytes)}</td>
                    <td>{formatBytes(disk.total_bytes)}</td>
                    <td>{formatBytes(disk.free_bytes)}</td>
                    <td>{formatPercent(disk.usage_percent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
