import { useState } from 'react';
import { Check, Copy, RefreshCw } from 'lucide-react';
import { formatDiagnosticResponse } from './diagnosticData';
import type { FeatureHealth, ProjectHealthReport } from '../../api/health';

export interface DiagnosticProps {
  feature: FeatureHealth;
  report: ProjectHealthReport;
  onRefresh: () => void;
  refreshing: boolean;
}
const date = (timestamp: number | null) => timestamp === null ? '尚無成功紀錄' : new Date(timestamp).toLocaleString('zh-TW', { hour12: false });

/** 使用同次後端報告的原始證據，不另外查詢即時數值，以免與判定結果錯置。 */
export function FeatureDiagnostics({ feature, report, onRefresh, refreshing }: DiagnosticProps) {
  const [view, setView] = useState<'feature' | 'response'>('feature');
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [copyError, setCopyError] = useState(false);
  const displayed = formatDiagnosticResponse(JSON.stringify(view === 'response' ? report : feature.raw_data));
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(displayed);
      setCopiedText(displayed);
      setCopyError(false);
    } catch { setCopiedText(null); setCopyError(true); }
  };
  return (
    <section className="health-diagnostics" aria-label="實際原始資料">
      <div className="health-diagnostic-heading">
        <h4>原始資料</h4>
        <button className="health-diagnostic-button" type="button" onClick={onRefresh} disabled={refreshing} aria-label="重新取得原始資料">
          <RefreshCw size={14} aria-hidden="true" />{refreshing ? '取得中…' : '重新取得'}
        </button>
      </div>
      <div className="health-diagnostic-source"><span>GET</span><code>/api/project-health/{encodeURIComponent(report.project_id)}</code><span>來源：<code>{feature.source}</code></span></div>
      <dl className="health-diagnostic-meta">
        <div><dt>判定時間</dt><dd>{date(feature.checked_at_ms)}</dd></div>
        <div><dt>最近成功</dt><dd>{date(feature.last_success_at_ms)}</dd></div>
        <div><dt>最近執行耗時</dt><dd>{feature.duration_ms === null ? '尚無執行紀錄' : `${feature.duration_ms.toFixed(1)} ms`}</dd></div>
      </dl>
      {feature.error ? <div className="health-diagnostic-error" role="alert">
        <strong>{feature.error.type}</strong><p>{feature.error.message}</p>
        {feature.error.traceback ? <pre tabIndex={0}><code>{feature.error.traceback}</code></pre> : null}
      </div> : null}
      <div className="health-raw-data">
        <div className="health-raw-toolbar">
          <div className="health-raw-tabs" role="group" aria-label="原始資料顯示方式">
            <button type="button" aria-pressed={view === 'feature'} onClick={() => setView('feature')}>功能資料</button>
            <button type="button" aria-pressed={view === 'response'} onClick={() => setView('response')}>完整 API 回應</button>
          </div>
          <button type="button" className="health-diagnostic-button" onClick={copy} aria-label="複製目前原始資料">
            {copiedText === displayed ? <Check size={14} /> : <Copy size={14} />}{copiedText === displayed ? '已複製' : '複製'}
          </button>
        </div>
        <pre tabIndex={0} aria-label={view === 'response' ? '完整 API 原始回應' : '完整功能原始資料'}><code>{displayed}</code></pre>
        {copyError ? <p role="status" className="health-diagnostic-message">無法存取剪貼簿，請直接選取上方內容複製。</p> : null}
      </div>
    </section>
  );
}
