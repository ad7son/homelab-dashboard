import { useMemo } from 'react';
import type {
  HistoricalMetricSample,
  HistoricalRange,
} from '../../types/history';
import {
  formatBytesPerSecond,
  formatPercent,
  formatTemperature,
} from '../../utils/format';
import { MetricChart } from './MetricChart';
import {
  formatHistoryAxisTime,
  formatHistoryTooltipTime,
  hasValidHistoricalTemperature,
  historicalSamplesToChartPoints,
} from './chartUtils';

interface HistoricalMonitoringChartsProps {
  range: HistoricalRange;
  samples: HistoricalMetricSample[];
}

export function HistoricalMonitoringCharts({
  range,
  samples,
}: HistoricalMonitoringChartsProps) {
  const chartPoints = useMemo(
    () => historicalSamplesToChartPoints(samples),
    [samples],
  );
  const temperatureAvailable = useMemo(
    () => hasValidHistoricalTemperature(samples),
    [samples],
  );

  const formatAxisTime = useMemo(
    () => (timestamp: number) => formatHistoryAxisTime(timestamp, range),
    [range],
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
        formatAxisTime={formatAxisTime}
        formatTooltipTime={formatHistoryTooltipTime}
        emptyMessage="No historical data available for this range."
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
        formatAxisTime={formatAxisTime}
        formatTooltipTime={formatHistoryTooltipTime}
        unavailable={!temperatureAvailable && samples.length > 0}
        unavailableMessage="Temperature data unavailable"
        emptyMessage="No historical data available for this range."
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
        formatAxisTime={formatAxisTime}
        formatTooltipTime={formatHistoryTooltipTime}
        emptyMessage="No historical data available for this range."
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
        formatAxisTime={formatAxisTime}
        formatTooltipTime={formatHistoryTooltipTime}
        showLegend
        emptyMessage="No historical data available for this range."
      />
    </div>
  );
}
