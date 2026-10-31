import { useMemo } from 'react';
import type { RealtimeSample } from '../../types/realtime';
import {
  formatBytesPerSecond,
  formatPercent,
  formatTemperature,
} from '../../utils/format';
import { MetricChart } from './MetricChart';
import { hasValidSeriesValues, toChartPoints } from './chartUtils';

interface LiveMonitoringChartsProps {
  samples: RealtimeSample[];
}

export function LiveMonitoringCharts({ samples }: LiveMonitoringChartsProps) {
  const chartPoints = useMemo(() => toChartPoints(samples), [samples]);
  const temperatureAvailable = useMemo(
    () => hasValidSeriesValues(chartPoints, 'cpuTemperatureCelsius'),
    [chartPoints],
  );

  return (
    <div className="realtime-charts-grid">
      <MetricChart
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

      <MetricChart
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

      <MetricChart
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

      <MetricChart
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
  );
}
