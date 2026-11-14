import { summarizeFeatures } from './healthData';
import type { FeatureHealth } from '../../api/health';

/** 只統計呼叫端傳入的功能：詳情傳單一專案，總覽可傳彙整清單。 */
export function HealthSummary({ features }: { features?: FeatureHealth[] }) {
  const counts = summarizeFeatures(features ?? []);
  const summary = [
    { label: 'Total', value: features?.length, status: 'total' },
    { label: 'Healthy', value: counts.healthy, status: 'healthy' },
    { label: 'Issues', value: counts.issues, status: 'issues' },
    { label: 'Unavailable', value: counts.unavailable, status: 'unavailable' },
    { label: 'Unknown', value: counts.unknown, status: 'unknown' },
  ];
  return (
      <div className="health-summary">
        <h3 className="health-summary-title">Summary</h3>
        <dl className="health-summary-grid">
          {summary.map((item) => (
            <div className={`health-summary-item health-tone-${item.status}`} key={item.label}>
              <dt>{item.label}</dt>
              <dd>{features ? item.value : '—'}</dd>
            </div>
          ))}
        </dl>
      </div>
  );
}
