import type { CpuInfo } from '../../types/system';
import {
  formatFrequency,
  formatNullable,
  formatPercent,
  formatTemperature,
} from '../../utils/format';

interface CpuCardProps {
  cpu: CpuInfo;
}

export function CpuCard({ cpu }: CpuCardProps) {
  return (
    <article className="metric-card">
      <h2>CPU</h2>
      <p className="metric-primary">{formatPercent(cpu.usage_percent)}</p>
      <div className="metric-secondary">
        <span>
          Temp:{' '}
          {formatNullable(cpu.temperature, formatTemperature)}
        </span>
        <span>
          Freq:{' '}
          {formatNullable(cpu.frequency, formatFrequency)}
        </span>
      </div>
      <div
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
      </div>
    </article>
  );
}
