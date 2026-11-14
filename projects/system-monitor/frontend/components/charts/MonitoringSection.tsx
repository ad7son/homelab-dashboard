import { useState } from 'react';
import type { RealtimeSample } from '../../utils/realtimeSamples';
import { HISTORICAL_RANGES, type HistoricalRange } from '../../api/history';
import type { UseHistoryResult } from '../../hooks/useHistory';
import { HistoricalMonitoringCharts } from './HistoricalMonitoringCharts';
import { LiveMonitoringCharts } from './LiveMonitoringCharts';
import { MONITORING_METRICS, type MonitoringMetric } from './metrics';

type MonitoringMode = 'live' | 'history';

interface MonitoringSectionProps {
  history: UseHistoryResult;
  emptyMessage: string;
  samples: RealtimeSample[];
  mode: MonitoringMode;
  onModeChange: (mode: MonitoringMode) => void;
}

export function MonitoringSection({
  samples,
  history,
  emptyMessage,
  mode,
  onModeChange,
}: MonitoringSectionProps) {
  // 指標選擇獨立於即時／歷史模式，切換模式或範圍時保留同一個指標。
  const [metric, setMetric] = useState<MonitoringMetric>('cpu');
  const { range, setRange, data, loading, error, retry } = history;

  const isLive = mode === 'live';

  return (
    <div
      className="realtime-monitoring"
    >
      <div className="monitoring-controls">
        <select
          className="monitoring-metric-select"
          aria-label="Monitoring metric"
          value={metric}
          onChange={(event) => setMetric(event.target.value as MonitoringMetric)}
        >
          {MONITORING_METRICS.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
        <div className="segmented-control" role="group" aria-label="Monitoring mode">
          <button
            type="button"
            className={
              isLive
                ? 'segmented-control-button segmented-control-button-active'
                : 'segmented-control-button'
            }
            aria-pressed={isLive}
            onClick={() => onModeChange('live')}
          >
            Live
          </button>
          <button
            type="button"
            className={
              !isLive
                ? 'segmented-control-button segmented-control-button-active'
                : 'segmented-control-button'
            }
            aria-pressed={!isLive}
            onClick={() => onModeChange('history')}
          >
            History
          </button>
        </div>

        {!isLive ? (
          <div
            className="segmented-control"
            role="group"
            aria-label="Historical range"
          >
            {HISTORICAL_RANGES.map((option) => (
              <button
                key={option}
                type="button"
                className={
                  range === option
                    ? 'segmented-control-button segmented-control-button-active'
                    : 'segmented-control-button'
                }
                aria-pressed={range === option}
                onClick={() => setRange(option)}
              >
                {option}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {!isLive && error && data ? <p className="monitoring-panel-detail" role="alert">{error}；目前顯示上次取得的歷史資料。</p> : null}
      {isLive ? (
        <LiveMonitoringCharts samples={samples} metric={metric} emptyMessage={emptyMessage} />
      ) : loading && !data ? (
        <div className="monitoring-panel-state" role="status">
          Loading historical data…
        </div>
      ) : error && !data ? (
        <div className="monitoring-panel-state monitoring-panel-state-error">
          <h3 className="monitoring-panel-title">Historical data unavailable</h3>
          <p className="monitoring-panel-body">
            Unable to load historical monitoring data.
          </p>
          <p className="monitoring-panel-detail">{error}</p>
          <button
            type="button"
            className="homelab-retry-button"
            onClick={retry}
          >
            Retry
          </button>
        </div>
      ) : data && data.samples.length === 0 ? (
        <div className="monitoring-panel-state" role="status">
          <p className="monitoring-panel-body">
            No samples recorded in the last {range === '15m' ? '15 minutes' : range === '1h' ? 'hour' : range === '24h' ? '24 hours' : '7 days'}.
          </p>
          <p className="monitoring-panel-detail">Check that the metrics collector is running.</p>
          <button type="button" className="homelab-retry-button" onClick={retry}>Retry</button>
        </div>
      ) : data ? (
        <HistoricalMonitoringCharts range={range} intervalSeconds={data.interval_seconds} samples={data.samples} metric={metric} />
      ) : null}
    </div>
  );
}

export type { MonitoringMode, HistoricalRange };
