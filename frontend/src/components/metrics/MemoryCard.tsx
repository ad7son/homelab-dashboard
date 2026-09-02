import type { MemoryInfo } from '../../types/system';
import { formatBytes, formatPercent } from '../../utils/format';

interface MemoryCardProps {
  memory: MemoryInfo;
}

export function MemoryCard({ memory }: MemoryCardProps) {
  return (
    <article className="metric-card">
      <h2>Memory</h2>
      <p className="metric-primary">{formatPercent(memory.usage_percent)}</p>
      <div className="metric-secondary">
        <span>
          Used: {formatBytes(memory.used)} / {formatBytes(memory.total)}
        </span>
        <span>Available: {formatBytes(memory.available)}</span>
        <span>
          Swap: {formatBytes(memory.swap.used)} /{' '}
          {formatBytes(memory.swap.total)} (
          {formatPercent(memory.swap.usage_percent)})
        </span>
      </div>
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
