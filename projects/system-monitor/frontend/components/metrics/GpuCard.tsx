import type { GpuInfo } from '../../types/system';
import { formatPercent } from '../../utils/format';

/** 不支援或讀取失敗時保留卡片並顯示 N/A，只有真實零值才顯示 0%。 */
export function GpuCard({ gpu }: { gpu?: GpuInfo }) {
  const usage = gpu?.status === 'available' ? gpu.usage_percent : null;

  return (
    <article className="metric-card">
      <h2>GPU</h2>
      <p className="metric-primary">{usage == null ? 'N/A' : formatPercent(usage)}</p>
      <p className="metric-secondary-line">
        {usage == null
          ? gpu?.status === 'unsupported' ? 'GPU monitoring not supported' : 'GPU data unavailable'
          : (gpu!.device_count ?? 0) > 1
            ? `${gpu!.name} · Busiest of ${gpu!.device_count} GPUs`
            : gpu!.name}
      </p>
      {usage != null ? (
        <div className="usage-bar" role="progressbar" aria-label="GPU usage" aria-valuenow={usage} aria-valuemin={0} aria-valuemax={100}>
          <div className="usage-bar-fill usage-bar-gpu" style={{ width: `${usage}%` }} />
        </div>
      ) : null}
    </article>
  );
}
