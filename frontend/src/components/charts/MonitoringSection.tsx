import type { RealtimeSample } from '../../types/realtime';
import { HISTORICAL_RANGES, type HistoricalRange } from '../../types/history';
import { useHistoricalMetrics } from '../../hooks/useHistoricalMetrics';
import { SectionHeader } from '../layout/SectionHeader';
import { HistoricalMonitoringCharts } from './HistoricalMonitoringCharts';
import { LiveMonitoringCharts } from './LiveMonitoringCharts';

type MonitoringMode = 'live' | 'history';

interface MonitoringSectionProps {
  samples: RealtimeSample[];
  mode: MonitoringMode;
  onModeChange: (mode: MonitoringMode) => void;
}

export function MonitoringSection({
  samples,
  mode,
  onModeChange,
}: MonitoringSectionProps) {
  const historyEnabled = mode === 'history';
  const { range, setRange, data, loading, error, retry } = useHistoricalMetrics({
    enabled: historyEnabled,
  });

  const isLive = mode === 'live';

  return (
    <section
      className="realtime-monitoring"
      aria-labelledby="monitoring-heading"
    >
      <SectionHeader
        id="monitoring-heading"
        title="Monitoring"
        description={
          isLive
            ? 'Live behavior and short-term movement'
            : 'Historical trends from persistent samples'
        }
        meta={
          isLive ? (
            <span className="section-header-eyebrow">Last 5 minutes</span>
          ) : (
            <span className="section-header-eyebrow">Persistent history</span>
          )
        }
      />

      <div className="monitoring-controls">
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
        <LiveMonitoringCharts samples={samples} />
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
        <HistoricalMonitoringCharts range={range} samples={data.samples} />
      ) : null}
    </section>
  );
}

export type { MonitoringMode, HistoricalRange };
