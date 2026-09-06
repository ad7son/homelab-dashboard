import type { RealtimeSample } from '../../types/realtime';
import type { MemoryInfo } from '../../types/system';
import { formatBytes, formatPercent } from '../../utils/format';
import { averageRecentMetric } from '../../utils/realtimeAverages';

interface MemoryCardProps {
  memory: MemoryInfo;
  samples: RealtimeSample[];
}

export function MemoryCard({ memory, samples }: MemoryCardProps) {
  const average30s = averageRecentMetric(samples, 'memoryUsagePercent');
  const averageLabel =
    average30s == null ? '30s avg N/A' : `30s avg ${formatPercent(average30s)}`;

  return (
    <article className="metric-card">
      <h2>Memory</h2>
      <p className="metric-primary">{formatPercent(memory.usage_percent)}</p>
      <p className="metric-secondary-line">
        {averageLabel} · {formatBytes(memory.used)} / {formatBytes(memory.total)}
      </p>
      <div
        className="usage-bar"
        role="progressbar"
        aria-valuenow={memory.usage_percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="usage-bar-fill usage-bar-memory"
          style={{ width: `${memory.usage_percent}%` }}
        />
      </div>
    </article>
  );
}
