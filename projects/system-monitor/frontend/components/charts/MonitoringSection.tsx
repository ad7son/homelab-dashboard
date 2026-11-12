import { useState } from 'react';
import type { RealtimeSample } from '../../types/realtime';
import { HISTORICAL_RANGES, type HistoricalRange } from '../../types/history';
import { useHistoricalMetrics } from '../../hooks/useHistoricalMetrics';
import { HistoricalMonitoringCharts } from './HistoricalMonitoringCharts';
import { LiveMonitoringCharts } from './LiveMonitoringCharts';
import { MONITORING_METRICS, type MonitoringMetric } from '../../types/monitoring';

type MonitoringMode = 'live' | 'history';

interface MonitoringSectionProps {
  refreshToken: number;
  samples: RealtimeSample[];
  mode: MonitoringMode;
  onModeChange: (mode: MonitoringMode) => void;
}

export function MonitoringSection({
  samples,
  refreshToken,
  mode,
  onModeChange,
}: MonitoringSectionProps) {
  // 指標選擇獨立於即時／歷史模式，切換模式或範圍時保留同一個指標。
  const [metric, setMetric] = useState<MonitoringMetric>('cpu');
  const historyEnabled = mode === 'history';
  const { range, setRange, data, loading, error, retry } = useHistoricalMetrics({
    enabled: historyEnabled,
    refreshToken,
  });

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

      {isLive ? (
        <LiveMonitoringCharts samples={samples} metric={metric} />
      ) : loading ? (
        <div className="monitoring-panel-state" role="status">
          Loading historical data…
        </div>
      ) : error ? (
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
          No historical data available for this range.
        </div>
      ) : data ? (
        <HistoricalMonitoringCharts range={range} samples={data.samples} metric={metric} />
      ) : null}
    </div>
  );
}

export type { MonitoringMode, HistoricalRange };
