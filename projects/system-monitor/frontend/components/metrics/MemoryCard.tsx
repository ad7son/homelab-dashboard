import type { RealtimeSample } from '../../utils/realtimeSamples';
import type { MemoryInfo } from '../../api/overview';
import { formatBytes, formatNullable, formatPercent } from '../../utils/format';
import { averageRecentMetric } from '../../utils/realtimeAverages';

interface MemoryCardProps {
  memory?: MemoryInfo;
  emptyMessage?: string;
  samples: RealtimeSample[];
}

export function MemoryCard({ memory, samples, emptyMessage }: MemoryCardProps) {
  const average30s = averageRecentMetric(samples, 'memoryUsagePercent');
  const averageLabel =
    average30s == null ? '30s avg N/A' : `30s avg ${formatPercent(average30s)}`;

  return (
    <article className="metric-card">
      <h2>Memory</h2>
      <p className="metric-primary">{memory ? formatNullable(memory.usage_percent, formatPercent) : '—'}</p>
      <p className="metric-secondary-line">
        {memory ? `${averageLabel} · ${formatNullable(memory.used, formatBytes)} / ${formatNullable(memory.total, formatBytes)}` : emptyMessage ?? 'No memory data available'}
      </p>
      {memory?.usage_percent != null ? <div
        className="usage-bar"
        role="progressbar"
        aria-valuenow={memory?.usage_percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="usage-bar-fill usage-bar-memory"
          style={{ width: `${memory?.usage_percent}%` }}
        />
      </div> : null}
    </article>
  );
}
