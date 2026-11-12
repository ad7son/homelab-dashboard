import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { STATUS_LABELS } from './healthData';
import type { FeatureHealth, ProjectHealthReport } from '../../types/health';
import { FeatureDiagnostics, type DiagnosticProps } from './FeatureDiagnostics';

/** 原生 disclosure 提供鍵盤開關；展開時顯示與狀態相同快照的證據。 */
function FeatureRow({ feature, ...diagnostics }: DiagnosticProps) {
  const [open, setOpen] = useState(false);
  return (
    <details className="health-feature" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>
        <span className="health-feature-name">{feature.name}</span>
        <span className="health-feature-message">{feature.message}</span>
        <span className={`health-feature-status health-tone-${feature.status}`}>
          <span className="health-status-dot" aria-hidden="true" />{STATUS_LABELS[feature.status]}
        </span>
        <ChevronDown className="health-feature-chevron" size={16} aria-hidden="true" />
      </summary>
      {open ? (
        <div className="health-feature-detail">
          <div className="health-feature-explanation">
            <section><h4>功能說明</h4><p>{feature.description}</p></section>
            <section><h4>判定依據</h4><p>{feature.criteria}</p></section>
          </div>
          <FeatureDiagnostics feature={feature} {...diagnostics} />
        </div>
      ) : null}
    </details>
  );
}

/** 先辨識功能與結果，再從右側狀態判斷優先度；每個欄位維持固定對齊。 */
export function HealthFeatureList({ features, ...diagnostics }: { features: FeatureHealth[]; report: ProjectHealthReport; onRefresh: () => void; refreshing: boolean }) {
  return (
    <div className="health-feature-list">
      <div className="health-feature-columns" aria-hidden="true">
        <span>Feature</span><span>Latest Result</span><span>Status</span><span />
      </div>
      {features.map((feature) => <FeatureRow key={feature.id} feature={feature} {...diagnostics} />)}
    </div>
  );
}
