import type { DiskIoInfo } from '../../api/overview';
import { formatBytesPerSecond, formatNullable } from '../../utils/format';

/** 顯示全機磁碟讀寫速率；首次取樣與不支援環境維持 N/A，不偽裝成閒置。 */
export function DiskIoCard({ diskIo, emptyMessage }: { diskIo?: DiskIoInfo; emptyMessage?: string }) {
  const available = diskIo?.status === 'available';

  return (
    <article className="metric-card">
      <h2>Disk I/O</h2>
      <div className="disk-io-rates">
        <div className="disk-io-rate">
          <span className="rate-label">Read</span>
          <span className="metric-primary metric-primary-sm">
            {!diskIo ? '—' : formatNullable(available ? diskIo.read_bytes_per_second : null, formatBytesPerSecond)}
          </span>
        </div>
        <div className="disk-io-rate">
          <span className="rate-label">Write</span>
          <span className="metric-primary metric-primary-sm">
            {!diskIo ? '—' : formatNullable(available ? diskIo.write_bytes_per_second : null, formatBytesPerSecond)}
          </span>
        </div>
      </div>
      {!available ? (
        <p className="metric-secondary-line metric-secondary-line-quiet">
          {!diskIo ? emptyMessage ?? 'No disk data available' : diskIo.status === 'warming_up'
            ? 'Collecting disk activity…'
            : 'Disk I/O data unavailable'}
        </p>
      ) : null}
    </article>
  );
}
