import type { RealtimeSample } from '../../types/realtime';
import type { CpuInfo } from '../../types/system';
import {
  formatNullable,
  formatPercent,
  formatTemperature,
} from '../../utils/format';
import { averageRecentMetric } from '../../utils/realtimeAverages';

interface CpuCardProps {
  cpu: CpuInfo;
  samples: RealtimeSample[];
}

export function CpuCard({ cpu, samples }: CpuCardProps) {
  const average30s = averageRecentMetric(samples, 'cpuUsagePercent');
  const temperature = formatNullable(cpu.temperature, formatTemperature);
  const averageLabel =
    average30s == null ? '30s avg N/A' : `30s avg ${formatPercent(average30s)}`;

  return (
    <article className="metric-card">
      <h2>CPU</h2>
      <p className="metric-primary">{formatNullable(cpu.usage_percent, formatPercent)}</p>
      <p className="metric-secondary-line">
        {temperature} · {averageLabel}
      </p>
      {cpu.usage_percent !== null ? <div
        className="usage-bar"
        role="progressbar"
        aria-valuenow={cpu.usage_percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="usage-bar-fill usage-bar-cpu"
          style={{ width: `${cpu.usage_percent}%` }}
        />
      </div> : null}
    </article>
  );
}
