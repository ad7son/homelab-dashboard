import { useMemo } from 'react';
import type { RealtimeSample } from '../../types/realtime';
import { formatBytesPerSecond, formatPercent, formatTemperature } from '../../utils/format';
import { RealtimeChart } from './RealtimeChart';
import { hasValidSeriesValues, toChartPoints } from './chartUtils';

interface RealtimeMonitoringProps {
  samples: RealtimeSample[];
}

export function RealtimeMonitoring({ samples }: RealtimeMonitoringProps) {
  const chartPoints = useMemo(() => toChartPoints(samples), [samples]);
  const temperatureAvailable = useMemo(
    () => hasValidSeriesValues(samples, 'cpuTemperatureCelsius'),
    [samples],
  );

  return (
    <section className="realtime-monitoring" aria-labelledby="realtime-monitoring-heading">
      <div className="realtime-monitoring-header">
        <h2 id="realtime-monitoring-heading">Realtime Monitoring</h2>
        <span className="realtime-monitoring-subtitle">Last 5 minutes</span>
      </div>

      <div className="realtime-charts-grid">
        <RealtimeChart
          title="CPU Usage"
          data={chartPoints}
          series={[
            {
              dataKey: 'cpuUsagePercent',
              name: 'CPU',
              color: 'var(--color-chart-cpu)',
            },
          ]}
          yDomain={[0, 100]}
          yTickFormatter={(value) => `${value}`}
          formatValue={(value) => formatPercent(value)}
        />

        <RealtimeChart
          title="CPU Temperature"
          data={chartPoints}
          series={[
            {
              dataKey: 'cpuTemperatureCelsius',
              name: 'Temp',
              color: 'var(--color-chart-temperature)',
            },
          ]}
          yTickFormatter={(value) => `${value}`}
          formatValue={(value) => formatTemperature(value)}
          unavailable={!temperatureAvailable && samples.length > 0}
          unavailableMessage="Temperature data unavailable"
        />

        <RealtimeChart
          title="Memory Usage"
          data={chartPoints}
          series={[
            {
              dataKey: 'memoryUsagePercent',
              name: 'Memory',
              color: 'var(--color-chart-memory)',
            },
          ]}
          yDomain={[0, 100]}
          yTickFormatter={(value) => `${value}`}
          formatValue={(value) => formatPercent(value)}
        />

        <RealtimeChart
          title="Network Traffic"
          data={chartPoints}
          series={[
            {
              dataKey: 'networkDownloadBytesPerSecond',
              name: 'Download',
              color: 'var(--color-chart-download)',
            },
            {
              dataKey: 'networkUploadBytesPerSecond',
              name: 'Upload',
              color: 'var(--color-chart-upload)',
            },
          ]}
          yAxisWidth={64}
          yTickFormatter={(value) => formatBytesPerSecond(value)}
          formatValue={(value) => formatBytesPerSecond(value)}
          showLegend
        />
      </div>
    </section>
  );
}
